from core.firebase import db
from crewai import Agent, Task, Crew, LLM
import os
from dotenv import load_dotenv
from fastapi import WebSocket
load_dotenv()
import util.PersonalityUtil as PersonalityUtil
import asyncio

class VillageService:
    async def get_character(self,user_id:str) -> list:
        # 1. 동물 불러오기
        characters = db.collection("characters").where(
            "user_id","==",user_id
        ).where(
            "status", "==", "completed"
        ).limit(5)
        # characters_docs = characters.stream()
        # character_list = [c.to_dict() for c in characters.stream()]
        character_list = []
        for c in characters.stream():
            character_dict = c.to_dict()
            character_dict["character_id"] = c.id
            character_list.append(character_dict)
        # print(character_list)
        return character_list
    
    async def get_relationship(self,character_list:list):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        character_1 = character_list[0]
        character_2 = character_list[1]

        llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7,
            api_key=GEMINI_API_KEY
        )

        doctor = Agent(
            role="동물 상호작용 전문가",
            goal=f"{character_1['animaltype']}이(가) {character_2['animaltype']}를 만났을 때 어떻게 상호작용하는지 조사하고 설명하기",
            backstory=f"이 전문가는 {character_1['animaltype']}가 {character_2['animaltype']}를 마주쳤을 때의 행동을 연구하며, 로컬 LLM의 지식을 활용해 구체적인 상호작용을 예측합니다.",
            llm=llm,
            verbose=True,
            tools=[]
        )

        docter_task = Task(
            description=(
                f"{character_1['animaltype']}이(가) {character_2['animaltype']}가 만났을 때 {character_1['animaltype']}이(가) 어떻게 상호작용하는지 조사하고 요약하세요. "
                f"당신의 내장된 지식을 사용해 두 동물이 마주쳤을 때의 {character_1['animaltype']}의 구체적인 행동(예: 싸움, 우호적 반응, 무시 등)을 결론을 100자 이내로 요약해서 말하세요."
            ),
            expected_output=f"{character_1['animaltype']}이(가) {character_2['animaltype']}를 만난 초기 상호작용 설명",
            agent=doctor
        )

        crew = Crew(agents=[doctor], tasks=[docter_task], process="sequential")

        initial_result = crew.kickoff()
        return initial_result
    
    async def create_message(self,websocket:WebSocket ,character_list:list, context:str):
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7,
            api_key=GEMINI_API_KEY
        )

        agent_list = []
        # task_list = []

        # for character in character_list:
        #     personality_id = character['personality']
        #     personality = await PersonalityUtil.get_personality(personality_id)
        #     personality_type = personality['species_speech_pattern']

        #     prompt = f"""
        #         {character['nickname']} 의 성격은 {personality['description']} 캐릭터입니다.
        #         대화 스타일은 {personality_type[character['animaltype']]} 입니다.
        #         캐릭터와 대화를 하세요
        #         """

        #     agent = Agent(
        #         role=f"{character['animaltype']}동물의 '{character['nickname']}' 캐릭터",
        #         goal="다른 캐릭터와 상호작용하기",
        #         # backstory=f"{character_1['nickname']}은(는) 호기심 많은 캐릭터로, {character_2['nickname']} 과 대화를 합니다.",
        #         backstory=prompt,
        #         llm=llm
        #     )
        #     agent_list.append(agent)

        for character in character_list:
            # personality = personality_dict[character['personality']]
            personality_id = character['personality']
            personality = await PersonalityUtil.get_personality(personality_id)
            print(personality)
            personality_type = personality['species_speech_pattern']
        
            prompt = f"""
            {character['nickname']} 의 성격은 {personality['description']} 캐릭터입니다.
            대화 스타일은 {personality_type[character['animaltype']]} 입니다.
            캐릭터와 대화를 하세요
            """
            agent = Agent(
                role=f"{character['animaltype']}동물의 '{character['nickname']}' 캐릭터",
                goal="다른 캐릭터와 상호작용하기",
                # backstory=f"{character_1['nickname']}은(는) 호기심 많은 캐릭터로, {character_2['nickname']} 과 대화를 합니다.",
                backstory=prompt,
                llm=llm
            )
            agent_list.append(agent)
        
        previous_message = ""
        
        character_nickname = ", ".join(character['nickname'] for character in character_list)
        
        for agent in agent_list:
        
            task = Task(
                description=f"서로의 관계('{context}')를 바탕으로"
            )

        for agent in agent_list:
            task = Task

        for i in range(len(agent_list) * 2):
            agent = agent_list[i % 2]
            character = character_list[i % 2]
            task = Task(
                description=f"이전 대화 내용('{previous_message}')과 서로의 관계('{context}')를 바탕으로 {character_nickname}에 대화의 응답하라. 이전 대화가 없으면 기본 인사로 시작하라.",
                agent=agent,
                expected_output=f"{character_nickname}와의 대화 내용. 이전 대화가 있으면 그에 맞춰 답변하고, 없으면 자연스러운 인사로 시작함.",
            )
        
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process="sequential",
                verbose=True,
            )
        
            result = crew.kickoff()
        
            crew_output_dict = result.dict()
        
            previous_message = crew_output_dict['raw']
        
            await websocket.send_json({
                "message" : crew_output_dict['raw'],
                "character" : character['id']
            })
