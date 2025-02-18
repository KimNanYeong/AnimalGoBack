import jwt
import bcrypt
import datetime
from fastapi import APIRouter, HTTPException, Form, Request
from firebase_admin import firestore
from pydantic import BaseModel
from typing import Annotated
import os

router = APIRouter()
db = firestore.client()

# 🔹 JWT 설정
SECRET_KEY = "mysecretkey123"  # 🔥 환경 변수 또는 Firebase 설정에서 불러올 것
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 🔹 1시간 동안 유효
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# 🔹 JWT 토큰 생성 함수
def create_access_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ✅ 로그인 응답 모델 (Swagger 문서 개선)
class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    user_nickname: str
    role: str
    message: str

class ErrorResponse(BaseModel):
    detail: str

# ==========================
# 🔹 로그인 API (JWT 적용) - KeyError 수정
# ==========================
@router.post(
    "/login",
    tags=["Auth"],
    summary="사용자 로그인",
    response_model=UserLoginResponse,
    responses={
        200: {"description": "로그인 성공", "model": UserLoginResponse},
        404: {"description": "사용자를 찾을 수 없음", "model": ErrorResponse},
        401: {"description": "잘못된 비밀번호", "model": ErrorResponse},
        500: {"description": "서버 내부 오류", "model": ErrorResponse}
    }
)
def login_user(
    user_id: Annotated[str, Form(..., description="로그인할 사용자 ID (Form 데이터)")],
    password: Annotated[str, Form(..., description="로그인할 사용자 비밀번호 (Form 데이터)")],
    # request : Request
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
        refresh_token = create_access_token(token_data,REFRESH_TOKEN_EXPIRE_MINUTES)

        # 🔹 Firestore에서 닉네임 필드 확인 (KeyError 방지)
        user_nickname = user_data.get("nickname") or user_data.get("user_nickname") or "Unknown"

        # 🔹 마지막 로그인 시간 업데이트
        # user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})

        # 박건희 로그인 토큰 디비 저장 추가
        user_ref.update({
            "last_login" : firestore.SERVER_TIMESTAMP,
            "access_token" : access_token,
            "refresh_token" : refresh_token
        })

        print(refresh_token)
        return UserLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user_id=user_id,
            user_nickname=user_nickname,
            role=user_data.get("role", "user"),
            message="Login successful!"
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))