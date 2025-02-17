from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from db.faiss_db import delete_faiss_index  # ✅ 추가


# ✅ Firestore 클라이언트 생성
db = firestore.client()

# ✅ FastAPI 라우터 설정
router = APIRouter()

@router.delete("/delete_chat/{chat_id}",
               tags=["chat"], 
               summary="채팅방 삭제", 
               description="특정 채팅방을 삭제합니다.")
async def delete_chat(chat_id: str):
    """
    🔥 채팅방 삭제 API
    - Firestore에서 채팅방과 모든 메시지 삭제
    - FAISS 벡터 DB에서도 해당 채팅방 데이터 삭제
    """

    # ✅ Firestore에서 채팅방 문서 및 모든 메시지 삭제
    chat_ref = db.collection("chats").document(chat_id)
    messages_ref = chat_ref.collection("messages")

    try:
        # ✅ Firestore에서 메시지 삭제
        messages = messages_ref.stream()
        for msg in messages:
            msg.reference.delete()

        # ✅ Firestore에서 채팅방 삭제
        chat_ref.delete()

        # ✅ FAISS 벡터 DB에서 해당 채팅방의 벡터 삭제
        delete_faiss_index(chat_id)  # 🔥 FAISS 파일 삭제

        return {"message": f"✅ 채팅방 {chat_id} 및 관련 데이터가 삭제되었습니다."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"🚨 채팅방 삭제 중 오류 발생: {str(e)}")