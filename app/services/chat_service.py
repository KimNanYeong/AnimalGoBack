from services import get_user_nickname, get_character_data, get_personality_data, save_message
from vectorstore.faiss_utils import get_similar_messages
from services import generate_prompt, generate_response
from firebase_admin import firestore
import re
from collections import deque  # 간단한 메모리 관리용

db = firestore.client()

# 캐릭터 정보 캐싱 (서버 실행 시 한 번만 로드)
cached_character_data = {}
# 대화 기록을 메모리에 저장 (최대 10개 메시지로 제한)
conversation_memory = deque(maxlen=10)

def clean_ai_response(response: str) -> str:
    """AI 응답에서 불필요한 텍스트 제거"""
    return re.sub(r"^\s*\[?AI\]?:?\s*", "", response).strip()

def generate_ai_response(user_id: str, charac_id: str, user_input: str):
    """Firestore 조회 없이 메모리에서 대화 관리, 저장만 Firestore에"""
    chat_id = f"{user_id}-{charac_id}"

    # 캐릭터 데이터 캐싱 (최초 1회만 로드)
    if chat_id not in cached_character_data:
        character_data = get_character_data(user_id, charac_id)
        personality_data = get_personality_data(character_data.get("personality_id", "default"))
        user_nickname = get_user_nickname(user_id)
        cached_character_data[chat_id] = (character_data, personality_data, user_nickname)
    else:
        character_data, personality_data, user_nickname = cached_character_data[chat_id]

    # 사용자 입력을 메모리에 추가
    conversation_memory.append(f"User: {user_input}")

    # Firestore에 사용자 메시지 저장 (비동기적으로 처리 가능하나 여기선 동기 유지)
    save_message(chat_id, user_id, user_input, is_response=False)

    # FAISS에서 유사 메시지 검색 (최소화된 컨텍스트만 사용)
    retrieved_context = get_similar_messages(chat_id, user_input, top_k=1)  # top_k 줄여서 성능 개선
    memory_history = "\n".join(conversation_memory)  # 메모리에서 대화 기록 바로 사용

    # AI 응답 생성
    ai_response = generate_response(
        generate_prompt(
            animaltype=character_data["animaltype"],
            nickname=character_data["nickname"],
            personality_id=character_data["personality"],
            speech_style=personality_data.get("speech_style", "기본 말투"),
            species_speech_pattern=personality_data.get("species_speech_pattern", {}).get(character_data["animaltype"], ""),
            emoji_style=personality_data.get("emoji_style", ""),
            prompt_template=personality_data.get("prompt_template", "나는 친절한 말투로 대답할게!"),
            user_nickname=user_nickname,
            retrieved_context=f"{retrieved_context}\n\n{memory_history}",
            user_input=user_input
        ),
        chat_id
    )

    cleaned_response = clean_ai_response(ai_response)

    # AI 응답을 메모리에 추가
    conversation_memory.append(f"AI: {cleaned_response}")

    # Firestore에 AI 응답 저장
    save_message(chat_id, charac_id, cleaned_response, is_response=True)

    return cleaned_response, None
