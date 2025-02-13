import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from firebase_admin import firestore
from pydantic import BaseModel, Field
from typing import Annotated

router = APIRouter()
db = firestore.client()

# 🔹 기본 저장 경로 (사용자별 폴더 적용)
BASE_STORAGE_FOLDER = "C:/animal-storage"

# ==========================
# 🔹 응답 모델 (`original_path` 반영)
# ==========================
class ImageUploadResponse(BaseModel):
    characterId: str = Field(..., example="char_abc123", description="캐릭터의 고유 ID")
    original_path: str = Field(..., example="C:/animal-storage/user_abc123/originals/abcd-efgh.png", description="개발 서버에 저장된 원본 이미지 경로")
    appearance: str = Field(..., example="Golden fur, blue eyes", description="캐릭터의 외모 특징")
    personality: str = Field(..., example="Brave and energetic", description="캐릭터의 성격")
    animaltype: str = Field(..., example="Fox", description="동물 유형 (Animal type)")
    message: str = Field(..., example="Original image stored successfully on the server!", description="API 응답 메시지")

# ==========================
# 🔹 원본 이미지 업로드 API (`users` 컬렉션에서 `user_id` 존재 여부 체크)
# ==========================
@router.post(
    "/upload-original-image",
    summary="원본 이미지 업로드",
    description="사용자가 원본 동물 이미지를 업로드하고 Firestore `characters` 문서에 저장하는 API",
    response_model=ImageUploadResponse
)
async def upload_original_image(
    user_id: Annotated[str, Form(..., description="사용자 고유 ID (User's unique ID)")],
    appearance: Annotated[str, Form(..., description="캐릭터의 외모 특징 (Character's appearance)")],
    personality: Annotated[str, Form(..., description="캐릭터의 성격 (Character's personality)")],
    animaltype: Annotated[str, Form(..., description="동물 유형 (Animal type)")],
    file: UploadFile = File(..., description="업로드할 원본 동물 이미지 파일 (Original image file to upload)")
):
    """
    - **user_id**: 사용자 고유 ID (Firestore `users` 컬렉션에서 확인)
    - **appearance**: 캐릭터의 외모 설명
    - **personality**: 캐릭터의 성격 설명
    - **animaltype**: 동물 유형
    - **file**: 업로드할 원본 이미지 파일
    """
    try:
        # 🔹 Firestore에서 `users` 컬렉션에서 `user_id` 확인
        user_ref = db.collection("users").document(user_id)
        if not user_ref.get().exists:
            raise HTTPException(status_code=400, detail="User not found in Firestore")

        # 🔹 사용자별 저장 폴더 경로 생성
        user_folder = os.path.join(BASE_STORAGE_FOLDER, user_id, "originals")
        os.makedirs(user_folder, exist_ok=True)

        # 🔹 고유 파일명 생성
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        original_path = os.path.join(user_folder, unique_filename)

        # 🔹 파일 저장
        with open(original_path, "wb") as buffer:
            buffer.write(await file.read())

        # 🔹 Firestore의 `characters` 문서에 저장
        character_ref = db.collection("characters").document()
        character_ref.set({
            "userId": user_id,
            "original_path": original_path,  # 🔹 원본 이미지 경로 저장
            "appearance": appearance,
            "personality": personality,
            "animaltype": animaltype,
            "uploadedAt": firestore.SERVER_TIMESTAMP,
            "status": "pending"
        })

        return {
            "characterId": character_ref.id,
            "original_path": original_path,  # 🔹 응답에서도 `original_path` 반환
            "appearance": appearance,
            "personality": personality,
            "animaltype": animaltype,
            "message": "Original image stored successfully on the server!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
