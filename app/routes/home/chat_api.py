from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Form, HTTPException
from firebase_admin import firestore
#from app.services.ai_chats_service import auto_chat, check_character_exists  # 변경된 함수 이름 사용
from services.ai_chats_service import start_conversation, check_character_exists, status_completed # Ai crew 구조
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter()
db = firestore.client()

# ========================
# 🔹 캐릭터 간 AI 대화 API 
# ========================
@router.post("/ai_characters_chats",
    summary="AI 캐릭터 간 대화 생성",
    tags=["Basic"],
    description="""
    Gemini 2.0 API를 사용하여 두 캐릭터 간 자동 대화를 4회 반복합니다.
    캐릭터는 Firestore `characters` 컬렉션의 문서 ID를 기반으로 선택해야 합니다.
    자동 생성된 chat_id는 `{charac_1}_{charac_2}` 형식입니다.
    """
)
async def start_ai_conversation(
    charac_1: str = Form(..., description="첫 번째 캐릭터 ID (Firestore의 document ID)"),
    charac_2: str = Form(..., description="두 번째 캐릭터 ID (Firestore의 document ID)")
):
    """
    두 캐릭터 간 자동 대화를 4회 반복 실행합니다.
    """
    chat_id = f"{charac_1}_{charac_2}"  # chat_id 자동 생성

    # Firestore에서 캐릭터 존재 여부 확인
    if not check_character_exists(charac_1) or not check_character_exists(charac_2):
        raise HTTPException(status_code=404, detail="캐릭터 ID - Firestore에 존재하지 않습니다.")
    
    # 이미지 변환 여부 확인
    if not status_completed(charac_1):
        raise HTTPException(status_code=404, detail=" 이미지 변환이 되지 않았습니다. charac1 pending")
    if not status_completed(charac_2):
        raise HTTPException(status_code=404, detail=" 이미지 변환이 되지 않았습니다. charac2 pending")

    # Gemini 2.0 API 기반 자동 대화 실행 (Crew AI 없이 프롬프트를 통한 대화)
    #result = auto_chat(charac_1, charac_2)  --- AI crew 구조로 대체
    #result = start_conversation(charac_1, charac_2)  # streamin 구조로 대체 
    return StreamingResponse(start_conversation(charac_1, charac_2), media_type="text/event-stream")

# Pydantic 모델 정의
class ChatRoom(BaseModel):
    chat_id: str
    create_at: str
    last_active_at: str
    last_message: str

# ==================================================
# 특정 user_id가 보유한 캐릭터들의 채팅방 리스트 API
# ==================================================
@router.get("/users/{user_id}/chats", response_model=List[ChatRoom],
    summary="AI 캐릭터 대화방 리스트",
    tags=["Basic"],
    description="""
    대화방 리스트
    """)
def get_user_chatrooms(user_id: str):
    # chats 컬렉션에서 해당 user_id가 만든 채팅방만 조회
    chats_ref = db.collection("chats")
    query = chats_ref.where("user_id", "==", user_id).stream()

    chatroom_list = []
    for doc in query:
        data = doc.to_dict()
        participants = data.get("participants", [])

        # 1) participants가 2명인지 확인
        if len(participants) != 2:
            continue

        # 2) last_message가 존재하는지 확인
        last_message = data.get("last_message")
        if not last_message:
            continue

        # 필수 필드가 모두 존재하는지 확인
        if all(key in data for key in ["create_at", "last_active_at"]):
            chatroom_list.append({
                "chat_id": doc.id,
                "create_at": data["create_at"].isoformat(),
                "last_active_at": data["last_active_at"].isoformat(),
                "last_message": last_message
            })

    if not chatroom_list:
        raise HTTPException(status_code=404, detail="해당 유저가 만든 채팅방이 존재하지 않습니다.")

    return chatroom_list

# Pydantic 모델 정의
class Message(BaseModel):
    sender: str
    content: str
    timestamp: str

# ====================================
# 두 캐릭터 채팅방의 대화 내용 조회 API
# ====================================
@router.get("/chats/{chat_id}/messages", response_model=List[Message],
    summary="두 캐릭터 AI 대화 내용",
    tags=["Basic"],
    description="""
    두 캐릭터 AI 대화 메시지 모두 
    """)

def get_chat_messages(chat_id: str):
    # chats 컬렉션의 특정 채팅방 참조
    chat_ref = db.collection("chats").document(chat_id)
    chat_doc = chat_ref.get()

    # 채팅방이 존재하지 않을 때 예외 처리
    if not chat_doc.exists:
        raise HTTPException(status_code=404, detail="해당 채팅방이 존재하지 않습니다.")
    
    # participants가 정확히 2명인지 확인
    data = chat_doc.to_dict()
    participants = data.get("participants", [])
    if len(participants) != 2:
        raise HTTPException(status_code=400, detail="두 명이 대화하는 채팅방이 아닙니다.")
    
    # message 하위 컬렉션에서 메시지들 가져오기 (시간순 정렬)
    messages_ref = chat_ref.collection("messages").order_by("timestamp")
    message_docs = messages_ref.stream()

    messages = []
    for msg in message_docs:
        msg_data = msg.to_dict()
        messages.append({
            "sender": msg_data.get("sender"),
            "content": msg_data.get("content"),
            "timestamp": msg_data.get("timestamp").isoformat()  # Firestore 타임스탬프를 ISO 문자열로 변환
        })

    # 메시지가 없는 경우 예외 처리
    if not messages:
        raise HTTPException(status_code=404, detail="대화 내용이 존재하지 않습니다.")

    return messages
