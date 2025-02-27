from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.chat_service import generate_ai_response, get_character_data
from firebase_admin import firestore
import json

router = APIRouter()
db = firestore.client()

# 현재 활성화된 WebSocket 연결 저장
active_connections = {}

@router.websocket("/chat/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    try:
        await websocket.accept()

        # ✅ WebSocket 연결을 관리하는 active_connections에 추가
        if chat_id not in active_connections:
            active_connections[chat_id] = []
        active_connections[chat_id].append(websocket)

        # ✅ Firestore에서 기존 채팅 내역 가져오기
        chat_ref = db.collection("chats").document(chat_id)
        chat_data = chat_ref.get()

        if not chat_data.exists:
            chat_ref.set({"messages": [], "last_active_at": firestore.SERVER_TIMESTAMP, "last_message": {"content": "", "sender": ""}})  # 🔥 채팅방이 없으면 자동 생성
            messages = []
        else:
            messages = chat_data.to_dict().get("messages", [])

        # ✅ 기존 메시지를 클라이언트에 전송
        try:
            await websocket.send_text(json.dumps({"chat_id": chat_id, "messages": messages}))
        except RuntimeError:
            return

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_id = message_data.get("user_id")
            message = message_data.get("message")

            # ✅ Firestore에 사용자 메시지 저장
            try:
                chat_ref.update({
                    "messages": firestore.ArrayUnion([
                        {"user_id": user_id, "message": message}
                    ]),
                    "last_active_at": firestore.SERVER_TIMESTAMP,
                    "last_message": {"content": message, "sender": user_id}
                })
            except Exception as e:
                print(f"❌ Firestore 메시지 저장 오류: {e}")

            # ✅ AI 응답 생성
            user_id_split, charac_id = chat_id.split("-", 1)
            ai_response, error = generate_ai_response(user_id_split, charac_id, message)

            if error:
                ai_response = "AI 응답 생성 중 오류 발생"

            # ✅ Firestore에 AI 응답 저장
            try:
                chat_ref.update({
                    "messages": firestore.ArrayUnion([
                        {"user_id": "AI", "message": ai_response}
                    ]),
                    "last_active_at": firestore.SERVER_TIMESTAMP,
                    "last_message": {"content": ai_response, "sender": charac_id}
                })
            except Exception as e:
                print(f"❌ Firestore AI 응답 저장 오류: {e}")

            # ✅ WebSocket을 통해 모든 연결된 클라이언트에 실시간 메시지 전송
            try:
                for conn in active_connections.get(chat_id, []):
                    await conn.send_text(json.dumps({
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "message": message
                    }))
                    await conn.send_text(json.dumps({
                        "chat_id": chat_id,
                        "user_id": "AI",
                        "message": ai_response
                    }))
                print(f"📤 AI 응답 전송 완료: {ai_response}")
            except RuntimeError:
                print(f"❌ WebSocket이 닫힌 상태에서 메시지를 보내려고 함: {chat_id}")
                break

    except WebSocketDisconnect:
        print(f"❌ WebSocket {chat_id} 연결 종료")

        # ✅ WebSocket이 닫히면 active_connections에서 제거
        if chat_id in active_connections:
            active_connections[chat_id].remove(websocket)
            if not active_connections[chat_id]:  # 채팅방에 연결된 클라이언트가 없으면 삭제