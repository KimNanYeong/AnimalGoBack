from langchain.memory import ConversationBufferMemory
import google.generativeai as genai
import os
from dotenv import load_dotenv
from services import get_recent_chat_messages
import vectorstore.faiss_utils as faiss_utils
import time  # ✅ 실행 시간 측정을 위한 모듈 추가

# ✅ 환경 변수 로드
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

# ✅ Gemini API 키 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)

# ✅ LangChain Memory 설정 (대화 기록)
buffer_memory = ConversationBufferMemory(memory_key="chat_history")  # 최근 대화 저장

# ✅ 전역 변수로 요약 관리
conversation_summary = ""


def sync_memory_from_firestore(chat_id, limit_count=10):
    """🔥 Firestore에서 가져온 최신 대화 기록을 LangChain Memory에 추가 (중복 방지)"""
    chat_history = get_recent_chat_messages(chat_id, limit_count)
    existing_memory = get_conversation_history()
    seen_texts = set(existing_memory.split("\n"))

    for message in chat_history:
        if message["content"] not in seen_texts:
            buffer_memory.save_context({"input": message["content"]}, {"output": ""})
            seen_texts.add(message["content"])


def sync_memory_from_faiss(chat_id, user_input):
    """🔥 FAISS에서 가져온 유사한 문장을 LangChain Memory에 추가"""
    similar_messages = faiss_utils.get_similar_messages(chat_id, user_input, top_k=3)
    if similar_messages:
        buffer_memory.save_context({"input": user_input}, {"output": similar_messages})


def add_message_to_memory(user_message: str, ai_response: str):
    """🔥 LangChain Memory에 사용자와 AI의 대화를 추가 + 요약 업데이트"""
    global conversation_summary
    start_time = time.time()

    conversation_history = get_conversation_history()

    # ✅ 중복 방지
    if ai_response in conversation_history:
        print(f"⚠️ `add_message_to_memory()` 중복 실행 방지: {ai_response}")
        return

    buffer_memory.save_context({"input": user_message}, {"output": ai_response})

    # ✅ 새로운 정보를 요약
    conversation_summary = generate_summary(user_message, ai_response, conversation_summary)

    end_time = time.time()
    print(f"🔥 `add_message_to_memory()` 실행 시간: {end_time - start_time:.3f}초")


def generate_response(user_input: str, chat_id: str) -> str:
    """🔥 LangChain Memory + FAISS를 활용한 AI 응답 생성"""
    sync_memory_from_firestore(chat_id)
    sync_memory_from_faiss(chat_id, user_input)

    full_input = f"{conversation_summary}\n\n[사용자]: {user_input}"

    start_time = time.time()
    response = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21").generate_content([full_input])
    end_time = time.time()

    print(f"🔥 Gemini 응답 생성 완료: {end_time - start_time:.3f}초")

    if not response.text:
        return "죄송해요, 적절한 응답을 생성할 수 없어요."

    ai_response = response.text.strip()

    # ✅ Memory에 대화 추가
    add_message_to_memory(user_input, ai_response)

    return ai_response


def get_conversation_history():
    """🔥 LangChain Memory에서 최근 대화 기록 가져오기"""
    history = buffer_memory.load_memory_variables({}).get("chat_history", "")
    return history[-200:]


def generate_summary(user_message: str, ai_response: str, current_summary: str = "") -> str:
    """🔥 Gemini API를 사용해 대화 요약 생성"""
    full_input = f"{current_summary}\n[사용자]: {user_message}\n[AI]: {ai_response}"

    model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
    response = model.generate_content([full_input])

    if not response.text:
        return current_summary  # 응답이 없으면 기존 요약 유지

    return response.text.strip()


def sync_memory_from_firestore_on_start(chat_id, limit_count=50):
    """🔥 서버 시작 시 Firestore에서 특정 채팅방의 최근 대화 기록을 LangChain Memory에 추가"""
    chat_history = get_recent_chat_messages(chat_id, limit_count)
    print(f"🔥 Firestore에서 `{chat_id}` 최근 {limit_count}개 대화 불러오기 완료!")

    for message in reversed(chat_history):
        if message["sender"] == "AI":
            buffer_memory.save_context({"input": ""}, {"output": message["content"]})
        else:
            buffer_memory.save_context({"input": message["content"]}, {"output": ""})

def get_conversation_summary():
    """🔥 LangChain Memory에서 대화 요약을 가져오기"""
    global conversation_summary  # ✅ 전역 변수 사용
    return conversation_summary[-500:] if len(conversation_summary) > 500 else conversation_summary