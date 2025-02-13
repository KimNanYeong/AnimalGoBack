from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, save_message
from firebase_admin import firestore

router = APIRouter()

# ✅ Firestore 클라이언트 연결
db = firestore.client()

@router.post("/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    pet_id: str = Query(..., description="Pet ID")
):
    """
    ✅ 사용자 메시지를 저장하고 AI 응답을 생성하는 API
    - Firestore `chats/{chat_id}/messages`에 사용자 메시지 저장
    - AI 응답을 생성한 후 Firestore에 저장
    - Firestore `chats/{chat_id}` 문서의 `last_message` 필드 업데이트
    """
    
    # 입력값 검증
    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}_{pet_id}"

    # ✅ 사용자 메시지 저장 (먼저 저장)
    user_message_id = save_message(chat_id, "user", user_input)

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, pet_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    # ✅ AI 응답 저장
    ai_message_id = save_message(chat_id, "ai", ai_response)

    # ✅ Firestore `chats/{chat_id}` 문서의 `last_message` 업데이트
    chat_ref = db.collection("chats").document(chat_id)
    chat_ref.update({
        "last_message": {
            "content": ai_response,
            "sender": "ai",
            "timestamp": firestore.SERVER_TIMESTAMP
        },
        "last_active_at": firestore.SERVER_TIMESTAMP  # 채팅방 활성화 시간 업데이트
    })

    return {"response": ai_response}
