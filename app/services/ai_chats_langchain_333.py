import os 
import re
import asyncio
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from crewai import Agent, Task, Crew, LLM

# [수정 추가] LangChain 관련 최신 모듈 임포트
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings  # NOTE: Gemini API용 Embedding이 별도로 있으면 대체 필요

# from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import OpenAIEmbeddings


# warnings.filterwarnings("ignore", category=DeprecationWarning)

#FIREBASE_CRED_PATH = r"C:/data/fbkeys/fbkey0305.json"
FIREBASE_CRED_PATH = r"C:/data/fbkeys/fbkey.json"


if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
# genai.configure(api_key=GEMINI_API_KEY)

# def save_message_and_update_chat(chat_id, sender, message):
#     chat_ref = db.collection("chats").document(chat_id)

#     if not chat_ref.get().exists:
#         chat_ref.set({
#             "last_message": {"content": "", "sender": ""},
#             "last_active_at": firestore.SERVER_TIMESTAMP
#         })

#     db.collection("chats").document(chat_id).collection("messages").add({
#         "content": message,
#         "sender": sender,
#         "timestamp": firestore.SERVER_TIMESTAMP
#     })

#     chat_ref.set({
#         "last_message": {"content": message, "sender": sender},
#         "last_active_at": firestore.SERVER_TIMESTAMP
#     }, merge=True)

# 수정: gemini-pro 모델 사용  -- 언젠가 사용 ...
# llm = ChatGoogleGenerativeAI(google_api_key=GEMINI_API_KEY, model="gemini-pro")
# memory = ConversationBufferMemory()
# conversation = ConversationChain(llm=llm, memory=memory)

# def chat_with_memory(chat_id, sender, message):
#     save_message_and_update_chat(chat_id, sender, message)
#     print("chat_id =", chat_id, " message =", message)
#     response = conversation.run(message)
#     print("chat_id =", chat_id, " response ==", response)
#     save_message_and_update_chat(chat_id, "bot", response)
#     return response


env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
print("dot_env=",env_path )
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

print ("GEMINI-API_KEY", GEMINI_API_KEY )

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"
model = genai.GenerativeModel(GEMINI_MODEL)  # default model

print (" start 000 ")

def check_character_exists(character_id):
    """Firestore에서 특정 캐릭터가 존재하는지 확인"""
    character_ref = db.collection("characters").document(character_id).get()
    return character_ref.exists

def status_completed(doc_id: str) -> bool:
    # characters 컬렉션의 특정 문서 참조 및 필드 가져오기
    status = db.collection("characters").document(doc_id).get().to_dict().get("status")
    # status가 "completed"인지 확인
    return status == "completed"

class CustomLLM(LLM):
    def __init__(self, model=GEMINI_MODEL):
        self.model = model
        super().__init__(model=model, function=self._generate_response)

    def _generate_response(self, prompt):
        """Gemini 2.0 API를 호출하여 AI 응답 생성"""
        model_gen = genai.GenerativeModel(self.model)
        response = model_gen.generate_content(prompt)
        return response.text

    def call(self, prompt: str, callbacks=None) -> str:
        """crewai 라이브러리로부터 전달받은 메시지를 Gemini API가 이해할 수 있는 형식으로 변환"""
        return self._generate_response(prompt)
    
    # [수정 추가] LangChain 호환을 위한 _call 메서드 추가 (RetrievalQA 체인 등에서 내부적으로 사용)
    def _call(self, prompt: str, stop=None) -> str:
        return self._generate_response(prompt)


