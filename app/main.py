import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ✅ Firestore 관련 모듈 불러오기
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.firebase import db  # Firestore 초기화 모듈

# ✅ 라우트 (API 엔드포인트) 불러오기
from app.routes.chat import router as chat_router  # 채팅 관련 API
from app.routes.clear_chat import router as clear_chat_router  # 채팅 기록 삭제 API
from app.routes.traits import router as traits_router  # 성격 데이터 관련 API
from app.routes.pets import router as pets_router  # 반려동물 관련 API
from app.routes import chat_list  # 채팅 리스트 API
from app.routes import chat_history  # ✅ 채팅 내역 조회 API 추가

# ✅ 현재 실행 중인 파일의 경로를 sys.path에 추가 (모듈 경로 문제 해결)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ✅ FastAPI 애플리케이션 생성
app = FastAPI()

# ✅ CORS 설정 (프론트엔드에서 API 호출 가능하도록 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (배포 시 특정 도메인으로 제한 가능)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, DELETE 등)
    allow_headers=["*"],  # 모든 요청 헤더 허용
)

# ✅ API 라우트 등록 (각 기능별 엔드포인트 연결)
app.include_router(chat_router)  # 채팅 API
app.include_router(clear_chat_router)  # 채팅 삭제 API
app.include_router(traits_router, prefix="/api")  # 성격 데이터 API
app.include_router(pets_router, prefix="/api")  # 반려동물 관리 API
app.include_router(chat_list.router)  # 채팅 리스트 API
app.include_router(chat_history.router)  # ✅ 채팅 내역 조회 API 추가

# ✅ 기본 루트 엔드포인트 (서버 상태 확인용)
@app.get("/")
def home():
    """백엔드 서버 상태 확인용 엔드포인트"""
    return {"message": "FastAPI 백엔드 실행 중!"}

# ✅ FastAPI 실행 (로컬 환경에서 직접 실행할 경우)
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
