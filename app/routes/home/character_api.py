import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from firebase_admin import firestore
from typing import Annotated, List, Optional
from pydantic import BaseModel

# ✅ 로깅 설정

router = APIRouter()
db = firestore.client()

BASE_STORAGE_FOLDER = "C:/animal-storage"  # ------------- 삭제 예정

class CharacterResponse(BaseModel):
    character_id: str
    nickname: str
    character_path: Optional[str] = None
    image_url: Optional[str] = None

class CharactersListResponse(BaseModel):
    user_id: str
    characters: List[CharacterResponse]

class ErrorResponse(BaseModel):
    detail: str

# 🔹 응답 모델 정의
class AnimalResponse(BaseModel):
    id: str  # 🔹 Firestore 문서 ID (예: "dog", "cat")
    korean: str  # 🔹 한글 이름 (예: "개", "고양이")

class AnimalsListResponse(BaseModel):
    animals: List[AnimalResponse]  # 🔹 리스트 응답 구조

# ================================================================
# 🔹 캐릭터 닉네임 추가/수정 API (/nickname) + 채팅방 자동 생성 추가
# ================================================================
@router.post(
    "/nickname",
    summary="캐릭터 닉네임 추가/수정 및 채팅방 자동 생성",  tags=["Basic"],
    description="입력된 character_id의 Firestore 문서에서 nickname을 추가하거나 수정하고, chats 컬렉션에 채팅방을 자동 생성하는 API"
)
async def update_character_nickname(
    character_id: Annotated[str, Form(..., description="기존 캐릭터 ID (Existing character ID)")],
    nickname: Annotated[str, Form(..., description="새로운 또는 수정할 캐릭터 닉네임 (Character nickname)")],
):

    try:
        # 🔹 Firestore에서 기존 캐릭터 문서 확인
        character_ref = db.collection("characters").document(character_id)
        character_doc = character_ref.get()
        
        if not character_doc.exists:
            raise HTTPException(status_code=404, detail="Character ID not found in Firestore")
        
        # 🔹 캐릭터 데이터 가져오기
        character_data = character_doc.to_dict()
        user_id = character_data.get("user_id")
        status = character_data.get("status", "unknown")  # 기본값 "unknown" 설정
        character_path = character_data.get("character_path", "").strip()  # 기본값 빈 문자열 설정

        if not user_id:
            raise HTTPException(status_code=500, detail="User ID is missing in Firestore document")

        # ✅ 캐릭터 `status`가 `pending`이거나 `character_path`가 없으면 닉네임 등록 불가
        # if status == "pending" or not character_path:
        #     raise HTTPException(status_code=400, detail="캐릭터 생성 전으로 닉네임을 등록할 수 없습니다")

        # 🔹 캐릭터 닉네임 업데이트
        character_ref.update({
            "nickname": nickname,  # 🔹 닉네임 업데이트
            "nickname_create_at": firestore.SERVER_TIMESTAMP,  # 🔹 업데이트된 시간 기록
        })

        # 🔹 채팅방 문서 참조 생성
        chat_ref = db.collection("chats").document(character_id)
        chat_doc = chat_ref.get()

        # ✅ 채팅방이 없을 경우 생성
        if not chat_doc.exists:
            chat_data = {
                "chat_id": character_id,
                "user_id": user_id,
                "nickname": nickname,
                "personality": character_data.get("personality", "unknown"),
                "animaltype": character_data.get("animaltype", "unknown"),
                "create_at": firestore.SERVER_TIMESTAMP,
                "last_active_at": firestore.SERVER_TIMESTAMP,
                "last_message": None
            }
            chat_ref.set(chat_data)  # 🔹 Firestore에 채팅방 저장

        response = {
            "characterId": character_id,
            "nickname": nickname,
            "chat_created": not chat_doc.exists,  # ✅ 채팅방 생성 여부 반환
            "message": "Character nickname updated successfully!"
        }
        
        return response
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Form 데이터 기반 캐릭터 목록 조회 API (completed 상태만 필터링, personality & animaltype 제외)
@router.post(
    "/characters",
    summary="특정 user 의 '완료된' 캐릭터 목록 조회",  tags=["Basic"],
    response_model=CharactersListResponse,
    responses={
        200: {"description": "완료된 캐릭터 목록 반환 또는 보유 캐릭터 없음 메시지", "model": CharactersListResponse},
        500: {"description": "서버 내부 오류", "model": ErrorResponse}
    }
)
async def get_user_characters(
    user_id: str = Form(..., description="조회할 사용자의 user_id (Form 데이터)")
):
    

    try:
        # 🔹 Firestore에서 `user_id`가 일치하고 `status == "completed"`인 문서 조회
        characters_ref = db.collection("characters").where("user_id", "==", user_id).where("status", "==", "completed")
        characters_docs = characters_ref.stream()

        characters_list: List[CharacterResponse] = []
        for doc in characters_docs:
            character_data = doc.to_dict()
            character_id = doc.id

            #닉네임 없는 경우 미출력 추가 박건희
            if character_data.get("nickname"):
                continue

            # 🔹 이미지 URL 생성 (기본 경로 포함)
            character_path = character_data.get("character_path")
            image_url = None
            if character_path:
                if character_path.startswith("http"):  # ✅ Firebase Storage URL이면 그대로 사용
                    image_url = character_path
                else:
                    # ✅ 로컬 이미지 파일이면 접근 가능한 URL로 변환
                    base_url = "http://127.0.0.1:8000/static/images/"
                    image_url = f"{base_url}{character_path.split('/')[-1]}"

            # 🔹 응답에서 personality, animaltype 필드 제외
            characters_list.append(CharacterResponse(
                character_id=character_id,
                nickname=character_data.get("nickname", "Unknown"),
                character_path=character_path,
                image_url=image_url
            ))

        # ✅ 캐릭터가 없을 경우 200 OK 반환 + "보유중인 캐릭터가 없습니다." 메시지
        if not characters_list:
            response = CharactersListResponse(user_id=user_id, characters=[], message="보유중인 캐릭터가 없습니다.")
            return response

        response = CharactersListResponse(user_id=user_id, characters=characters_list, message="완료된 캐릭터 목록 조회 성공")
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def upload_character_image(
    character_id: Annotated[str, Form(..., description="기존 캐릭터 ID (Existing character ID)")],
    file: UploadFile = File(..., description="업로드할 변환된 캐릭터 이미지 (Transformed character image file)")
):

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

        response = {
            "characterId": character_id,
            "user_id": user_id,
            "character_path": character_path,
            "message": "Transformed character image updated successfully!"
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🔹 Firestore `animals` 컬렉션 조회 API
@router.get(
    "/animals",
    summary="동물 목록 조회",  tags=["Basic"],
    description="Firestore `animals` 컬렉션에서 동물 목록을 조회하여 리스트로 반환하는 API.",
    response_model=AnimalsListResponse,
    responses={
        200: {"description": "동물 목록 조회 성공"},
        500: {"description": "서버 내부 오류"}
    }
)
async def get_animals():

    try:
        # 🔹 Firestore에서 `animals` 컬렉션의 모든 문서 조회
        animals_ref = db.collection("animals").stream()
        animals_list = [{"id": doc.id, **doc.to_dict()} for doc in animals_ref]

        response = {"animals": animals_list}
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))