# 🔄 Firestore에 메시지 저장 및 업데이트 함수
def save_message_and_update_chat(chat_id, sender, message):
    """메시지를 저장하고 last_message와 last_active_at 필드를 업데이트"""

    chat_ref = db.collection("chats").document(chat_id)
    # 🔹 메시지 저장
    db.collection("chats").document(chat_id).collection("messages").add({
        "content": message,
        "sender": sender,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    # 🔹 last_message와 sender, last_active_at 업데이트
    chat_ref.update({
        "last_message": {
            "content": message,
            "sender": sender
        },
        "last_active_at": firestore.SERVER_TIMESTAMP
    })


def get_personality_traits(personality):
    """personality_traits 컬렉션에서 speech_style, species_speech_pattern, emoji_style 가져오기"""
    traits_ref = db.collection("personality_traits").document(personality)
    traits_doc = traits_ref.get()
    if traits_doc.exists:
        traits_data = traits_doc.to_dict()
        return {
            "speech_style": traits_data.get("speech_style", "기본 말투"),
            "species_speech_pattern": traits_data.get("species_speech_pattern", "기본 말투 패턴"),
            "emoji_style": traits_data.get("emoji_style", "🙂")
        }
    else:
        print(f"❌ '{personality}'에 해당하는 personality_traits가 없습니다.")
        return {
            "speech_style": "기본 말투",
            "species_speech_pattern": "기본 말투 패턴",
            "emoji_style": "🙂"
        }

#  마스터 AI (대화 주제 선언)
master_agent = Agent(
    role="마스터 AI",
    goal="주제 정하기",
    backstory="어떤 동물 캐릭터들이 대화할 수 있는 주제를 생각해보고 랜덤으로 한가지만 정하는거야",
    llm=CustomLLM()
)

# def create_animal_agent(charac_id):
#     # doc_ref = db.collection("characters").document(charac_id)
#     # data = doc_ref.get().to_dict()

#     # # 🔄 personality에 해당하는 traits 가져오기
#     # personality = data.get("personality", "기본 성격")
#     # traits = get_personality_traits(personality)

#     prompt_template = f"""
#         **역할**
#         - 나는 가상의 "virtual cat" 입니다 
#         - 나의 이름은 "영리한 냥이"입니다.
#         - 나의 성격은 "온순함"이며, "" 스타일로 대화합니다.

#         **대화 스타일**
#         - "dog"의 입장에서 감정을 담아 자연스럽게 대화하세요.
#         - "사나움" 같은 말투를 활용하세요.
#         - 문장은 간결하고 직관적으로 유지하세요.

#         # **이모지 사용**
#         # - "emoji_style" 이모지를 한번만 자연스럽게 사용하세요.
#     """
#     return Agent(
#         role="영리한냥이",
#         goal="온순함",
#         backstory=prompt_template,
#         llm=CustomLLM()
#     )
def create_animal_agent(charac_id):
    doc_ref = db.collection("characters").document(charac_id)
    data = doc_ref.get().to_dict()

    # 🔄 personality에 해당하는 traits 가져오기
    personality = data.get("personality", "기본 성격")
    traits = get_personality_traits(personality)

    prompt_template = f"""
        **역할**
        - 나는 가상의 "{data.get('animaltype', 'animal')}" 입니다 
        - 나의 닉네임은 "{data.get('nickname', '매우 날쌘 동물')}"입니다.
        - 나의 성격은 "{personality}"이며, "{traits['speech_style']}" 스타일로 대화합니다.

        **대화 스타일**
        - {data.get('animaltype', '동물')}의 입장에서 감정을 담아 자연스럽게 대화하세요.
        - "{traits['species_speech_pattern']}" 같은 말투를 활용하세요.
        - 문장은 간결하고 직관적으로 유지하세요.

        **이모지 사용**
        - "{traits['emoji_style']}" 이모지를 한번만 자연스럽게 사용하세요.
    """
    return Agent(
        role=data["nickname"],
        goal=data["personality"],
        backstory=prompt_template,
        llm=CustomLLM()
    )

def start_conversation(charac1, charac2):
    #  마스터 AI가 주제 발표
    print("topic 스타트",charac1, "_", charac2)

    topic_response = master_agent.llm._generate_response("30글자 이내로 된 공통 대화 주제 형용사와 명사로된 서술체로 2개만 생각하고 랜덤으로 1개 선택")
    match = re.search(r"\*\*(.+?)\*\*", topic_response)
    topic = match.group(1).strip() if match else "일상 대화"

    print("topic : ", topic)

    agent_1 = create_animal_agent(charac1)
    agent_2 = create_animal_agent(charac2)

    chat_id = f"{charac1}_{charac2}"
    chat_ref = db.collection("chats").document(chat_id)
    user_id = charac1.split('-')[0]
    if not chat_ref.get().exists:
        chat_ref.set({
            "chat_id": chat_id,
            "participants": [charac1, charac2],
            "create_at": firestore.SERVER_TIMESTAMP,
            "last_active_at": None,
            "last_message": None,
            "user_id": user_id
        })

    for i in range(3):
        # agent_1의 응답 생성
        response_1 = agent_1.llm._generate_response(f"주제: {topic}\n[{agent_2.role}]에게 [{agent_1.role}]로서 묻는 대화를 40글자 이내로 시작하라:\n[{agent_1.backstory}]")
        print("response_1 :", response_1)
        yield f'{{"speaker": "{charac1}", "message": "{response_1}"}}\n'
 
        save_message_and_update_chat(chat_id, charac1, response_1)
       

        # agent_2의 응답 생성
        response_2 = agent_2.llm._generate_response(f"주제: {topic}\n[{agent_2.role}]로서 30 글자 대답하라:\n[{agent_2.backstory}]")

        print("response_2 :", response_2)
        yield f'{{"speaker": "{charac2}", "message": "{response_2}"}}\n'

        save_message_and_update_chat(chat_id, charac2, response_2)        

    # 🔹 채팅방 마지막 활동 시간 업데이트 (마지막 메시지 기준)
    chat_ref.update({
        "last_active_at": firestore.SERVER_TIMESTAMP
    })

    return response_2 # 작업  끝

# [RAG 추가] Retrieval Augmented Generation (RAG) 구현
def load_documents():
    """
    Firestore의 "knowledge" 컬렉션에서 문서를 불러와 리스트로 반환하는 함수.
    각 문서는 'content' 필드를 포함한다고 가정합니다.
    """
    docs = []
    docs_ref = db.collection("knowledge").stream()  # Firestore에 'knowledge' 컬렉션이 있어야 함
    for doc in docs_ref:
        doc_data = doc.to_dict()
        content = doc_data.get("content", "")
        if content:
            docs.append(content)
    return docs

# 문서 로드 및 기본 문서 처리
documents = load_documents()
if not documents:
    # [수정 추가] 기본 문서 (예시)
    documents = [
        "이 문서는 RAG 시스템 예시를 위한 기본 문서입니다.",
        "Gemini API를 활용한 LangChain RAG 구현 예제입니다."
    ]

# [RAG 추가] FAISS 벡터 스토어 생성 (여기서는 OpenAIEmbeddings 사용 – Gemini에 맞는 embedding 모델로 교체 가능)
embeddings = OpenAIEmbeddings()  # NOTE: Gemini API 전용 embedding 모델이 있다면 해당 모델로 변경 필요
vector_store = FAISS.from_texts(documents, embeddings)
retriever = vector_store.as_retriever()

# [RAG 추가] RetrievalQA 체인 생성 – CustomLLM을 Gemini API 호출용 LLM으로 사용
rag_chain = RetrievalQA.from_chain_type(
    llm=CustomLLM(),
    chain_type="stuff",  # chain_type은 필요에 따라 조정 가능
    retriever=retriever
)

def answer_query(query):
    """
    RAG 체인을 사용하여 입력 쿼리에 대해 검색된 문서와 함께 답변 생성
    """
    return rag_chain.run(query)


# __main__ 실행 예시
if __name__ == "__main__":
    # 기존 대화 흐름 실행 예시

    conversation = list(start_conversation("1-dog019", "1-horse001"))
    print("대화 내용:")
    for line in conversation:
        print(line)
    
    # # [RAG 추가] RAG 체인을 이용한 질의응답 테스트
    # test_query = "동물 캐릭터의 일반적인 특징은 무엇인가요?"
    # rag_answer = answer_query(test_query)
    # print("\n[RAG 체인 결과] 질의: ", test_query)
    # print("답변: ", rag_answer)
