from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_google_genai import GoogleGenerativeAI
import google.generativeai as genai
import os
from dotenv import load_dotenv
from services import get_chat_messages
import vectorstore.faiss_utils as faiss_utils

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

def sync_memory_from_firestore(chat_id):
    """🔥 Firestore에서 가져온 대화 기록을 LangChain Memory에 추가"""
    chat_history = get_chat_messages(chat_id)  # Firestore에서 가져오기
    for message in chat_history:
        buffer_memory.save_context({"input": message["content"]}, {"output": ""})  # Memory에 저장
    print(f"✅ Firestore에서 {len(chat_history)}개의 메시지를 불러와 Memory에 동기화 완료!")

def sync_memory_from_faiss(chat_id, user_input):
    """🔥 FAISS에서 가져온 유사한 문장을 LangChain Memory에 추가"""
    similar_messages = faiss_utils.get_similar_messages(chat_id, user_input, top_k=3)
    if similar_messages:
        buffer_memory.save_context({"input": user_input}, {"output": similar_messages})
        print(f"✅ FAISS 검색된 문장 {len(similar_messages)}개를 Memory에 추가!")

def add_message_to_memory(user_message: str, ai_response: str):
    """🔥 LangChain Memory에 사용자와 AI의 대화를 추가하면서 요약 개선"""
    buffer_memory.save_context({"input": user_message}, {"output": ai_response})

    # ✅ 기존 요약을 불러옴
    current_summary = summary_memory.load_memory_variables({}).get("summary", "")

    # ✅ 새로운 정보를 요약하는 방식으로 변경
    updated_summary = f"{current_summary}\n[사용자]: {user_message}\n[AI]: {ai_response}"

    # ✅ 중복 문장 제거 및 핵심 정보만 유지
    updated_summary = clean_summary(updated_summary)

    summary_memory.save_context({"input": user_message}, {"output": updated_summary})
    
def generate_response(user_input: str, chat_id: str) -> str:
    """🔥 LangChain Memory + FAISS를 활용한 AI 응답 생성"""
    sync_memory_from_firestore(chat_id)  # Firestore 데이터 반영
    sync_memory_from_faiss(chat_id, user_input)  # FAISS 검색 결과 반영

    conversation_summary = get_conversation_summary()
    full_input = f"{conversation_summary}\n\n{user_input}"

    response = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21").generate_content([full_input])

    if not response.text:
        return "죄송해요, 적절한 응답을 생성할 수 없어요."

    ai_response = response.text.strip()
    
    # ✅ Memory에 대화 추가
    add_message_to_memory(user_input, ai_response)
    
    return ai_response

def get_conversation_summary():
    """🔥 LangChain Memory에서 대화 요약을 가져오면서 불필요한 정보 제거"""
    summary = summary_memory.load_memory_variables({}).get("summary", "")

    # ✅ 핵심 단어 위주로 요약 압축
    return refine_summary(summary)

def get_conversation_history():
    """LangChain Memory에서 전체 대화 기록 가져오기"""
    return buffer_memory.load_memory_variables({}).get("chat_history", "")

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

def refine_summary(summary):
    """🔥 중요한 정보만 남기고 불필요한 문장 제거"""
    keywords = ["좋아하는", "취미", "기억", "말씀", "곁에 있을게요"]  # 중요한 키워드
    lines = summary.split("\n")
    refined_lines = [line for line in lines if any(keyword in line for keyword in keywords)]

    refined_summary = "\n".join(refined_lines)
    return refined_summary[-500:] if len(refined_summary) > 500 else refined_summary