import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from firebase_admin import firestore
from typing import Annotated

router = APIRouter()
db = firestore.client()

# 🔹 기본 저장 경로 (사용자별 폴더 적용)       ------------- 삭제 예정
BASE_STORAGE_FOLDER = "C:/animal-storage"  # ------------- 삭제 예정


# ==========================
# 🔹 캐릭터 닉네임 추가/수정 API (`/nickname`)
# ==========================
@router.post(
    "/nickname",
    summary="캐릭터 닉네임 추가/수정",
    description="입력된 `character_id`의 Firestore 문서에서 `nickname` 필드를 추가하거나 수정하는 API"
)
async def update_character_nickname(
    character_id: Annotated[str, Form(..., description="기존 캐릭터 ID (Existing character ID)")],
    nickname: Annotated[str, Form(..., description="새로운 또는 수정할 캐릭터 닉네임 (Character nickname)")],
):
    """
    - **character_id**: Firestore `characters` 문서에서 업데이트할 ID
    - **nickname**: 추가 또는 수정할 캐릭터 닉네임
    """
    try:
        # 🔹 Firestore에서 기존 characterId 문서 확인
        character_ref = db.collection("characters").document(character_id)
        character_doc = character_ref.get()

        if not character_doc.exists:
            raise HTTPException(status_code=404, detail="Character ID not found in Firestore")

        # 🔹 Firestore 문서 업데이트 (`nickname` 필드 추가/수정)
        character_ref.update({
            "nickname": nickname,  # 🔹 닉네임 업데이트
            "updatedAt": firestore.SERVER_TIMESTAMP,  # 🔹 업데이트된 시간 기록
        })

        return {
            "characterId": character_id,
            "nickname": nickname,
            "message": "Character nickname updated successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================  ------------- 삭제 예정
# 🔹 변환된 이미지 업로드 및 기존 `characterId` 문서 업데이트 (`user_id` 기반 최적화된 폴더 구조) ------------- 삭제 예정
# ==========================  ------------- 삭제 예정
# @router.post(
#     "/upload-character-image",
#     summary="변환된 캐릭터 이미지 업로드 (삭제 예정 - ComyUI 변환중 처리)",
#     description="변환된 캐릭터 이미지를 업로드하고 Firestore `characters` 문서에서 `character_path` 필드를 업데이트하는 API"
# )
async def upload_character_image(
    character_id: Annotated[str, Form(..., description="기존 캐릭터 ID (Existing character ID)")],
    file: UploadFile = File(..., description="업로드할 변환된 캐릭터 이미지 (Transformed character image file)")
):
    """
    - **character_id**: 기존 캐릭터 ID (Firestore `characters` 문서에서 업데이트할 ID)
    - **file**: 업로드할 변환된 캐릭터 이미지
    """
    try:
        # 🔹 Firestore에서 기존 characterId 문서 확인
        character_ref = db.collection("characters").document(character_id)
        character_doc = character_ref.get()

        if not character_doc.exists:
            raise HTTPException(status_code=404, detail="Character ID not found in Firestore")

        # 🔹 Firestore 문서에서 `user_id` 가져오기
        character_data = character_doc.to_dict()
        user_id = character_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=500, detail="User ID is missing in Firestore document")

        # 🔹 사용자별 저장 폴더 경로 생성
        user_folder = os.path.join(BASE_STORAGE_FOLDER, user_id, "characters")
        os.makedirs(user_folder, exist_ok=True)

        # 🔹 고유 파일명 생성
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        character_path = os.path.join(user_folder, unique_filename)

        # 🔹 파일 저장
        with open(character_path, "wb") as buffer:
            buffer.write(file.read())

        # 🔹 Firestore 문서 업데이트 (`character_path` 필드 변경)
        character_ref.update({
            "character_path": character_path,  # 🔹 사용자별 폴더에 저장된 경로 반영
            "updatedAt": firestore.SERVER_TIMESTAMP,  # 🔹 업데이트된 시간 기록
            "status": "completed"  # 🔹 상태 변경
        })

        return {
            "characterId": character_id,
            "userId": user_id,
            "character_path": character_path,
            "message": "Transformed character image updated successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
