import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv
from fastapi.middleware.cors import CORSMiddleware 
import asyncio


# 환경변수 
load_dotenv(find_dotenv())

#
from graph import app
from api import router
from tasks import clean_expired_session



@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    cleaner_task = asyncio.create_task(session_cleaner_task())
    
    yield  
    
    cleaner_task.cancel()


server = FastAPI(
    title="대한민국 복지 정책 챗봇 API",
    description="RAG 기반 복지 정책 안내 챗봇 서버입니다.",
    lifespan=lifespan
)

origins = [
    "https://my-react-native-web.com", # (웹으로 배포할 경우) 실제 도메인
    "http://localhost:3000",           # 웹 로컬 테스트용
    "http://localhost:8081",           # React Native(Metro) 로컬 테스트용
]

# !!!!!!여기 추후 수정
server.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 모든 출처(바탕화면 파일 포함)에서의 접근을 허락함
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # GET, POST 등 모든 통신 방식 허락
    allow_headers=["Content-Type", "Authorization"],  # 모든 데이터 헤더 허락
)

server.include_router(router)


    
async def session_cleaner_task():
    while True:
        clean_expired_session(app.memory)
        await asyncio.sleep(60 * 60)
