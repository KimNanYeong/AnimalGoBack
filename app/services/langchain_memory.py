from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
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
summary_memory = ConversationSummaryMemory(llm=genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21"), memory_key="summary")

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
    """🔥 LangChain Memory에 사용자와 AI의 대화를 추가 + SummaryMemory도 업데이트"""
    start_time = time.time()

    conversation_history = get_conversation_history()

    # ✅ 중복 방지
    if ai_response in conversation_history:
        print(f"⚠️ `add_message_to_memory()` 중복 실행 방지: {ai_response}")
        return

    # ✅ BufferMemory에 대화 추가
    buffer_memory.save_context({"input": user_message}, {"output": ai_response})

    # ✅ SummaryMemory에도 대화 추가 (자동 요약)
    summary_memory.save_context({"input": user_message}, {"output": ai_response})

    end_time = time.time()
    print(f"🔥 `add_message_to_memory()` 실행 시간: {end_time - start_time:.3f}초")


def generate_response(user_input: str, chat_id: str) -> str:
    """🔥 LangChain Memory + FAISS를 활용한 AI 응답 생성"""
    sync_memory_from_firestore(chat_id)
    sync_memory_from_faiss(chat_id, user_input)

    # ✅ SummaryMemory에서 대화 요약 가져오기
    conversation_summary = get_conversation_summary()

    full_input = f"{conversation_summary}\n\n[사용자]: {user_input}"

    start_time = time.time()
    response = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21").generate_content([full_input])
    end_time = time.time()

    print(f"🔥 Gemini 응답 생성 완료: {end_time - start_time:.3f}초")

    if not response.text:
        return "죄송해요, 적절한 응답을 생성할 수 없어요."

    ai_response = response.text.strip()

    # ✅ Memory에 대화 추가 (SummaryMemory도 함께 업데이트됨)
    add_message_to_memory(user_input, ai_response)

    return ai_response


def get_conversation_history(limit_count=5):
    """🔥 LangChain Memory에서 최근 N개의 대화 기록 가져오기"""
    history = buffer_memory.load_memory_variables({}).get("chat_history", [])
    return history[-limit_count:]  # ✅ 최근 5개 대화만 반환


def get_conversation_summary():
    """🔥 LangChain SummaryMemory에서 대화 요약 가져오기"""
    return summary_memory.load_memory_variables({}).get("summary", "")


def sync_memory_from_firestore_on_start(chat_id, limit_count=50):
    """🔥 서버 시작 시 Firestore에서 특정 채팅방의 최근 대화 기록을 LangChain Memory에 추가"""
    chat_history = get_recent_chat_messages(chat_id, limit_count)
    print(f"🔥 Firestore에서 `{chat_id}` 최근 {limit_count}개 대화 불러오기 완료!")

    # ✅ 기존 메모리에 있는 대화 확인 (중복 방지)
    existing_memory = get_conversation_history()
    seen_texts = set(existing_memory)

    for message in reversed(chat_history):
        if message["content"] not in seen_texts:
            if message["sender"] == "AI":
                buffer_memory.save_context({"input": ""}, {"output": message["content"]})
                summary_memory.save_context({"input": ""}, {"output": message["content"]})
            else:
                buffer_memory.save_context({"input": message["content"]}, {"output": ""})
                summary_memory.save_context({"input": message["content"]}, {"output": ""})

            seen_texts.add(message["content"])  # ✅ 중복 방지 처리
