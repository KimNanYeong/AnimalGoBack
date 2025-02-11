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

# ✅ 특정 채팅방의 최근 대화 내역 가져오기 (최대 10개) + 반복 질문 요약
@router.get("/chat/history/{chat_id}")
async def get_chat_history(chat_id: str):
    """
    Firestore에서 특정 채팅방(chat_id)의 최근 10개 메시지를 가져옵니다.
    - Firestore Timestamp를 ISO 8601 형식으로 변환
    - 같은 질문이 반복되면 요약 메시지를 추가
    """
    messages_ref = db.collection("chats").document(chat_id).collection("messages")
    docs = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()

    chat_history = []
    for doc in docs:
        message = doc.to_dict()

        # ✅ Firestore Timestamp 변환 (ISO 8601)
        if "timestamp" in message:
            if isinstance(message["timestamp"], datetime):
                message["timestamp"] = message["timestamp"].isoformat()
            elif hasattr(message["timestamp"], "to_datetime"):
                message["timestamp"] = message["timestamp"].to_datetime().isoformat()

        chat_history.append(message)

    # ✅ 반복 질문이 있는 경우 요약 메시지를 추가
    summary = summarize_repeated_questions(chat_history)
    if summary:
        chat_history.insert(0, {  
            "sender": "system",
            "content": " / ".join(summary),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # ✅ 최신 메시지가 리스트의 마지막에 오도록 순서 변경
    chat_history.reverse()

    return {"chat_id": chat_id, "messages": chat_history}

# ✅ AI와 채팅하는 API (Gemini API 사용)
@router.post("/chat/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    pet_id: str = Query(..., description="Pet ID")
):
    """
    Gemini API를 활용하여 AI와 채팅하는 API
    - 사용자의 입력(user_input)을 받아 Firestore에서 반려동물 & 성격 데이터 조회
    - AI에게 최근 채팅 내역을 포함한 메시지를 전달하여 자연스러운 응답 생성
    - 생성된 AI 응답을 Firestore에 저장 후 반환
    """

    # ✅ Firestore에서 반려동물 데이터 가져오기
    pet_data = get_pet_data(user_id, pet_id)
    if pet_data is None:
        raise HTTPException(status_code=404, detail="Pet data not found")

    pet_name = pet_data.get("name", "Unknown Pet")
    species = pet_data.get("species", "Unknown Species")
    trait_id = pet_data.get("trait_id", "calm")  # 기본 성격 calm 설정

    # ✅ Firestore에서 성격 데이터 가져오기
    trait_data = get_trait_data(trait_id)
    if trait_data is None:
        raise HTTPException(status_code=404, detail="Trait data not found")

    personality = trait_data.get("name", "기본 성격")

    # ✅ Firestore에서 최근 10개 채팅 내역 가져오기
    chat_history = get_recent_messages(user_id, pet_id)
    formatted_history = [msg["content"] for msg in chat_history]

    # ✅ AI가 반려동물의 개성을 반영할 수 있도록 시스템 프롬프트 설정
    system_prompt = f"""
    너는 {species}인 {pet_name}야.
    너는 {personality} 성격을 가지고 있어.
    친근한 말투로 대답해야 해.
    """

    try:
        # ✅ Gemini API 요청 (messages 대신 리스트로 직접 입력)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            [system_prompt, *formatted_history, user_input]  # 전체 입력 리스트로 전달
        )

        # ✅ 응답이 정상적으로 생성되지 않으면 예외 발생
        if not response.text:
            raise HTTPException(status_code=500, detail="Gemini API returned empty response")

        ai_response = response.text

        # ✅ Firestore에 대화 내용 저장
        messages_ref = db.collection("chats").document(f"{user_id}_{pet_id}").collection("messages")
        messages_ref.add({"content": user_input, "sender": "user", "timestamp": datetime.now(timezone.utc)})
        messages_ref.add({"content": ai_response, "sender": pet_name, "timestamp": datetime.now(timezone.utc)})

        return {"response": ai_response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")
