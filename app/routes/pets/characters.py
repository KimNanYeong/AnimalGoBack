from fastapi import APIRouter, HTTPException
from services.characters_service import delete_character
from schemas.characters import CharacterCreateRequest, CharacterResponse  # ✅ 스키마 가져오기
from vectorstore.faiss_cleanup import delete_faiss_index  # ✅ FAISS 벡터 삭제 함수 추가

router = APIRouter()

@router.delete("/characters/{user_id}/{charac_id}",
               tags=["chat"], 
               summary="사용자의 캐릭터 삭제", 
               description="특정 사용자의 캐릭터를 삭제합니다.")
async def remove_character(user_id: str, charac_id: str):
    """🔥 캐릭터 삭제 API (채팅방 + FAISS 데이터 함께 삭제)"""

    # ✅ Firestore에서 캐릭터 및 채팅방 삭제
    delete_result = delete_character(user_id, charac_id)

    # ✅ 조건문 수정 (정확한 문구 확인)
    if "message" in delete_result and "deleted successfully" in delete_result["message"]:
        chat_id = f"{user_id}-{charac_id}"
        # print(f"🟢 FAISS 삭제 실행: {chat_id}")
        delete_faiss_index(chat_id)  # 🔥 FAISS 벡터 삭제 추가

    return delete_result