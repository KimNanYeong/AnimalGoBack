from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

# ✅ Firestore 클라이언트 생성
db = firestore.client()

# ✅ FastAPI 라우터 설정
router = APIRouter()

@router.delete("/chat/{chat_id}/delete")
async def delete_chat(chat_id: str):
    """
    🔥 특정 채팅방을 삭제하는 API 🔥
    - Firestore에서 `chats/{chat_id}` 문서 삭제
    - 해당 채팅방의 messages 컬렉션도 삭제
    """

    try:
        chat_ref = db.collection("chats").document(chat_id)
        chat_doc = chat_ref.get()

        if not chat_doc.exists:
            raise HTTPException(status_code=404, detail="Chat not found")

        # ✅ messages 컬렉션 삭제
        messages_ref = chat_ref.collection("messages").stream()
        for message in messages_ref:
            message.reference.delete()

        # ✅ 채팅방 문서 삭제
        chat_ref.delete()

        return {"message": f"Chat {chat_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))