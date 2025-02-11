from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

# ✅ Firestore 클라이언트 생성
db = firestore.client()

# ✅ FastAPI 라우터 설정
router = APIRouter()

@router.delete("/chat/{chat_id}/clear_messages")
async def clear_chat_messages(chat_id: str):
    """
    🔥 특정 채팅방의 모든 메시지를 삭제하는 API 🔥
    
    - `chat_id`에 해당하는 채팅방의 `messages` 컬렉션을 가져와서 모든 문서를 삭제합니다.
    - 삭제가 완료되면 성공 메시지를 반환합니다.
    - Firestore에서 문서를 개별적으로 삭제해야 하므로 `stream()`을 사용하여 하나씩 삭제합니다.
    - 예외 발생 시 500 에러를 반환합니다.
    
    📌 **사용 예시 (프론트엔드 요청)**
    ```http
    DELETE /chat/{chat_id}/clear_messages
    ```
    """
    try:
        # ✅ Firestore에서 해당 `chat_id`의 채팅방 참조
        chat_doc = db.collection("chats").document(chat_id)
        messages_ref = chat_doc.collection("messages")  # 하위 컬렉션 메시지 가져오기
        
        # ✅ 모든 메시지를 가져와서 하나씩 삭제
        docs = messages_ref.stream()
        for doc in docs:
            doc.reference.delete()  # 메시지 삭제
        
        return {"message": f"All messages for chat_id {chat_id} have been deleted successfully."}

    except Exception as e:
        # ❌ Firestore 작업 중 오류 발생 시 HTTP 500 에러 반환
        raise HTTPException(status_code=500, detail=str(e))
