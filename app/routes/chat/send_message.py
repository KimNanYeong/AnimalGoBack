from fastapi import APIRouter, HTTPException
from services.chat_service import generate_ai_response, get_character_data
from firebase_admin import firestore
import json
from datetime import datetime

router = APIRouter()
db = firestore.client()

# 현재 활성화된 WebSocket 연결 저장
active_connections = {}

@router.post("/chat/send_message", tags=["chat"])
async def chat_with_ai(user_input: str, user_id: str, charac_id: str):
    chat_id = f"{user_id}-{charac_id}"

    print(f"🚀 [send_message] 새로운 메시지 도착: user_id={user_id}, charac_id={charac_id}, user_input={user_input}")

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        print(f"❌ [send_message] Character data not found: user_id={user_id}, charac_id={charac_id}")
        raise HTTPException(status_code=404, detail="Character data not found")

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        print(f"❌ [send_message] AI 응답 생성 실패: error={error}")
        raise HTTPException(status_code=500, detail=error)

    # ✅ Firestore에 메시지 저장 + last_active_at 업데이트
    chat_ref = db.collection("chats").document(chat_id)

    # 🔥 Firestore 업데이트 전 데이터 출력
    doc = chat_ref.get()
    if doc.exists:
        prev_data = doc.to_dict()
        print(f"📌 [Firestore 이전 상태] chat_id={chat_id}, last_active_at={prev_data.get('last_active_at')}")
    else:
        print(f"📌 [Firestore] 문서 없음, 새 문서 생성 예정: chat_id={chat_id}")

    chat_ref.update({
        "messages": firestore.ArrayUnion([
            {"user_id": user_id, "message": user_input},
            {"user_id": "AI", "message": ai_response}
        ]),
        "last_active_at": firestore.SERVER_TIMESTAMP  # ✅ Firestore에서 자동으로 현재 시간 적용
    })

    # 🔥 Firestore 업데이트 후 데이터 확인
    updated_doc = chat_ref.get().to_dict()
    print(f"✅ [Firestore 업데이트 완료] chat_id={chat_id}, last_active_at={updated_doc.get('last_active_at')}")

    # ✅ WebSocket을 통해 메시지 전송 (해당 채팅방에 WebSocket 연결된 경우)
    if chat_id in active_connections:
        for websocket in active_connections[chat_id]:
            try:
                await websocket.send_text(json.dumps({"chat_id": chat_id, "user_id": user_id, "message": user_input}))
                await websocket.send_text(json.dumps({"chat_id": chat_id, "user_id": "AI", "message": ai_response}))
            except Exception as e:
                print(f"🔥 [WebSocket 오류] {e}")
    else:
        print(f"⚠️ [WebSocket] 연결 없음: chat_id={chat_id}")

    # ✅ 기존 HTTP 응답도 유지
    return {"chat_id": chat_id, "ai_response": ai_response}
