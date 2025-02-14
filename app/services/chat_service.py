from firebase_admin import firestore
import google.generativeai as genai
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import HTTPException
from db.faiss_db import search_similar_messages, store_chat_in_faiss


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
    """🔥 Firestore에서 성격 데이터를 가져오는 함수"""
    try:
        personality_ref = db.collection("personality_traits").document(personality_id)
        personality_doc = personality_ref.get()

        if not personality_doc.exists:
            print(f"⚠️ Firestore: personality_id={personality_id} 문서를 찾을 수 없음. 기본 데이터 사용.")
            return {
                "description": "기본 성격",
                "emoji_style": "🙂",
                "id": "default",
                "name": "기본",
                "prompt_template": "나는 친절한 말투로 대답할게!",
                "species_speech_pattern": {},
                "speech_style": "기본 말투"
            }

        return personality_doc.to_dict()

    except Exception as e:
        print(f"🚨 Firestore에서 personality_id={personality_id} 데이터를 가져오는 중 오류 발생: {str(e)}")
        return {
            "description": "기본 성격",
            "emoji_style": "🙂",
            "id": "default",
            "name": "기본",
            "prompt_template": "나는 친절한 말투로 대답할게!",
            "species_speech_pattern": {},
            "speech_style": "기본 말투"
        }


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
    """🔥 RAG 기반 AI 응답 생성 (FAISS 벡터 검색 적용)"""
    chat_id = f"{user_id}_{charac_id}"  # ✅ 채팅방 ID

    # ✅ Firestore에서 캐릭터 데이터 가져오기
    character_ref = db.collection("characters").document(chat_id)
    character_doc = character_ref.get()

    if not character_doc.exists:
        return None, "Character data not found"

    character_data = character_doc.to_dict()
    personality_id = character_data.get("personality", "default")
    animaltype = character_data.get("animaltype", "알 수 없음")
    nickname = character_data.get("nickname", "이름 없음")

    # ✅ Firestore에서 성격(personality) 데이터 가져오기
    personality_data = get_personality_data(personality_id)

    speech_style = personality_data.get("speech_style", "기본 말투")
    species_speech_pattern = personality_data.get("species_speech_pattern", {}).get(animaltype, "")
    emoji_style = personality_data.get("emoji_style", "")

    # ✅ 벡터 검색으로 문맥 가져오기 (채팅방별 FAISS 검색)
    similar_messages = search_similar_messages(chat_id, user_input, top_k=3)

    # ✅ 디버깅용 출력
    print(f"🔍 검색어: {user_input}")
    print(f"🔎 검색된 유사 문장들 (chat_id={chat_id}):")
    for msg in similar_messages:
        print(f"✅ {msg}")

    retrieved_context = "\n".join(similar_messages)
    
    # ✅ 프롬프트 구성
    system_prompt = f"""
    📌 **역할과 성격**
    당신은 사용자의 반려동물인 {animaltype} {nickname}입니다.
    당신의 성격은 "{personality_id}"이며, 대화 스타일은 "{speech_style}"입니다.
    
    📌 **이모지 스타일**
    - "{emoji_style}" 같은 이모지를 대화에서 자연스럽게 활용하세요.

    📌 **대화 스타일**
    - 항상 {animaltype}의 입장에서 대화하세요.
    - 감정을 담아 자연스럽게 반응하고, 사용자의 감정을 고려하여 적절한 어조를 사용하세요.
    - "{species_speech_pattern}" 같은 종특적인 말투를 자연스럽게 활용하세요.
    - 간결하고 직관적인 문장을 사용하며, 너무 길거나 딱딱한 표현은 피하세요.
    - 필요하면 이모지(🐶🐱💕) 등을 적절히 사용하여 친근한 느낌을 살리세요.

    📌 **과거 대화 문맥**
    {retrieved_context}

    💡 **대화 문맥을 유지하는 중요한 규칙**
    1. **"나","내가"**는 항상 **사용자를 의미**합니다. (즉, 질문을 입력한 사람)  
    2. **"너"**는 **{nickname} (즉, AI 캐릭터)**을 의미합니다.  
    3. 사용자가 전에 했던 말을 기억하고, 관련된 정보를 포함하여 응답하세요.  
    4. 만약 기억해야 할 정보가 없다면, 자연스럽게 넘기거나 다시 물어보세요.  

    📌 **추가 지침**
    - 불필요한 인사말은 생략하고, 대화의 흐름을 유지하세요.
    - 특정 질문에 대한 답변을 모르면, "잘 모르겠지만 네가 알려주면 기억할게!" 같은 방식으로 반응하세요.
    - 지나치게 공식적이지 않도록, 친근하고 유쾌한 말투를 유지하세요.

    📝 **사용자의 질문**  
    "{user_input}"
    """

    try:
        # ✅ Gemini API 호출
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([system_prompt])

        if not response.text:
            return None, "Empty response from Gemini API"

        # ✅ AI 응답 처리
        ai_response = response.text.strip()
        ai_response = ai_response.replace("안녕하세요!", "").replace("반갑습니다!", "")
        ai_response = ' '.join(ai_response.split())

        # 🚨 Firestore 저장 제거 → `send_message.py`에서 처리!
        
        # ✅ FAISS 벡터 DB에 새로운 대화 저장 (채팅방별 저장)
        store_chat_in_faiss(chat_id)

        return ai_response, None

    except Exception as e:
        print(f"🚨 Error in generate_ai_response: {str(e)}")
        return None, f"API Error: {str(e)}"
