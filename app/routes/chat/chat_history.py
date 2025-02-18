from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime, timezone, timedelta
from db.faiss_db import store_chat_in_faiss
import logging
import os

# ✅ Firestore 클라이언트 연결
db = firestore.client()

# ✅ FastAPI 라우터 설정
router = APIRouter()

# Ensure the log directory exists
log_directory = 'log'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# ✅ 로깅 설정
logging.basicConfig(filename='log/chat_history.log', level=logging.DEBUG)

@router.get("/chat/history/{chat_id}",
            tags=["chat"], 
            summary="채팅 메시지 기록 조회", 
            description="특정 채팅방의 채팅 메시지 리스트를 반환합니다.")
async def get_chat_history(chat_id: str):
    """
    ✅ 특정 채팅방의 채팅 메시지 리스트를 반환하는 API
    - Firestore `chats/{chat_id}/messages` 컬렉션에서 최근 메시지를 가져옴
    - 최대 50개 메시지를 `timestamp` 기준 최신순으로 정렬하여 반환
    """
    logging.info(f"Request received for chat history with chat_id: {chat_id}")
    try:
        chat_ref = db.collection("chats").document(chat_id)
        chat_doc = chat_ref.get()

        if not chat_doc.exists:
            logging.warning(f"Chat room not found for chat_id: {chat_id}")
            raise HTTPException(status_code=404, detail="Chat room not found")

        # ✅ Firestore에서 최신 메시지를 먼저 가져옴 (내림차순 정렬)
        messages_ref = chat_ref.collection("messages").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(50)

        messages = []
        for msg in messages_ref.stream():
            msg_data = msg.to_dict()

            # ✅ Firestore Timestamp -> Python datetime 변환
            timestamp = msg_data.get("timestamp")
            if isinstance(timestamp, firestore.SERVER_TIMESTAMP.__class__):
                timestamp = timestamp.to_datetime()

            # ✅ 한국 시간(KST, UTC+9) 변환 및 포맷팅
            kst = timezone(timedelta(hours=9))
            formatted_time = timestamp.astimezone(kst).strftime("%Y년 %m월 %d일 %p %I시 %M분 %S초 UTC%z") if timestamp else ""

            messages.append({
                "content": msg_data.get("content", ""),
                "sender": msg_data.get("sender", ""),
                "timestamp": formatted_time  # ✅ 한국 시간 문자열로 변환 후 저장
            })

        if not messages:
            logging.warning(f"No messages found in chat room with chat_id: {chat_id}")
            raise HTTPException(status_code=404, detail="No messages found in this chat room.")

        # ✅ 최신 메시지가 마지막에 위치하도록 리스트 역순 정렬
        messages.reverse()

        response = {"chat_id": chat_id, "messages": messages}
        logging.info(f"Response for chat_id {chat_id}: {response}")
        return response

    except Exception as e:
        logging.error(f"Error retrieving chat history for chat_id {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))