import jwt
import bcrypt
import datetime
from fastapi import APIRouter, HTTPException, Form, Depends
from firebase_admin import firestore
from pydantic import BaseModel
from typing import Annotated

router = APIRouter()
db = firestore.client()

# 🔹 JWT 설정
SECRET_KEY = "mysecretkey123"  # 🔥 환경 변수 또는 Firebase 설정에서 불러올 것
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 🔹 1시간 동안 유효

# 🔹 JWT 토큰 생성 함수
def create_access_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 🔹 로그인 요청 모델
class UserLoginRequest(BaseModel):
    user_id: str
    password: str

# ==========================
# 🔹 로그인 API (JWT 적용)
# ==========================
@router.post("/login", summary="사용자 로그인 (JWT 적용)")
def login_user(
    user_id: Annotated[str, Form(...)],
    password: Annotated[str, Form(...)],
):
    try:
        # 🔹 Firestore에서 사용자 조회
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_doc.to_dict()
        stored_hashed_password = user_data.get("hashed_password")

        # 🔹 비밀번호 검증
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid password")

        # 🔹 로그인 성공 → JWT 토큰 생성
        token_data = {"sub": user_id, "role": user_data.get("role", "user")}
        access_token = create_access_token(token_data, ACCESS_TOKEN_EXPIRE_MINUTES)

        # 🔹 마지막 로그인 시간 업데이트
        user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "nickname": user_data["nickname"],
            "role": user_data.get("role", "user"),
            "message": "Login successful!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
