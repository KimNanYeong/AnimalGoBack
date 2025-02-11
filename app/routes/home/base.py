from fastapi import APIRouter, HTTPException
import socket
from app.core.firebase import db
from firebase_admin import firestore

# ✅ FastAPI 라우터 생성
router = APIRouter()

# =============================
# 🔹 현재 개발용 PC 서버의 IP 주소 가져오기
# =============================
def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        return "Unknown"

# 🔹 기본 API 엔드포인트 (테스트용)
@router.get("/")
def read_root():
    """ 기본 API 엔드포인트 - 서버 정상 동작 확인용 """
    return {"message": "Hello, FastAPI!"}

# 🔹 Firestore에 개발용 서버 IP 주소 저장
@router.post("/register-server-ip")
def register_server_ip():
    try:
        server_ip = get_local_ip()
        server_ref = db.collection("server_info").document("development_pc")
        server_ref.set({"ip_address": server_ip, "registeredAt": firestore.SERVER_TIMESTAMP})
        return {"ip_address": server_ip, "message": "Server IP registered successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔹 Firestore에서 개발용 서버 IP 조회 API
@router.get("/get-server-ip")
def get_server_ip():
    try:
        server_ref = db.collection("server_info").document("development_pc").get()
        if not server_ref.exists:
            raise HTTPException(status_code=404, detail="Server IP not registered")

        server_data = server_ref.to_dict()
        return {"ip_address": server_data["ip_address"], "message": "Server IP retrieved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
