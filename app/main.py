import sys
import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from starlette.background import BackgroundTask

# Firestore 관련 모듈 불러오기
import firebase_admin
from firebase_admin import credentials, firestore
from core import db

# FAISS 벡터 DB 관련 모듈 추가
from db.faiss_db import ensure_faiss_directory, load_existing_faiss_indices

# from routes import (
#     chat_send_message_router, chat_history_router, chat_list_router, clear_chat_router,
#     characters_router, user_router, base_router, image_router, character_router,
#     register_router, login_router, show_image_router, create_router
# )

from routes import *

log_directory = 'log'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(filename='log/info.log', level=logging.DEBUG)

def log_info(req_method, req_url, req_headers, req_body, res_status, res_headers, res_body):
    logging.info("")
    logging.info(f"Request Method: {req_method}")
    logging.info(f"Request URL: {req_url}")
    logging.info(f"Request Headers: {req_headers}")
    logging.info(f"Request Body: {req_body}")
    logging.info(f"Response Status: {res_status}")
    logging.info(f"Response Headers: {res_headers}")
    logging.info(f"Response Body: {res_body}")
    logging.info("")

app = FastAPI()

@app.middleware('http')
async def log_middleware(request: Request, call_next):
    req_method = request.method
    req_url = str(request.url)
    req_headers = dict(request.headers)
    req_body = await request.body()

    response = await call_next(request)

    res_status = response.status_code
    res_headers = dict(response.headers)
    res_body = b''
    async for chunk in response.body_iterator:
        res_body += chunk

    task = BackgroundTask(log_info, req_method, req_url, req_headers, req_body, res_status, res_headers, res_body)
    return Response(content=res_body, status_code=res_status,
                    headers=res_headers, media_type=response.media_type, background=task)

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

# 서버 시작 시 FAISS 저장 디렉토리 자동 생성
ensure_faiss_directory()

# 서버 시작 시 기존 FAISS 인덱스 자동 로드
load_existing_faiss_indices()

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

# FastAPI 실행 (로컬 환경에서 직접 실행할 경우)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000)