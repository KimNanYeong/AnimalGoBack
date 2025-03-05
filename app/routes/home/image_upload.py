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
    characterId: str = Field(..., example="user123-Fox001", description="캐릭터의 고유 ID")
    original_path: str = Field(..., example="C:/animal-storage/user_abc123/originals/abcd-efgh.png", description="개발 서버에 저장된 원본 이미지 경로")
    appearance: str = Field(..., example="Golden fur, blue eyes", description="캐릭터의 외모 특징")
    personality: str = Field(..., example="Brave and energetic", description="캐릭터의 성격")
    animaltype: str = Field(..., example="Fox", description="동물 유형 (Animal type)")
    message: str = Field(..., example="Original image stored successfully on the server!", description="API 응답 메시지")

def get_document_id_by_field(collection_name, field_name, value):
    # 🔹 Firestore에서 특정 필드 값을 기준으로 문서 조회
    query = db.collection(collection_name).where(field_name, "==", value).stream()

    # 🔹 첫 번째 결과만 반환 (여러 개일 경우 첫 번째만 선택)
    for doc in query:
        print(f"✅ Found Document ID: {doc.id}")
        return doc.id

    # 🔹 결과가 없을 경우
    print("❌ 해당 값에 해당하는 문서를 찾을 수 없습니다.")
    return None

# ==========================
# 🔹 원본 이미지 업로드 API (`characters` 문서명을 `{user_id}-{animaltype}{번호}`로 자동 생성)
# ==========================
@router.post(
    "/upload-original-image",
    summary="원본 이미지 업로드", tags=["Basic"],
    description="사용자가 원본 동물 이미지를 업로드하고 Firestore `characters` 문서명을 `{user_id}-{animaltype}{번호}` 형식으로 저장하는 API",
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
        
        appearance_id = get_document_id_by_field("appearance_traits", "korean", appearance)
        personality_id = get_document_id_by_field("personality_traits", "name", personality)
        animals_id = get_document_id_by_field("animals", "korean", animaltype)

        # 🔹 해당 `user_id`와 `animaltype (입력 한글) > animals_id (영문)`을 가진 캐릭터id 보유 개수 조회
        characters_ref = db.collection("characters")
        existing_characters = characters_ref.where("user_id", "==", user_id).where("animaltype", "==", animals_id).stream()
        
        character_count = sum(1 for _ in existing_characters) + 1  # 기존 개수 + 1

        # 🔹 `{user_id}-{animaltype}{번호}` 형식의 문서명 생성
        character_id = f"{user_id}-{animals_id}{character_count:03d}"  # 001, 002, 003 ...

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
        character_ref = db.collection("characters").document(character_id)  # 🔹 문서명 지정
        character_ref.set({
            "user_id": user_id,
            "original_path": original_path,  # 🔹 원본 이미지 경로 저장
            "appearance": appearance_id,
            "personality": personality_id,
            "animaltype": animals_id,
            "create_at": firestore.SERVER_TIMESTAMP,  # 🔹 생성 시각 추가
            "status": "pending"
        })

        # 🔹 Firestore의 `affinity` 컬렉션에 친밀도 데이터 추가
        affinity_ref = db.collection("affinity").document(character_id)
        affinity_ref.set({
            "character_id": character_id,
            "user_id": user_id,
            "points": 50,  # 🔹 초기 친밀도 포인트 설정
            "level": 1,  # 🔹 기본 레벨 설정
            "last_interaction": firestore.SERVER_TIMESTAMP  # 🔹 마지막 상호작용 시간 저장
        })

        response = {
            "characterId": character_id,  # 🔹 `{user_id}-{animaltype}{번호}` 반환
            "original_path": original_path,  # 🔹 응답에서도 `original_path` 반환
            "appearance": appearance_id,
            "personality": personality_id,
            "animaltype": animals_id,
            "message": "Original image stored successfully on the server!"
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))