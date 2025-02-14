from firebase_admin import firestore
import google.generativeai as genai
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import HTTPException


# 환경 변수 설정
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)
db = firestore.client()
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"

def initialize_chat(user_id: str, charac_id: str, character_data: dict):
    """🔥 채팅방이 존재하지 않으면 Firestore에 자동 생성"""

    chat_id = f"{user_id}_{charac_id}"
    chat_ref = db.collection("chats").document(chat_id)
    chat_doc = chat_ref.get()

    # ✅ 채팅방이 존재하지 않고, 캐릭터가 삭제된 상태면 생성 안 함
    character_ref = db.collection("characters").document(f"{user_id}_{charac_id}")
    if not character_ref.get().exists:
        print(f"🚨 Character {charac_id} not found. Skipping chat creation.")
        return

    # ✅ 채팅방이 없을 경우에만 생성
    if not chat_doc.exists:
        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "nickname": character_data["nickname"],
            "personality": character_data["personality"],
            "animaltype": character_data["animaltype"],
            "create_at": firestore.SERVER_TIMESTAMP,
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "last_message": None
        }
        chat_ref.set(chat_data)

def get_character_data(user_id: str, charac_id: str):
    """Firestore에서 캐릭터 데이터 가져오기 (characters 컬렉션 사용)"""
    
    character_ref = db.collection("characters").document(f"{user_id}_{charac_id}")
    character_doc = character_ref.get()

    if character_doc is None or not character_doc.exists:
        print(f"❌ Firestore: 캐릭터 정보 없음 → user_id: {user_id}, charac_id: {charac_id}")
        return None

    character_data = character_doc.to_dict()

    # ✅ animaltype 필드가 없을 경우 기본값 "미확인" 설정
    animaltype = character_data.get("animaltype", "미확인")

    # ✅ personality_id 확인
    personality_id = character_data.get("personality")
    if not personality_id:
        print(f"❌ Firestore: personality ID 없음 → user_id: {user_id}, charac_id: {charac_id}")
        return None

    print(f"✅ Firestore: personality_id={personality_id}, animaltype={animaltype}")  # 디버깅 출력

    return {
        "nickname": character_data.get("nickname"),
        "personality": personality_id,
        "animaltype": animaltype,  # ✅ 수정: 기본값 설정
        "speech_pattern": "",
        "speech_style": ""
    }


def get_personality_data(personality_id: str):
    """성격 데이터를 가져오는 함수"""
    personality_ref = db.collection("personality_traits").document(personality_id)
    personality_doc = personality_ref.get()

    # ✅ Firestore 문서가 있는지 확인할 때 None 체크 추가
    if personality_doc is None or not personality_doc.exists:
        print(f"❌ Firestore: personality_id={personality_id} 문서를 찾을 수 없음.")
        return None
        
    return personality_doc.to_dict()

def get_recent_messages(chat_id: str, limit: int = 10):
    """최근 메시지 가져오기"""
    messages_ref = db.collection("chats").document(chat_id).collection("messages")
    docs = list(
        messages_ref.order_by("timestamp", direction=firestore.Query.ASCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]

def save_message(chat_id: str, sender: str, content: str):
    """메시지 저장"""
    messages_ref = db.collection("chats").document(chat_id).collection("messages")
    message_data = {
        "sender": sender,
        "content": content,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    doc_ref = messages_ref.add(message_data)[1]
    return doc_ref

def generate_ai_response(user_id: str, charac_id: str, user_input: str):
    """AI 응답 생성"""
    chat_id = f"{user_id}_{charac_id}"  # ✅ pet_id → charac_id 변경

    # ✅ 캐릭터 데이터 가져오기
    character_data = get_character_data(user_id, charac_id)  # ✅ 함수명 수정
    if character_data is None:
        return None, "Character data not found"

    # ✅ 채팅방 초기화 (존재하지 않으면 생성)
    initialize_chat(user_id, charac_id, character_data)

    # ✅ 성격 데이터 가져오기
    personality_data = get_personality_data(character_data["personality"])
    if personality_data is None:
        return None, "Personality data not found"

    # ✅ 대화 스타일 설정
    animaltype = character_data["animaltype"]  # ✅ Firestore 필드명과 일치하게 수정
    speech_pattern = personality_data.get("species_speech_pattern", {}).get(animaltype, "{말투}")
    speech_style = personality_data.get("speech_style", "기본 말투")

    # ✅ 프롬프트 구성
    system_prompt = f"""
    당신은 {animaltype}인 {character_data['nickname']}입니다.
    성격: {character_data['personality']}
    말하는 스타일: {speech_style}

    다음 지침을 따라주세요:
    1. 항상 {animaltype}의 입장에서 대화하세요.
    2. {speech_pattern} 같은 의성어를 자연스럽게 섞어서 사용하세요.
    3. 응답은 간결하고 자연스럽게, 마치 카카오톡으로 대화하듯이 해주세요.
    4. 불필요한 인사말이나 형식적인 문구는 제외하고, 대화의 맥락에 맞게 바로 답변해주세요.
    5. 이모지는 적절히 사용하되 과하지 않게 해주세요.
    """

    # ✅ 최근 메시지 가져오기
    chat_history = get_recent_messages(chat_id)
    formatted_history = [msg["content"] for msg in chat_history]

    try:
        # ✅ Gemini API 호출
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([system_prompt, *formatted_history, user_input])

        if not response.text:
            return None, "Empty response from Gemini API"

        # ✅ AI 응답 처리
        ai_response = response.text.strip()
        ai_response = ai_response.replace("안녕하세요!", "").replace("반갑습니다!", "")
        ai_response = ' '.join(ai_response.split())

        # ✅ last_message 필드 업데이트
        db.collection("chats").document(chat_id).update({
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "last_message": {
                "content": ai_response,
                "sender": "ai",
                "timestamp": firestore.SERVER_TIMESTAMP
            }
        })

        return ai_response, None

    except Exception as e:
        print(f"Error in generate_ai_response: {str(e)}")
        return None, f"API Error: {str(e)}"
