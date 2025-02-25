from services import get_user_nickname, get_character_data, get_personality_data, save_message
from vectorstore.faiss_utils import get_similar_messages  # ✅ FAISS 검색 올바른 경로로 import
from services import generate_prompt
from services import generate_response, add_message_to_memory, get_conversation_history, get_conversation_summary, sync_memory_from_firestore, sync_memory_from_faiss
from firebase_admin import firestore

db = firestore.client()

def clean_ai_response(response: str) -> str:
    """🔥 AI 응답에서 불필요한 텍스트 제거"""
    return response.replace("AI: ", "").strip()

def generate_ai_response(user_id: str, charac_id: str, user_input: str):
    """🔥 AI가 사용자 입력에 응답"""
    chat_id = f"{user_id}-{charac_id}"

    # ✅ Firestore에서 캐릭터 및 사용자 정보 가져오기
    character_data = get_character_data(user_id, charac_id)
    personality_data = get_personality_data(character_data.get("personality_id", "default"))
    user_nickname = get_user_nickname(user_id)

    # ✅ Firestore에 사용자 메시지 저장
    save_message(chat_id, user_id, user_input, is_response=False)

    # ✅ Firestore & FAISS 데이터를 LangChain Memory와 동기화
    sync_memory_from_firestore(chat_id)  # Firestore에서 가져온 대화 Memory에 반영
    sync_memory_from_faiss(chat_id, user_input)  # FAISS 검색 결과 Memory에 반영

    # ✅ LangChain Memory에서 대화 히스토리 & 요약된 대화 가져오기
    memory_history = get_conversation_history()
    conversation_summary = get_conversation_summary()
    print(f"🔥 대화 요약 내용: {conversation_summary}")  # ✅ 요약된 대화 확인

    # ✅ FAISS 검색으로 문맥 가져오기
    retrieved_context = get_similar_messages(chat_id, user_input, top_k=5)

    # ✅ 프롬프트 생성
    final_prompt = generate_prompt(
        animaltype=character_data["animaltype"],
        nickname=character_data["nickname"],
        personality_id=character_data["personality"],
        speech_style=personality_data.get("speech_style", "기본 말투"),
        species_speech_pattern=personality_data.get("species_speech_pattern", {}).get(character_data["animaltype"], ""),
        emoji_style=personality_data.get("emoji_style", ""),
        prompt_template=personality_data.get("prompt_template", "나는 친절한 말투로 대답할게!"),
        user_nickname=user_nickname,
        
        retrieved_context=f"{retrieved_context}\n\n{memory_history[-200:]}\n\n{conversation_summary[-200:]}",  
        user_input=user_input
    )

    try:
        # ✅ AI 응답 생성
        ai_response = generate_response(final_prompt, chat_id)
        cleaned_response = clean_ai_response(ai_response)

        # ✅ LangChain Memory 업데이트
        add_message_to_memory(user_input, cleaned_response)

        # ✅ Firestore에 AI 응답 저장 (chat_id와 user_id를 올바르게 설정)
        save_message(chat_id, charac_id, cleaned_response, is_response=True)

        return cleaned_response, None

    except Exception as e:
        print(f"🚨 Error in generate_ai_response: {str(e)}")
        return None, f"API Error: {str(e)}"
