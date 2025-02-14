from fastapi import APIRouter, HTTPException
from services.characters_service import create_character, delete_character
from schemas.characters import CharacterCreateRequest, CharacterResponse  # ✅ 스키마 가져오기
from db.faiss_db import delete_faiss_index  # ✅ FAISS 벡터 삭제 함수 추가

router = APIRouter()

@router.post("/characters/", response_model=CharacterResponse)
def create_character_api(request: CharacterCreateRequest):
    """🔥 캐릭터 생성 API"""
    character_data = create_character(
        user_id=request.user_id,
        charac_id=request.charac_id,
        nickname=request.nickname,
        animaltype=request.animaltype,
        personality=request.personality
    )
    
    return character_data

@router.delete("/characters/{user_id}/{charac_id}")
async def remove_character(user_id: str, charac_id: str):
    """🔥 캐릭터 삭제 API (채팅방 + FAISS 데이터 함께 삭제)"""

    # ✅ Firestore에서 캐릭터 및 채팅방 삭제
    delete_result = delete_character(user_id, charac_id)

    # ✅ 조건문 수정 (정확한 문구 확인)
    if "message" in delete_result and "deleted successfully" in delete_result["message"]:
        chat_id = f"{user_id}_{charac_id}"
        # print(f"🟢 FAISS 삭제 실행: {chat_id}")
        delete_faiss_index(chat_id)  # 🔥 FAISS 벡터 삭제 추가

    return delete_result