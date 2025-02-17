from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

# ✅ FastAPI 라우터 생성
router = APIRouter()

# ✅ Firestore 클라이언트 연결
db = firestore.client()

@router.get("/chat/list/{user_id}",
            tags=["chat"], 
            summary="사용자의 채팅방 목록 조회", 
            description="특정 사용자의 모든 채팅방 리스트를 반환합니다.")
async def get_chat_list(user_id: str):
    """
    ✅ 특정 사용자의 모든 채팅방 리스트를 반환하는 API
    - Firestore `chats` 컬렉션에서 `chat_id`가 `user_id_`로 시작하는 문서들을 조회
    - `last_active_at` 기준으로 정렬하여 최신 채팅이 위로 오도록 반환
    """

    try:
        # ✅ Firestore에서 채팅방을 `last_active_at` 기준으로 정렬하여 가져오기
        chats_ref = db.collection("chats") \
            .where("chat_id", ">=", f"{user_id}-") \
            .where("chat_id", "<", f"{user_id}-\uf8ff") \
            .order_by("last_active_at", direction=firestore.Query.DESCENDING) \
            .stream()

        chat_list = []

        for chat in chats_ref:
            chat_data = chat.to_dict()
            chat_id = chat.id  # 문서 ID

            last_message = chat_data.get("last_message", {
                "content": "",
                "sender": "",
                "timestamp": ""
            })

            chat_list.append({
                "chat_id": chat_id,
                "nickname": chat_data.get("nickname", ""),
                "personality": chat_data.get("personality", ""),
                "create_at": chat_data.get("create_at", ""),
                "last_active_at": chat_data.get("last_active_at", ""),
                "last_message": last_message
            })

        if not chat_list:
            raise HTTPException(status_code=404, detail="No chats found for this user.")

        return {"chats": chat_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))