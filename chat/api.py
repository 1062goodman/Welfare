import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware 

from graph import app 




server = FastAPI(
    title="대한민국 복지 정책 챗봇 API",
    description="RAG 기반 복지 정책 안내 챗봇 서버입니다."
)

# !!!!!!여기 추후 수정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처(바탕화면 파일 포함)에서의 접근을 허락함
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST 등 모든 통신 방식 허락
    allow_headers=["*"],  # 모든 데이터 헤더 허락
)


# 손님이 보낼 주문서(Request) 양식 정의 (Pydantic 사용)
class ChatRequest(BaseModel):
    session_id: str          # 사용자 구분용 ID (단톡방 번호 같은 역할)
    user_message: str        # 사용자가 입력한 질문

# 손님에게 줄 영수증(Response) 양식 정의
class ChatResponse(BaseModel):
    bot_reply: str           # 챗봇의 답변

# 엔드포인트(창구) 만들기
@server.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest):
    print(f"[{request.session_id}] 사용자 질문 수신: {request.user_message}")
    
    # LangGraph에 전달할 설정 (어떤 사용자의 대화 기록을 꺼낼지 지정)
    config = {"configurable": {"thread_id": request.session_id}}
    
    # 챗봇(app)에게 질문 던지기 (주방으로 전달)
    result_state = app.invoke(
        {"messages": [HumanMessage(content=request.user_message)]},
        config=config
    )
    
    # 챗봇이 만들어낸 마지막 답변 꺼내기
    final_message = result_state["messages"][-1].content
    
    # 포장해서(Response 형식) 손님에게 반환
    return ChatResponse(bot_reply=final_message)