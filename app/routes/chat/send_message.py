from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, save_message, get_character_data  # ✅ `get_character_data` 추가
from firebase_admin import firestore

router = APIRouter()
db = firestore.client()

@router.post("/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    charac_id: str = Query(..., description="Character ID")  # ✅ pet_id → charac_id 변경
):
    """
    ✅ 사용자 메시지를 저장하고 AI 응답을 생성하는 API
    - Firestore `chats/{chat_id}/messages`에 사용자 메시지 저장
    - AI 응답을 생성한 후 Firestore에 저장
    - Firestore `chats/{chat_id}` 문서의 `last_message` 필드 업데이트
    """

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}_{charac_id}"  # ✅ 변경: chat_id 구성 변경

    # ✅ 캐릭터 데이터 가져오기 (Firestore `characters` 컬렉션에서 조회)
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        raise HTTPException(status_code=404, detail="Character data not found")  # ✅ pet → character 변경

    # ✅ 사용자 메시지 저장 (채팅 기록에 저장)
    save_message(chat_id, "user", user_input)

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)  # ✅ pet_id → charac_id 변경
    if error:
        raise HTTPException(status_code=500, detail=error)

    # ✅ AI 응답 저장
    save_message(chat_id, "ai", ai_response)

    # ✅ Firestore `chats/{chat_id}` 문서의 `last_message` 업데이트
    chat_ref = db.collection("chats").document(chat_id)

    # ✅ Firestore 문서가 없을 경우 `set()`을 사용하여 기본값을 설정하고 업데이트
    chat_ref.set(
        {
            "last_message": {
                "content": ai_response,
                "sender": "ai",
                "timestamp": firestore.SERVER_TIMESTAMP
            },
            "last_active_at": firestore.SERVER_TIMESTAMP
        },
        merge=True,  # ✅ 기존 데이터 유지하면서 새로운 데이터 추가
    )

    return {"response": ai_response}
