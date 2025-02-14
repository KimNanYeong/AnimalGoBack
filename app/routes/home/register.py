import bcrypt
from fastapi import APIRouter, HTTPException, Form, Depends
from firebase_admin import firestore
from pydantic import BaseModel, Field
from typing import Annotated

router = APIRouter()
db = firestore.client()

# ==========================
# 🔹 비밀번호 해싱 및 검증 함수
# ==========================
def hash_password(password: str) -> str:
    """ 비밀번호 해싱 """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ 입력된 비밀번호와 저장된 해시된 비밀번호를 비교 """
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ==========================
# 🔹 회원가입 API (폼 입력 지원)
# ==========================
@router.post("/register", tags=["Auth"], summary="회원가입", description="사용자가 회원가입을 수행하고 Firestore에 저장하는 API")
def register_user(
    user_id: Annotated[str, Form(..., description="사용자 고유 ID (User's unique ID)")],
    password: Annotated[str, Form(..., description="사용자 비밀번호 (Password for authentication)")],
    confirm_password: Annotated[str, Form(..., description="비밀번호 확인 (Confirm password)")],
    user_nickname: Annotated[str, Form(..., description="사용자 닉네임 (User's nickname)")]
):
    """
    - **user_id**: 사용자 고유 ID (중복 불가)
    - **password**: 비밀번호 (암호화 후 저장)
    - **confirm_password**: 비밀번호 확인 (password와 동일해야 함)
    - **user_nickname**: 사용자 닉네임
    """
    try:
        # 비밀번호 일치 확인
        if password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        # Firestore에서 user_id 중복 체크
        user_ref = db.collection("users").document(user_id)
        if user_ref.get().exists:
            raise HTTPException(status_code=400, detail="User ID already exists")

        # 비밀번호 해싱
        hashed_pw = hash_password(password)

        # Firestore에 사용자 정보 저장
        user_ref.set({
            "user_nickname": user_nickname,
            "hashed_password": hashed_pw,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        return {"userId": user_id, "message": f"User {user_nickname} registered successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# # ==========================
# # 🔹 (간단) 로그인 API (폼 입력 지원)
# # ==========================
# @router.post("/login", tags=["Auth"], summary="(간단) 로그인", description="사용자가 로그인하여 인증을 수행하는 API")
# def login_user(
#     user_id: Annotated[str, Form(..., description="사용자 고유 ID (User's unique ID)")],
#     password: Annotated[str, Form(..., description="사용자 비밀번호 (Password for authentication)")]
# ):
#     """
#     - **user_id**: 사용자 고유 ID
#     - **password**: 사용자가 입력한 비밀번호
#     """
#     try:
#         # Firestore에서 사용자 찾기
#         user_doc = db.collection("users").document(user_id).get()
#         if not user_doc.exists:
#             raise HTTPException(status_code=404, detail="User not found")

#         user_data = user_doc.to_dict()
#         stored_hashed_password = user_data.get("hashed_password")

#         # 비밀번호 검증
#         if not verify_password(password, stored_hashed_password):
#             raise HTTPException(status_code=401, detail="Invalid password")

#         return {"userId": user_id, "user_nickname": user_data["user_nickname"], "message": "Login successful!"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
