import jwt
import bcrypt
import datetime
import logging
from fastapi import APIRouter, HTTPException, Form
from firebase_admin import firestore
from pydantic import BaseModel
from typing import Annotated
import os

# Ensure the log directory exists
log_directory = 'log'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# ✅ 로깅 설정 (시간 포함)
logger = logging.getLogger("login_logger")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.join(log_directory, 'login.log'))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Suppress debug messages from python_multipart
logging.getLogger("python_multipart").setLevel(logging.WARNING)

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

# ✅ 로그인 응답 모델 (Swagger 문서 개선)
class UserLoginResponse(BaseModel):
    access_token: str
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
):
    logger.info(f"Request received to login user: user_id={user_id}")

    try:
        # 🔹 Firestore에서 사용자 조회
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logger.warning(f"User not found: user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_doc.to_dict()
        stored_hashed_password = user_data.get("hashed_password")

        # 🔹 비밀번호 검증
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
            logger.warning(f"Invalid password for user_id={user_id}")
            raise HTTPException(status_code=401, detail="Invalid password")

        # 🔹 로그인 성공 → JWT 토큰 생성
        token_data = {"sub": user_id, "role": user_data.get("role", "user")}
        access_token = create_access_token(token_data, ACCESS_TOKEN_EXPIRE_MINUTES)

        # 🔹 Firestore에서 닉네임 필드 확인 (KeyError 방지)
        user_nickname = user_data.get("nickname") or user_data.get("user_nickname") or "Unknown"

        # 🔹 마지막 로그인 시간 업데이트
        user_ref.update({"last_login": firestore.SERVER_TIMESTAMP})

        response = UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            user_nickname=user_nickname,
            role=user_data.get("role", "user"),
            message="Login successful!"
        )
        logger.info(f"Response for user_id={user_id}: {response}")
        return response
    except Exception as e:
        logger.error(f"Error logging in user_id={user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))