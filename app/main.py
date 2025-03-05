import sys
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Firestore 관련 모듈 불러오기
import firebase_admin
from firebase_admin import credentials, firestore
from core import db
# from core.Mongo import connect_to_mongo, close_mongo_connection
from datetime import datetime

from datetime import datetime
# FAISS 벡터 DB 관련 모듈 추가
from vectorstore.faiss_init import ensure_faiss_directory


# from routes import (
#     chat_send_message_router, chat_history_router, chat_list_router, clear_chat_router,
#     characters_router, user_router, base_router, image_router, character_router,
#     register_router, login_router, show_image_router, create_router
# )

from routes import *

#웹소켓 추가
from routes.chat.websocket_chat import router as websocket_router  # WebSocket 라우트 추가
from routes.chat.websocket_chat_list import router as websocket_chat_list_router
from starlette.middleware.trustedhost import TrustedHostMiddleware

from middleware.JWTMiddleWare import JWTMiddleware
from middleware.LoggerMiddleWare import LoggerMiddleware
from starlette.middleware.sessions import SessionMiddleware

# personality 의존성 주입
from util.PersonalityUtil import load_personality

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.cloud.firestore_v1.base_collection")

import logging
logging.getLogger("google.cloud.firestore").setLevel(logging.ERROR)  # Firestore 경고 숨김


app = FastAPI()

# 현재 실행 중인 파일의 경로를 sys.path에 추가 (모듈 경로 문제 해결)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# CORS 설정 (프론트엔드에서 API 호출 가능하도록 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (배포 시 특정 도메인으로 제한 가능)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, DELETE 등)
    allow_headers=["*"],  # 모든 요청 헤더 허용
)
# 그 다음 세션 미들웨어
# secret_key = os.getenv("SECRET_KEY")
# if not secret_key:
#     raise ValueError("SECRET_KEY environment variable is not set")

# app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.add_middleware(LoggerMiddleware)
# app.add_middleware(JWTMiddleware)

# 서버 시작 시 FAISS 저장 디렉토리 자동 생성
ensure_faiss_directory()

# API 라우트 등록 (각 기능별 엔드포인트 연결)
app.include_router(user_router)
app.include_router(chat_send_message_router, prefix="/chat")
app.include_router(chat_history_router, prefix="/chat")
app.include_router(chat_list_router, prefix="/chat")
app.include_router(clear_chat_router, prefix="/chat")
app.include_router(characters_router, prefix="/pets")
app.include_router(base_router, prefix="/home")
app.include_router(image_router, prefix="/home")
app.include_router(character_router, prefix="/home")
app.include_router(register_router, prefix="/home")
app.include_router(login_router, prefix="/home")
app.include_router(show_image_router, prefix="/image")
app.include_router(create_router, prefix="/create")

app.include_router(chat_basic_router, prefix="/home")
# ✅ WebSocket 라우트 등록
app.include_router(websocket_router)
app.include_router(websocket_chat_list_router, prefix="/chat")

# ✅ WebSocket을 위한 허용된 호스트 설정 추가
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*", "localhost", "127.0.0.1", "192.168.0.1", " 122.46.89.124"]
)

app.include_router(village_router)

@app.on_event("startup")
async def init():
    await load_personality()
    # await connect_to_mongo()

# @app.on_event('shutdown')
# async def db_close():
#     await close_mongo_connection()

# FastAPI 실행 (로컬 환경에서 직접 실행할 경우)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000)