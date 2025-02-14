from fastapi import APIRouter, HTTPException
import socket
# from app.core.firebase import db
from core.firebase import db

from firebase_admin import firestore

# ✅ FastAPI 라우터 생성
router = APIRouter()


# 🔹 기본 API 엔드포인트 (테스트용)
@router.get("/", summary="-",  tags=["Basic"], description="home")
def read_root():
    """ 기본 API 엔드포인트 - 서버 정상 동작 확인용 """
    return {"message": "Hello, FastAPI! - home -"}