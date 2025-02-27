from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_google_genai import GoogleGenerativeAI
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

# ✅ LangChain Memory 설정 (대화 기록 + 요약 Memory + 개체 정보 Memory)
buffer_memory = ConversationBufferMemory(memory_key="chat_history")  # 최근 대화 저장
summary_memory = ConversationSummaryMemory(
    llm=GoogleGenerativeAI(model="gemini-2.0-flash-thinking-exp-01-21"), memory_key="summary"
)

def sync_memory_from_firestore(chat_id, limit_count=10):
    """🔥 Firestore에서 가져온 최신 대화 기록을 LangChain Memory에 추가 (중복 방지)"""
    chat_history = get_recent_chat_messages(chat_id, limit_count)  # 최신 limit_count 개만 가져오기
    existing_memory = get_conversation_history()  # 기존 대화 기록 가져오기
    seen_texts = set(existing_memory.split("\n"))  # 🔥 중복 메시지 방지용 set()

    for message in chat_history:
        if message["content"] not in seen_texts:  # 🔥 중복 메시지가 아닐 때만 추가
            buffer_memory.save_context({"input": message["content"]}, {"output": ""})
            seen_texts.add(message["content"])  # 추가한 메시지를 기록

def sync_memory_from_faiss(chat_id, user_input):
    """🔥 FAISS에서 가져온 유사한 문장을 LangChain Memory에 추가"""
    similar_messages = faiss_utils.get_similar_messages(chat_id, user_input, top_k=3)
    if similar_messages:
        buffer_memory.save_context({"input": user_input}, {"output": similar_messages})

def add_message_to_memory(user_message: str, ai_response: str):
    """🔥 LangChain Memory에 사용자와 AI의 대화를 추가 (최적화)"""

    start_time = time.time()  # ⏳ 실행 시작 시간 기록

    # ✅ 기존 대화 기록 가져오기 (최적화)
    conversation_history = get_conversation_history()

    # ✅ 이미 저장된 응답이라면 추가 저장하지 않음
    if ai_response in conversation_history:
        print(f"⚠️ `add_message_to_memory()` 중복 실행 방지: {ai_response}")
        return

    buffer_memory.save_context({"input": user_message}, {"output": ai_response})

    # ✅ 기존 요약을 불러옴
    current_summary = summary_memory.load_memory_variables({}).get("summary", "")

    # ✅ 새로운 정보를 요약하는 방식으로 변경
    updated_summary = f"{current_summary}\n[사용자]: {user_message}\n[AI]: {ai_response}"

    # ✅ 중복 문장 제거 및 핵심 정보만 유지
    updated_summary = clean_summary(updated_summary)

    summary_memory.save_context({"input": user_message}, {"output": updated_summary})

    end_time = time.time()  # ⏳ 실행 종료 시간 기록

    print(f"🔥 `add_message_to_memory()` 실행 시간: {end_time - start_time:.3f}초")  # 🚀 실행 시간 출력
    
def generate_response(user_input: str, chat_id: str) -> str:
    """🔥 LangChain Memory + FAISS를 활용한 AI 응답 생성"""
    sync_memory_from_firestore(chat_id)  # Firestore 데이터 반영
    sync_memory_from_faiss(chat_id, user_input)  # FAISS 검색 결과 반영

    conversation_summary = get_conversation_summary()
    full_input = f"{conversation_summary}\n\n{user_input}"

    start_time = time.time()  # ✅ 응답 생성 시작 시간
    response = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21").generate_content([full_input])
    end_time = time.time()  # ✅ 응답 생성 완료 시간

    print(f"🔥 Gemini 응답 생성 완료: {end_time - start_time:.3f}초")  # ✅ 실행 시간 출력

    if not response.text:
        return "죄송해요, 적절한 응답을 생성할 수 없어요."

    ai_response = response.text.strip()
    
    # ✅ Memory에 대화 추가
    add_message_to_memory(user_input, ai_response)
    
    return ai_response

def get_conversation_history():
    """🔥 LangChain Memory에서 최근 대화 기록 가져오기"""
    history = buffer_memory.load_memory_variables({}).get("chat_history", "")
    return history[-200:]  # 🔥 최신 200자까지만 유지

def get_conversation_summary():
    """🔥 LangChain Memory에서 대화 요약을 가져오면서 불필요한 정보 제거"""
    summary = summary_memory.load_memory_variables({}).get("summary", "")
    return summary[-500:] if len(summary) > 500 else summary  # 🔥 최대 500자까지만 유지

def clean_summary(summary):
    """🔥 중복 문장 제거 및 핵심 정보만 유지하는 함수"""
    lines = summary.split("\n")
    unique_lines = []
    seen = set()

    for line in lines:
        if line not in seen:  # 중복 방지
            seen.add(line)
            unique_lines.append(line)

    # ✅ 최신 500자까지만 유지하여 요약이 너무 길어지는 것 방지
    cleaned_summary = "\n".join(unique_lines)
    return cleaned_summary[-500:] if len(cleaned_summary) > 500 else cleaned_summary

def sync_memory_from_firestore_on_start(chat_id, limit_count=50):
    """🔥 서버 시작 시 Firestore에서 특정 채팅방의 최근 대화 기록을 LangChain Memory에 추가"""
    chat_history = get_recent_chat_messages(chat_id, limit_count)
    print(f"🔥 Firestore에서 `{chat_id}` 최근 {limit_count}개 대화 불러오기 완료!")

    for message in reversed(chat_history):  # 🔥 최신순으로 LangChain Memory에 추가
        if message["sender"] == "AI":
            buffer_memory.save_context({"input": "", "output": message["content"]})  # 🔥 AI 응답 포함
        else:
            buffer_memory.save_context({"input": message["content"]}, {"output": ""})  # 🔥 사용자 입력 추가

