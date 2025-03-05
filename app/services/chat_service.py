from services import get_user_nickname, get_character_data, get_personality_data, save_message
from vectorstore.faiss_utils import get_similar_messages  # ✅ FAISS 검색 올바른 경로로 import
from services import generate_prompt, sync_memory_from_firestore_on_start
from services import generate_response, add_message_to_memory, get_conversation_history, get_conversation_summary, sync_memory_from_firestore, sync_memory_from_faiss
from firebase_admin import firestore
import re

db = firestore.client()

# ✅ 캐릭터 & 사용자 정보 캐싱 (서버 실행 시 한 번만 로드)
cached_character_data = {}

def clean_ai_response(response: str) -> str:
    """🔥 AI 응답에서 '[AI]:', 'AI: ', '\nAI:' 등 불필요한 텍스트 제거"""
    response = re.sub(r"^\s*\[?AI\]?:?\s*", "", response)  # 앞부분의 `[AI]:`, `AI:` 제거
    return response.strip()


def generate_ai_response(user_id: str, charac_id: str, user_input: str):
    """🔥 Firestore 저장을 `generate_ai_response()`에서 직접 실행하여 최적화"""
    chat_id = f"{user_id}-{charac_id}"

    # ✅ Firestore에서 캐릭터 & 사용자 정보 불러오기 (캐싱 적용)
    if chat_id not in cached_character_data:
        character_data = get_character_data(user_id, charac_id)
        personality_data = get_personality_data(character_data.get("personality_id", "default"))
        user_nickname = get_user_nickname(user_id)
        cached_character_data[chat_id] = (character_data, personality_data, user_nickname)
    else:
        character_data, personality_data, user_nickname = cached_character_data[chat_id]

    # 🔥 서버 재시작 시 Firestore에서 최근 대화 불러오기 (한 번만 실행)
    if len(get_conversation_history()) == 0:
        print(f"🔥 서버 재시작 감지! Firestore에서 `{chat_id}` 최근 대화 불러오는 중...")
        sync_memory_from_firestore_on_start(chat_id)  # 🔥 최근 대화 복원

    # ✅ Firestore에 사용자 메시지 저장 (AI 응답 생성 전에 실행)
    save_message(chat_id, user_id, user_input, is_response=False)

    retrieved_context = get_similar_messages(chat_id, user_input, top_k=3)  # FAISS 검색
    memory_history = get_conversation_history()  # LangChain Memory에서 최근 대화 가져오기
    conversation_summary = get_conversation_summary()  # 요약된 대화 내용 가져오기

    # ✅ AI 응답 생성

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
            retrieved_context=f"{retrieved_context}\n\n{memory_history[-200:]}\n\n{conversation_summary[-200:]}",  # ✅ LangChain Memory & FAISS 결과 반영
            user_input=user_input
        ),
        chat_id
    )


    cleaned_response = clean_ai_response(ai_response)

    # ✅ Firestore에 AI 응답 즉시 저장 (딜레이 방지)
    save_message(chat_id, charac_id, cleaned_response, is_response=True)

    # ✅ Firestore 저장 후 FAISS 검색 실행
    retrieved_context = get_similar_messages(chat_id, user_input, top_k=3)

    # ✅ LangChain Memory 동기화 (최신 메시지 기반)
    if len(get_conversation_history()) < 5:
        sync_memory_from_firestore(chat_id)
        sync_memory_from_faiss(chat_id, user_input)

    return cleaned_response, None