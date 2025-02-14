from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, get_character_data
from firebase_admin import firestore
from db.faiss_db import store_chat_in_faiss  # ✅ 채팅방별 FAISS 저장

router = APIRouter()
db = firestore.client()

@router.post("/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    charac_id: str = Query(..., description="Character ID")
):
    """
    ✅ 사용자 메시지를 저장하고 AI 응답을 생성하는 API
    - Firestore `chats/{chat_id}/messages`에 사용자 메시지 저장
    - AI 응답을 생성한 후 Firestore에 저장
    - Firestore `chats/{chat_id}` 문서의 `last_message` 필드 업데이트
    - ✅ Firestore 저장 후 FAISS 벡터 DB에도 자동 반영 (채팅방별 저장)
    """

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}_{charac_id}"

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        raise HTTPException(status_code=404, detail="Character data not found")

    messages_ref = db.collection("chats").document(chat_id).collection("messages")

    # ✅ Firestore 배치 저장 (성능 최적화)
    batch = db.batch()
    
    user_message = {
        "content": user_input,
        "sender": user_id,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    user_message_ref = messages_ref.document()
    batch.set(user_message_ref, user_message)

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    ai_message = {
        "content": ai_response,
        "sender": charac_id,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    ai_message_ref = messages_ref.document()
    batch.set(ai_message_ref, ai_message)

    # ✅ Firestore `chats/{chat_id}` 문서의 `last_message` 업데이트
    chat_ref = db.collection("chats").document(chat_id)
    batch.set(
        chat_ref,
        {
            "last_message": ai_message,
            "last_active_at": firestore.SERVER_TIMESTAMP
        },
        merge=True,
    )

    try:
        batch.commit()  # ✅ Firestore에 한 번에 저장
        print(f"✅ Firestore 저장 완료: chat_id={chat_id}")
    except Exception as e:
        print(f"🚨 Firestore 저장 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="Firestore 저장 중 오류 발생")

    # ✅ Firestore 저장 후 해당 채팅방의 FAISS 벡터 DB에 저장
    store_chat_in_faiss(chat_id)  # 🔥 채팅방별 벡터 DB 저장

    return {"response": ai_response}
