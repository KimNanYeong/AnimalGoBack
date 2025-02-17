from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, get_character_data, initialize_chat
from firebase_admin import firestore
from db.faiss_db import store_chat_in_faiss  # ✅ 채팅방별 FAISS 저장

router = APIRouter()
db = firestore.client()

@router.post("/send_message",
             tags=["chat"], 
             summary="AI와 메시지 주고받기", 
             description="AI와 채팅 메시지를 주고받습니다.")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    charac_id: str = Query(..., description="Character ID")
):

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}-{charac_id}"

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        raise HTTPException(status_code=404, detail="Character data not found")

    # ✅ 채팅방이 존재하지 않으면 자동 생성
    initialize_chat(user_id, charac_id, character_data)  # 🔥 여기에 추가

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    # ✅ Firestore `chats/{chat_id}` 문서의 `last_message` 업데이트 (대화 유지용)
    chat_ref = db.collection("chats").document(chat_id)
    try:
        chat_ref.set(
            {
                "last_message": {"content": ai_response, "sender": charac_id},
                "last_active_at": firestore.SERVER_TIMESTAMP
            },
            merge=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Firestore 저장 중 오류 발생")

    # ✅ Firestore 저장 후 해당 채팅방의 FAISS 벡터 DB에 저장
    store_chat_in_faiss(chat_id, charac_id)  # 🔥 채팅방별 벡터 DB 저장

    return {"response": ai_response}
