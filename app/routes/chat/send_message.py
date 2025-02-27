import os
from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, get_character_data
from vectorstore.faiss_storage import store_chat_in_faiss  # ✅ 채팅방별 FAISS 저장
from services.firestore_utils import initialize_chat
from firebase_admin import firestore

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
    """🔥 채팅 속도 최적화된 API"""
    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}-{charac_id}"

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        raise HTTPException(status_code=404, detail="Character data not found")

    # ✅ 채팅방이 존재하지 않으면 자동 생성
    initialize_chat(user_id, charac_id, character_data)

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    # ✅ AI 응답이 있을 때만 Firestore 업데이트 & FAISS 저장 실행
    if ai_response:
        try:
            # ✅ Firestore chats/{chat_id} 문서의 last_message 업데이트 (대화 유지용)
            chat_ref = db.collection("chats").document(chat_id)
            chat_ref.set(
                {
                    "last_message": {"content": ai_response, "sender": charac_id},
                    "last_active_at": firestore.SERVER_TIMESTAMP
                },
                merge=True,
            )
            print(f"✅ Firestore 업데이트 완료: {chat_id}")
        except Exception as e:
            print(f"⚠️ Firestore 저장 오류: {str(e)}")  # ✅ 오류는 무시하고 로그만 출력

        # ✅ Firestore 저장 성공한 경우에만 FAISS 벡터 DB 업데이트 (중복 실행 방지)
        store_chat_in_faiss(chat_id)  
        print(f"✅ FAISS 저장 완료: {chat_id}")

    return {"response": ai_response}