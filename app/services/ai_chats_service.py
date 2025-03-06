import os
from firebase_admin import firestore
import google.generativeai as genai
from crewai import Agent, Task, Crew, LLM
import asyncio
from dotenv import load_dotenv
import re

db = firestore.client()

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"
model = genai.GenerativeModel(GEMINI_MODEL)  # default model

async def check_character_exists(character_id):
    """Firestore에서 특정 캐릭터가 존재하는지 확인"""
    character_ref = db.collection("characters").document(character_id).get()
    return character_ref.exists

async def status_completed(doc_id: str) -> bool:
    # characters 컬렉션의 특정 문서 참조 및 필드 가져오기
    status = db.collection("characters").document(doc_id).get().to_dict().get("status")
    # status가 "completed"인지 확인
    return status == "completed"

class CustomLLM(LLM):
    def __init__(self, model=GEMINI_MODEL):
        self.model = model
        super().__init__(model=model, function=self._generate_response)

    async def _generate_response(self, prompt):
        """Gemini 2.0 API를 호출하여 AI 응답 생성"""
        model_gen = genai.GenerativeModel(self.model)
        response = model_gen.generate_content(prompt)
        return response.text

    async def call(self, prompt: str, callbacks=None) -> str:
        """crewai 라이브러리로부터 전달받은 메시지를 Gemini API가 이해할 수 있는 형식으로 변환"""
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

async def get_personality_traits(personality):
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

async def create_animal_agent(charac_id):
    doc_ref = db.collection("characters").document(charac_id)
    data = doc_ref.get().to_dict()

    # 🔄 personality에 해당하는 traits 가져오기
    personality = data.get("personality", "기본 성격")
    traits =  await get_personality_traits(personality)

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

async def start_conversation(request, charac1, charac2):
    #  마스터 AI가 주제 발표
    topic_response = await master_agent.llm._generate_response("30글자 이내로 된 공통 대화 주제 형용사와 명사로된 서술체로 2개만 생각하고 랜덤으로 1개 선택")
    match = re.search(r"\*\*(.+?)\*\*", topic_response)
    topic = match.group(1).strip() if match else "일상 대화"

    print("topic : ", topic)

    agent_1 = await create_animal_agent(charac1)
    agent_2 = await create_animal_agent(charac2)

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
        if await request.is_disconnected():
            print("Client disconnected, stopping conversation.")
            break
        # agent_1의 응답 생성
        response_1 = await agent_1.llm._generate_response(f"주제: {topic}\n[{agent_2.role}]에게 [{agent_1.role}]로서 묻는 대화를 40글자 이내로 시작하라:\n[{agent_1.backstory}]")
        print("response_1 :", response_1)
        yield f'{{"speaker": "{charac1}", "message": "{response_1}"}}\n'
 
        save_message_and_update_chat(chat_id, charac1, response_1)
        await asyncio.sleep(0)

        if await request.is_disconnected():
            print("Client disconnected, stopping conversation.")
            break
            
        # agent_2의 응답 생성
        response_2 = await agent_2.llm._generate_response(f"주제: {topic}\n[{agent_2.role}]로서 30 글자 대답하라:\n[{agent_2.backstory}]")

        print("response_2 :", response_2)
        yield f'{{"speaker": "{charac2}", "message": "{response_2}"}}\n'

        save_message_and_update_chat(chat_id, charac2, response_2)
        await asyncio.sleep(0)

    # 🔹 채팅방 마지막 활동 시간 업데이트 (마지막 메시지 기준)
    chat_ref.update({
        "last_active_at": firestore.SERVER_TIMESTAMP
    })