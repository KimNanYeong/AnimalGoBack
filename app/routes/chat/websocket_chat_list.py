import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from firebase_admin import firestore
import json
from datetime import datetime

router = APIRouter()
db = firestore.client()
active_connections = {}
# asyncio의 이벤트 루프를 저장할 변수 추가
event_loop = asyncio.get_event_loop()

def convert_timestamp(timestamp):
    """Firestore Timestamp -> ISO 8601 문자열 변환"""
    if timestamp is None:
        return None  # ✅ None 값 그대로 유지
    if timestamp == firestore.SERVER_TIMESTAMP:
        return None
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()  # ✅ JSON 직렬화 가능하도록 변환
    return str(timestamp)  # ✅ 예상치 못한 값은 문자열로 변환

def get_chat_list(user_id):
    chats_ref = db.collection("chats") \
        .where("chat_id", ">=", f"{user_id}-") \
        .where("chat_id", "<", f"{user_id}-\uf8ff") \
        .order_by("last_active_at", direction=firestore.Query.DESCENDING) \
        .get()

    chat_list = []
    for chat in chats_ref:
        chat_data = chat.to_dict()
        chat_id = chat.id

        # ✅ last_message가 None일 경우 기본값 {}으로 설정
        last_message = chat_data.get("last_message", {}) or {}

         # ✅ 문자열인 경우 JSON으로 변환
        if isinstance(last_message, str):
            try:
                last_message = json.loads(last_message)  # JSON 문자열 -> 딕셔너리 변환
            except json.JSONDecodeError:
                last_message = {"content": last_message}  # 변환 실패 시 문자열을 content에 넣음

        # ✅ 디버깅 로그 추가
        #print(f"[DEBUG] chat_id: {chat_id}, last_message: {last_message}")

        chat_list.append({
            "chat_id": chat_id,
            "nickname": chat_data.get("nickname", ""),
            "personality": chat_data.get("personality", ""),
            "create_at": convert_timestamp(chat_data.get("create_at", "")),  # 🔥 변환 적용
            "last_active_at": convert_timestamp(chat_data.get("last_active_at", "")),  # 🔥 변환 적용
            "last_message": {
                "content": last_message.get("content", ""),
                "sender": last_message.get("sender", ""),
                "timestamp": convert_timestamp(last_message.get("timestamp", None))  # 🔥 변환 적용
            }
        })
    return chat_list

@router.websocket("/chat/ws/list/{user_id}")
async def websocket_chat_list(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    if user_id not in active_connections:
        active_connections[user_id] = set()
    
    active_connections[user_id].add(websocket)

    try:
        await websocket.send_text(json.dumps({"message": "WebSocket 연결 성공"}))

        # ✅ Firestore에서 기존 채팅 목록을 가져와 WebSocket으로 전송
        chat_list = get_chat_list(user_id)
        await websocket.send_text(json.dumps({"chats": chat_list}))

        # ✅ Firestore 실시간 감지 설정
        def on_snapshot(doc_snapshot, changes, read_time):
            updated_chat_list = get_chat_list(user_id)

            async def send_update():
                for conn in active_connections.get(user_id, []):
                    try:
                        await conn.send_text(json.dumps({"chats": updated_chat_list}))
                    except Exception:
                        pass

            # ✅ 이벤트 루프가 없는 경우에도 안전하게 실행
            asyncio.run_coroutine_threadsafe(send_update(), event_loop)

        # ✅ Firestore 실시간 리스너 등록
        query_watch = db.collection("chats") \
            .where("chat_id", ">=", f"{user_id}-") \
            .where("chat_id", "<", f"{user_id}-\uf8ff") \
            .order_by("last_active_at", direction=firestore.Query.DESCENDING) \
            .on_snapshot(on_snapshot)

        while True:
            await websocket.receive_text()  # ✅ WebSocket 연결 유지

    except WebSocketDisconnect:
        active_connections[user_id].remove(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]