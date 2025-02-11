import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import uvicorn

# ✅ Firestore 관련 모듈 불러오기
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.firebase import db  # Firestore 초기화 모듈

# ✅ 라우트 (API 엔드포인트) 불러오기
from app.routes.chat.chat import router as chat_router
from app.routes.chat.chat_history import router as chat_history_router
from app.routes.chat.chat_list import router as chat_list_router
from app.routes.chat.clear_chat import router as clear_chat_router

from app.routes.pets.pets import router as pets_router
from app.routes.pets.pet_traits import router as traits_router

from app.routes.users.user import router as user_router
from app.routes.home.base import router as base_router
from app.routes.home.image_upload import router as image_router
from app.routes.home.character import router as character_router

# ✅ 현재 실행 중인 파일의 경로를 sys.path에 추가 (모듈 경로 문제 해결)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from routes.home import main_router  # 🔹 home.py에서 router만 가져오기

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
app.include_router(chat_router, prefix="/chat")
app.include_router(chat_history_router, prefix="/chat")
app.include_router(chat_list_router, prefix="/chat")
app.include_router(clear_chat_router, prefix="/chat")

app.include_router(pets_router, prefix="/pets")
app.include_router(traits_router, prefix="/pets")

# app.include_router(user_router, prefix="/users")
app.include_router(base_router, prefix="/home")
app.include_router(image_router, prefix="/home")
app.include_router(character_router, prefix="/home")


# ✅ FastAPI 실행 (로컬 환경에서 직접 실행할 경우)
# FastAPI 앱 생성
app = FastAPI(title="FastAPI with Firestore")
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
