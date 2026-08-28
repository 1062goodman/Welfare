import os
import uuid
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from langchain_core.messages import HumanMessage


from graph import app 
from tasks import session_timestamps

open_api=os.getenv("OPENAI")
router = APIRouter()


# 손님이 보낼 주문서(Request) 양식 정의 (Pydantic 사용)
class ChatRequest(BaseModel):
    session_id: str          # 사용자 구분용 ID (단톡방 번호 같은 역할)
    user_message: str        # 사용자가 입력한 질문

# 손님에게 줄 영수증(Response) 양식 정의
class ChatResponse(BaseModel):
    bot_reply: str           # 챗봇의 답변


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
    
    # 포장해서(Response 형식) 손님에게 반환
    return ChatResponse(bot_reply=final_message)




class ChatRequest(BaseModel):
    session_id: str          # 사용자 구분용 ID (단톡방 번호 같은 역할)
   


# 서버체크------------------------------------------------
@router.get("/Health", response_model=bool)
def health_check():
    return True


# 음성인식------------------------------------------------ 지금은 파일배치. 추후에 리얼타임 스트리밍으로 고도화
import openai
from fastapi import UploadFile, File

client = openai.OpenAI(api_key=open_api)


@router.post("/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=(audio_file.filename, audio_file.file, audio_file.content_type)
    )
    
    
    return {"recognized_text": transcript.text}