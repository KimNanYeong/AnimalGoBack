from firebase_admin import firestore
import google.generativeai as genai
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

# ✅ 환경 변수 로드
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# ✅ API 키 로드 및 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ Firestore 연결
db = firestore.client()
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"

def get_pet_data(user_id: str, pet_id: str):
    """Firestore에서 반려동물 데이터를 가져오는 함수"""
    doc_ref = db.collection("user_pets").document(f"{user_id}_{pet_id}")
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def get_recent_messages(user_id: str, pet_id: str):
    """Firestore에서 최근 10개 채팅 메시지를 가져오는 함수"""
    chat_doc_id = f"{user_id}_{pet_id}"
    messages_ref = db.collection("chats").document(chat_doc_id).collection("messages")
    
    docs = list(
        messages_ref.order_by("timestamp", direction=firestore.Query.ASCENDING)
        .limit(10)
        .stream()
    )
    return [doc.to_dict() for doc in docs]

def save_message(chat_id: str, sender: str, content: str):
    """Firestore에 메시지 저장하고 참조 반환"""
    messages_ref = db.collection("chats").document(chat_id).collection("messages")
    message_data = {
        "sender": sender,
        "content": content,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    doc_ref = messages_ref.add(message_data)[1]  # [1]로 DocumentReference 가져오기
    return doc_ref

def initialize_chat_if_not_exists(user_id: str, pet_id: str, pet_data: dict):
    """채팅방이 존재하지 않으면 생성"""
    chat_id = f"{user_id}_{pet_id}"
    chat_doc_ref = db.collection("chats").document(chat_id)
    chat_doc = chat_doc_ref.get()
    
    if not chat_doc.exists:
        chat_doc_ref.set({
            "chat_id": chat_id,
            "character_name": pet_data["name"],
            "character_personality": pet_data["personality"],
            "species": pet_data["species"],
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "last_message": {"content": "", "sender": "", "timestamp": None}
        })

def generate_ai_response(user_id: str, pet_id: str, user_input: str):
    """Gemini API를 호출하여 AI 응답을 생성하는 함수"""
    pet_data = get_pet_data(user_id, pet_id)
    if pet_data is None:
        return None, "Pet data not found"

    initialize_chat_if_not_exists(user_id, pet_id, pet_data)

    pet_name = pet_data.get("name", "Unknown Pet")
    personality = pet_data.get("personality", "기본 성격")
    species = pet_data.get("species", "동물")
    speech_pattern = pet_data.get("speech_pattern", "").strip()
    speech_style = pet_data.get("speech_style", "기본 말투")
    
    # 개선된 system prompt
    system_prompt = f"""
    당신은 {species}인 {pet_name}입니다.
    성격: {personality}
    말하는 스타일: {speech_style}
    
    다음 지침을 따라주세요:
    1. 항상 {species}의 입장에서 대화하세요.
    2. {speech_pattern} 같은 의성어를 자연스럽게 섞어서 사용하세요.
    3. 응답은 간결하고 자연스럽게, 마치 카카오톡으로 대화하듯이 해주세요.
    4. 불필요한 인사말이나 형식적인 문구는 제외하고, 대화의 맥락에 맞게 바로 답변해주세요.
    5. 이모지는 적절히 사용하되 과하지 않게 해주세요.
    
    이전 대화를 참고하여 일관된 성격과 말투를 유지하세요.
    """

    chat_history = get_recent_messages(user_id, pet_id)
    formatted_history = [msg["content"] for msg in chat_history]

    try:
        print("✅ Gemini API 호출 시작...")
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([system_prompt, *formatted_history, user_input])

        if not response.text:
            return None, "Gemini API returned empty response"

        # 응답에서 불필요한 부분 제거 및 정리
        ai_response = response.text.strip()
        ai_response = ai_response.replace("안녕하세요!", "").replace("반갑습니다!", "")
        ai_response = ' '.join(ai_response.split())  # 불필요한 공백 제거

        # Firestore에 메시지 저장
        message_ref = save_message(f"{user_id}_{pet_id}", pet_name, ai_response)

        # last_message 업데이트
        db.collection("chats").document(f"{user_id}_{pet_id}").update({
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "last_message": {
                "content": ai_response,
                "sender": pet_name,
                "timestamp": firestore.SERVER_TIMESTAMP
            }
        })

        print(f"✅ Firestore에 메시지 저장 완료 (message_id: {message_ref.id})")
        return ai_response, None

    except Exception as e:
        print(f"❌ Error in generate_ai_response: {str(e)}")
        return None, f"Gemini API Error: {str(e)}"