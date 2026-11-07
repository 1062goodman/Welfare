import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import openai
from typing import List, Optional

from graph import app 
from tasks import session_timestamps

from . import nest_pb2_grpc


router = APIRouter()

# 채팅------------------------------------------------

# 손님이 보낼 주문서(Request) 양식 정의 (Pydantic 사용)
class ChatRequest(BaseModel):
    session_id: str          # 사용자 구분용 ID (단톡방 번호 같은 역할)
    user_message: str        # 사용자가 입력한 질문

class PolicyCard(BaseModel):
    id: str
    name: str
    department: Optional[str] = None
    target: Optional[str] = None
    benefit: Optional[str] = None
    apply: Optional[str] = None
    summary: Optional[str] = None
    is_local: bool = False


# 손님에게 줄 영수증(Response) 양식 정의
class ChatResponse(BaseModel):
    bot_reply: str           # 챗봇의 답변
    reply_type: str = "general"
    policies: List[PolicyCard] = []


# 엔드포인트(창구) 만들기
@router.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest):
    print(f"[{request.session_id}] 사용자 질문 수신: {request.user_message}")
    
    # LangGraph에 전달할 설정 (어떤 사용자의 대화 기록을 꺼낼지 지정)
    config = {"configurable": {"thread_id": request.session_id}}

    session_timestamps[request.session_id] = datetime.now()

    # 챗봇(app)에게 질문 던지기 (주방으로 전달)
    result_state = app.invoke(
        {"messages": [HumanMessage(content=request.user_message)]},
        config=config
    )
    
    # 챗봇이 만들어낸 마지막 답변 꺼내기
    final_message = result_state["messages"][-1].content
    reply_type= result_state.get("reply_type", "general")

    policies = result_state.get("cards", []) if reply_type == "list" else []
    # 포장해서(Response 형식) 손님에게 반환
    return ChatResponse(bot_reply=final_message, reply_type=reply_type, policies=policies)



# 채팅내역 가져오기------------------------------------------------ 토큰 검증 로직 추가해야함
import uuid

class MessageHistoryResponse(BaseModel):
    id: str
    text: str
    isUser: bool
    replyType: Optional[str] = None
    policies: List[PolicyCard] = []

@router.get("/chat/history/{session_id}", response_model=List[MessageHistoryResponse])
def get_chat_history(session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    
    # LangGraph에서 해당 세션의 전체 상태(대화 기록) 꺼내기
    state = app.get_state(config)
    
    # 대화 기록이 아예 없으면 빈 리스트 반환
    if not state.values or "messages" not in state.values:
        return []
    
    history = []
    # 3. LangGraph의 메시지 객체들을 프론트엔드용 JSON 양식으로 변환
    for msg in state.values["messages"]:
        extra = getattr(msg, "additional_kwargs", {}) or {}
        history.append(MessageHistoryResponse(
            id=msg.id if hasattr(msg, 'id') and msg.id else str(uuid.uuid4()),
            text=msg.content,
            isUser=msg.type == "human",
            replyType=extra.get("reply_type"),
            policies=extra.get("cards", []),
        ))
        
    return history


# 서버체크------------------------------------------------
@router.get("/Health", response_model=bool)
def health_check():
    return True


# 음성인식
import asyncio, json
import grpc
from fastapi import WebSocket, WebSocketDisconnect
import nest_pb2

CLOVA_HOST = "clovaspeech-gw.ncloud.com:50051"
SILENCE = b"\x00" * 16000      # 0.5초 무음 (16kHz, 16bit, 모노)

client = openai.AsyncOpenAI()  # /File 엔드포인트용

def _data_req(chunk: bytes, seq: int, ep: bool):
    return nest_pb2.NestRequest(
        type=nest_pb2.RequestType.DATA,
        data=nest_pb2.NestData(
            chunk=chunk,
            extra_contents=json.dumps({"seqId": seq, "epFlag": ep}),
        ),
    )

async def _clova_requests(queue: asyncio.Queue):
    yield nest_pb2.NestRequest(
        type=nest_pb2.RequestType.CONFIG,
        config=nest_pb2.NestConfig(config=json.dumps({"transcription": {"language": "ko"}})),
    )
    seq, prev = 0, None
    while True:
        item = await queue.get()
        if item is None:                      # STOP_RECORDING
            break
        if prev is not None:
            yield _data_req(prev, seq, False)
            seq += 1
        prev = item
    if prev is not None:
        yield _data_req(prev, seq, False)
        yield _data_req(SILENCE, seq + 1, True)   # 마지막: 무음 + 발화 종료 신호

async def _clova_pump(call, websocket: WebSocket, state: dict):
    try:
        async for resp in call:
            try:
                t = json.loads(resp.contents).get("transcription")
            except ValueError:
                continue
            piece = (t or {}).get("text", "")
            if piece:
                state["text"] += piece
                await websocket.send_json({"recognized_text": state["text"].lstrip()})
    except grpc.aio.AioRpcError as e:
        print(f"클로바 오류: {e.code()} {e.details()}")
        await websocket.send_json({"status": "error", "message": e.details()})

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"{session_id} 웹소켓 연결")

    queue = task = channel = None
    state = {"text": ""}

    async def start():
        nonlocal queue, task, channel, state
        state = {"text": ""}
        queue = asyncio.Queue()
        channel = grpc.aio.secure_channel(CLOVA_HOST, grpc.ssl_channel_credentials())
        stub = nest_pb2_grpc.NestServiceStub(channel)
        call = stub.recognize(
            _clova_requests(queue),
            metadata=(("authorization", f"Bearer {os.environ['CLOVA_SECRET']}"),),
        )
        task = asyncio.create_task(_clova_pump(call, websocket, state))

    async def finish():
        nonlocal queue, task, channel
        if queue is None:
            return
        await queue.put(None)
        try:
            await asyncio.wait_for(task, timeout=4)
        except asyncio.TimeoutError:
            print(f"[{session_id}] 클로바 응답 대기 시간 초과")
        await channel.close()
        text = state["text"].strip()
        print(f"{session_id} 음성 인식 결과: {text}")
        await websocket.send_json({"recognized_text": text, "final": True})
        queue = task = channel = None

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("bytes"):
                if queue is None:
                    await start()
                await queue.put(message["bytes"])
            elif message.get("text") == "STOP_RECORDING":
                await finish()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[{session_id}] WebSocket 오류 발생: {e}")
    finally:
        print(f"[{session_id}] WebSocket 연결 종료됨")
        if task and not task.done():
            task.cancel()
        if channel:
            await channel.close()

    


#------------------------------------------------ 파일배치 미완


@router.post("/File")
async def transcribe_file(audio_file: UploadFile = File(...)):
    
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(audio_file.filename, audio_file.file, audio_file.content_type)
    )
    
    
    return {"recognized_text": transcript.text}

