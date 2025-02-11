from fastapi import APIRouter, HTTPException, Query
import google.generativeai as genai
from firebase_admin import firestore
from datetime import datetime, timezone
import os
from collections import Counter
from dotenv import load_dotenv


# ✅ FastAPI 라우터 생성
router = APIRouter()

load_dotenv()


# ✅ Firestore 클라이언트 연결
db = firestore.client()

# ✅ Gemini API 키 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # 환경 변수에서 API 키 가져오기
genai.configure(api_key=GEMINI_API_KEY)

# ✅ 사용할 AI 모델 지정 (Gemini 2.0 Flash Thinking Experimental 01-21)
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"

# ✅ Firestore에서 특정 반려동물 데이터를 가져오는 함수
def get_pet_data(user_id: str, pet_id: str):
    doc_ref = db.collection("user_pets").document(f"{user_id}_{pet_id}")
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

# ✅ Firestore에서 특정 성격(trait) 데이터를 가져오는 함수
def get_trait_data(trait_id: str):
    trait_ref = db.collection("character_traits").document(trait_id)
    trait_doc = trait_ref.get()
    return trait_doc.to_dict() if trait_doc.exists else None

# ✅ Firestore에서 최근 10개 채팅 메시지를 가져오는 함수
def get_recent_messages(user_id: str, pet_id: str):
    chat_doc_id = f"{user_id}_{pet_id}"
    messages_ref = db.collection("chats").document(chat_doc_id).collection("messages")
    docs = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
    return [doc.to_dict() for doc in docs]

# ✅ Firestore에서 반복 질문 요약하는 함수
def summarize_repeated_questions(messages):
    user_messages = [msg["content"].strip().lower() for msg in messages if msg["sender"] == "user"]
    message_counts = Counter(user_messages)

    summary = []
    for msg, count in message_counts.items():
        if count >= 5:
            summary.append(f"사용자가 '{msg}'라는 질문을 {count}번 했어요.")

    return summary if summary else None

# ✅ AI와 채팅하는 API (Gemini API 사용)
@router.post("/chat/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    pet_id: str = Query(..., description="Pet ID")
):
    """
    🔥 AI와 채팅하는 API 🔥
    - Firestore에서 반려동물 데이터를 가져와 성격을 반영한 채팅을 생성
    - Firestore에 메시지 저장 및 `last_active_at`, `last_message` 필드 업데이트
    """

    # ✅ Firestore에서 반려동물 데이터 가져오기
    pet_data = get_pet_data(user_id, pet_id)
    if pet_data is None:
        raise HTTPException(status_code=404, detail="Pet data not found")

    pet_name = pet_data.get("name", "Unknown Pet")
    personality = pet_data.get("personality", "기본 성격")
    chat_id = f"{user_id}_{pet_id}"

    # ✅ Firestore에서 해당 채팅방이 존재하는지 확인
    chat_doc_ref = db.collection("chats").document(chat_id)
    chat_doc = chat_doc_ref.get()

    if not chat_doc.exists:
        # ✅ 채팅방이 없으면 새로 생성
        chat_doc_ref.set({
            "chat_id": chat_id,
            "character_name": pet_name,
            "character_personality": personality,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active_at": datetime.now(timezone.utc).isoformat(),
            "last_message": {"text": "", "sender": "", "timestamp": None}  # ✅ 기본값 추가
        })

    # ✅ Firestore에서 최근 10개 채팅 내역 가져오기
    chat_history = get_recent_messages(user_id, pet_id)
    formatted_history = [msg["content"] for msg in chat_history]

    # ✅ AI가 반려동물의 개성을 반영할 수 있도록 시스템 프롬프트 설정
    system_prompt = f"""
    너는 {pet_name}야.
    너는 {personality} 성격을 가지고 있어.
    친근한 말투로 대답해야 해.
    """

    try:
        # ✅ Gemini API 요청
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([system_prompt, *formatted_history, user_input])

        if not response.text:
            raise HTTPException(status_code=500, detail="Gemini API returned empty response")

        ai_response = response.text

        # ✅ Firestore에 대화 내용 저장
        messages_ref = chat_doc_ref.collection("messages")

        # ⬇️ ✅ 사용자 메시지 저장
        user_message = {
            "content": user_input,
            "sender": "user",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        messages_ref.add(user_message)

        # ⬇️ ✅ AI 응답 메시지 저장
        ai_message = {
            "content": ai_response,
            "sender": pet_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        messages_ref.add(ai_message)

        # ✅ 채팅방 문서 업데이트 (last_active_at & last_message)
        chat_doc_ref.update({
            "last_active_at": ai_message["timestamp"],  # ✅ 가장 최근 메시지 시간
            "last_message": ai_message  # ✅ 최근 메시지 저장
        })

        return {"response": ai_response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")