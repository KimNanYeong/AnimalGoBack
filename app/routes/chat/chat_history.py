from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime, timezone

# ✅ Firestore 클라이언트 연결
db = firestore.client()

# ✅ FastAPI 라우터 설정
router = APIRouter()

@router.get("/chat/history/{chat_id}")
async def get_chat_history(chat_id: str):
    """
    ✅ 특정 채팅방의 채팅 메시지 리스트를 반환하는 API
    - Firestore `chats/{chat_id}/messages` 컬렉션에서 최근 메시지를 가져옴
    - 최대 50개 메시지를 `timestamp` 기준 내림차순 정렬하여 반환
    """

    try:
        # ✅ Firestore에서 해당 채팅방 존재 여부 확인
        chat_ref = db.collection("chats").document(chat_id)
        chat_doc = chat_ref.get()

        if not chat_doc.exists:
            raise HTTPException(status_code=404, detail="Chat room not found")

        # ✅ Firestore에서 최근 50개 메시지 가져오기
        messages_ref = chat_ref.collection("messages").order_by(
            "timestamp", direction=firestore.Query.ASCENDING
        ).limit(50)

        messages = []
        for msg in messages_ref.stream():
            msg_data = msg.to_dict()
            messages.append({
                "content": msg_data.get("content", ""),
                "sender": msg_data.get("sender", ""),
                "timestamp": msg_data.get("timestamp", "")
            })

        if not messages:
            raise HTTPException(status_code=404, detail="No messages found in this chat room.")

        return {"chat_id": chat_id, "messages": messages}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
