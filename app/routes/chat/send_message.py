import os
import logging
from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, get_character_data, initialize_chat
from firebase_admin import firestore
from db.faiss_db import store_chat_in_faiss  # ✅ 채팅방별 FAISS 저장

# Ensure the log directory exists
log_directory = 'log'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# ✅ 로깅 설정 (시간 포함)
logger = logging.getLogger("send_message_logger")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.join(log_directory, 'send_message.log'))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Suppress debug messages from python_multipart
logging.getLogger("python_multipart").setLevel(logging.WARNING)

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
    logger.info(f"Request received to chat with AI: user_id={user_id}, charac_id={charac_id}, user_input={user_input}")

    if not user_input.strip():
        logger.warning("Empty message not allowed")
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}-{charac_id}"

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)
    if character_data is None:
        logger.warning(f"Character data not found for user_id={user_id}, charac_id={charac_id}")
        raise HTTPException(status_code=404, detail="Character data not found")

    # ✅ 채팅방이 존재하지 않으면 자동 생성
    initialize_chat(user_id, charac_id, character_data)  # 🔥 여기에 추가

    # ✅ AI 응답 생성
    ai_response, error = generate_ai_response(user_id, charac_id, user_input)
    if error:
        logger.error(f"Error generating AI response: {error}")
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
        logger.error(f"Error saving to Firestore for chat_id={chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Firestore 저장 중 오류 발생")

    # ✅ Firestore 저장 후 해당 채팅방의 FAISS 벡터 DB에 저장
    store_chat_in_faiss(chat_id, charac_id)  # 🔥 채팅방별 벡터 DB 저장

    response = {"response": ai_response}
    logger.info(f"Response for chat_id={chat_id}: {response}")
    return response