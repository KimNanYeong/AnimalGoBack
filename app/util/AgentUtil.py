# -*- coding: utf-8 -*-
"""
AgentUtil.py
============

이 파일은 사용자별 에이전트와 태스크를 관리하기 위한 모듈입니다.
주요 클래스와 함수는 다음과 같습니다:

- AgentUtil 클래스: 사용자 에이전트 및 태스크를 등록, 조회, 수정, 삭제하는 기능을 제공.
- create_agent: 사용자별 에이전트와 태스크를 비동기적으로 생성하는 함수.
- run: 에이전트의 실행 로직을 담당하는 함수.
- destroy_agent: 지정 사용자의 에이전트와 태스크를 삭제하는 함수.

주의:
- 멀티스레드 환경을 고려하여 _lock과 _user_locks를 사용하여 동시성 문제를 해결합니다.
- 여러 위치에서 AgentUtil이 호출되는 경우 데이터 공유 여부에 주의해야 합니다.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from crewai import Crew, Agent, LLM, Task
import os
import threading

import util.PersonalityUtil as PersonalityUtil


class AgentUtil:
    def __init__(self):
        self.llm = LLM(
            model="gemini/gemini-1.5-flash",
            temperature=0.7,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        self.user_agent_dict: Dict[str, List[Agent]] = {}
        self.user_task_dict: Dict[str, List[Any]] = {}
        self._lock = threading.Lock()
        self._user_locks: Dict[str, threading.Lock] = {}
        self.manager_agent:Agent = Agent(
            role=f"동물 캐릭터들의 이동을 제어하는 매니저",
            goal="모든 동물들의 좌표를 반환합니다.",
            # backstory=f"성격 : ({personality['description']}), 대화 방식 : ({personality_type}), 화면에서 돌아다닙니다.",
            backstory="화면 사이즈 안에서 좌표를 반환하는 매니저",
            llm=self.llm
        )

    def get_manager_agent(self):
        return self.manager_agent

    def _get_user_lock(self, user_id: str) -> threading.Lock:
        """
        특정 사용자(user_id)를 위한 잠금(lock)을 반환합니다.
        """
        with self._lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = threading.Lock()
            return self._user_locks[user_id]

    def set_agent(self, user_id: str, agent: Agent) -> None:
        """
        특정 사용자(user_id)에 agent를 추가합니다.
        """
        lock = self._get_user_lock(user_id)
        with lock:
            if user_id not in self.user_agent_dict:
                self.user_agent_dict[user_id] = []
            self.user_agent_dict[user_id].append(agent)

    def get_user_agent(self, user_id: str) -> Optional[List[Agent]]:
        """
        특정 사용자(user_id)에 등록된 agent 리스트를 반환합니다.
        등록된 agent가 없다면 None을 반환합니다.
        """
        return self.user_agent_dict.get(user_id)

    def set_user_agent(self, user_id: str, agent_list: List[Agent]) -> None:
        """
        특정 사용자의 전체 agent 리스트를 설정합니다.
        """
        lock = self._get_user_lock(user_id)
        with lock:
            self.user_agent_dict[user_id] = agent_list

    def set_user_task(self, user_id: str, task: List[Task]) -> None:
        """
        특정 사용자(user_id)에 task를 추가합니다.
        """
        lock = self._get_user_lock(user_id)
        with lock:
            # if user_id not in self.user_task_dict:
            #     self.user_task_dict[user_id] = []
            # self.user_task_dict[user_id].append(task)
            self.user_task_dict[user_id] = task

    def get_user_task(self, user_id: str):
        """
       특정 사용자(user_id)에 등록된 task 리스트를 반환합니다.
       등록된 task 없다면 None을 반환합니다.
       """
        return self.user_task_dict.get(user_id)

    def modify_user_task(self, user_id: str, new_tasks: List[Any]) -> None:
        """
        특정 사용자의 task 리스트를 새로운 리스트로 교체합니다.
        """
        lock = self._get_user_lock(user_id)
        with lock:
            self.user_task_dict[user_id] = new_tasks

    async def start_crew_task(self, user_id: str) -> None:
        """
        사용자의 모든 agent에 대해 주기적으로 AI 작업(run)을 실행합니다.
        작업 결과는 콘솔에 출력되며, 필요에 따라 추가 로직을 구현할 수 있습니다.
        """
        agents = self.get_user_agent(user_id)
        tasks = self.get_user_task(user_id)
        if not agents or not tasks:
            print(f"사용자 {user_id}는 등록된 agent가 없습니다.")
            return

    def get_llm(self):
        """
        내부에 저장된 LLM 인스턴스를 반환하는 메서드

        반환:
        - LLM 인스턴스
        """
        return self.llm

    def destroy_agent(self, user_id: str):
        """
        지정 사용자의 에이전트 데이터를 삭제하는 메서드

        매개변수:
        - user_id: 사용자 식별자
        """
        with self._get_user_lock(user_id):
            if user_id in self.user_agent_dict:
                del self.user_agent_dict[user_id]

    def destroy_task(self, user_id: str):
        """
        지정 사용자의 태스크 데이터를 삭제하는 메서드

        매개변수:
        - user_id: 사용자 식별자
        """
        with self._get_user_lock(user_id):
            if user_id in self.user_task_dict:
                del self.user_task_dict[user_id]

# -------------
# 개별 함수들
# -------------
agentUtil = AgentUtil()

async def create_agent(user_id: str, character_list: list)-> bool:
    """
    사용자별 에이전트와 태스크를 생성 및 등록하는 비동기 함수.

    절차:
    1. LLM 인스턴스를 가져옵니다.
    2. 각 캐릭터에 대해 성격 정보를 포함한 에이전트를 생성합니다.
    3. 생성된 에이전트를 agent_list에 저장합니다.
    4. 각 에이전트에 대해 태스크를 생성하고 task_list에 저장합니다.
    5. 생성된 에이전트와 태스크 리스트를 각각 AgentUtil에 등록합니다.

    매개변수:
    - user_id: 사용자 식별자
    - character_list: 캐릭터 정보가 담긴 리스트 (각 캐릭터는 딕셔너리 형태)
    """
    try:
        agent_list = []
        task_list = []
        llm = agentUtil.get_llm()

        for character in character_list:
            # 각 캐릭터의 성격 정보(예: description, species_speech_pattern)를 조회
            personality = await PersonalityUtil.get_personality(character['personality'])
            personality_type = personality['species_speech_pattern']

            # 에이전트 생성: 역할, 목표, 배경 스토리 등을 설정
            agent = Agent(
                role=f"'{character['animaltype']}' 동물의 '{character['nickname']}' 캐릭터.",
                goal="화면에서 돌아다닙니다.",
                # backstory=f"성격 : ({personality['description']}), 대화 방식 : ({personality_type}), 화면에서 돌아다닙니다.",
                backstory="화면에서 돌아다닙니다",
                llm=llm
            )
            agent_list.append(agent)

            # 태스크 생성: 에이전트에게 주어질 작업을 정의
            # task = Task(
            #     description="x, y값을 0 ~ 255 사이의 랜덤한 값으로 이동하도록 좌표를 주세요",
            #     agent=agent,
            #     expected_output=f"{character['character_id']}_좌표 : ",
            # )
            # task_list.append(task)
        manager_agent = agentUtil.get_manager_agent()
        agent_list.append(manager_agent)
        task = Task(
            description="모든 동물에이전트의 x, y좌표를 0 ~ 255 사이의 랜덤한 값으로 이동하도록 좌표만 주세요",
            agent=manager_agent,
            expected_output="모든 캐릭터 좌표 : "
        )

        task_list.append(task)

        # 사용자별 에이전트와 태스크를 AgentUtil에 등록
        agentUtil.set_user_agent(user_id, agent_list)
        agentUtil.set_user_task(user_id, task_list)
        return True
    except Exception as e:
        print(e)
        return False

async def run_crew(user_id:str)-> Dict[str, Any]:
    """
    에이전트 실행 로직을 처리하는 메인 함수.

    주로 비동기 작업이나 스레드에서 호출되어, 등록된 에이전트들의 행동을 관리합니다.

    구체적인 실행 로직은 필요에 맞게 구현해야 합니다.
    """
    # 실행 로직 구현 (예: 이벤트 루프 처리, 스레드 시작 등)
    result_map = {}
    result_message_list = []
    try:
        agent_list = agentUtil.get_user_agent(user_id)
        task_list = agentUtil.get_user_task(user_id)
        start_time = datetime.now()
        for task in task_list:
            crew = Crew(agents=agent_list, tasks=[task], verbose=True, process="sequential")
            result = crew.kickoff()
            crew_result = result.model_dump()
            type(crew_result)
            result_message_list.append(crew_result['raw'])

        # crew = Crew(agents=agent_list,tasks=task_list,verbose=True, process="sequential")
        # start_time = datetime.now()
        # result = crew.kickoff()
        end_time = datetime.now()
        print(end_time - start_time)
        result_map['result'] = True
        result_map['result_message'] = result_message_list
        return result_map
    except Exception as e:
        print(e)
        result_map['result'] = False
        return result_map

async def destroy_agent(user_id: str):
    """
    지정된 사용자의 에이전트와 태스크 데이터를 삭제하는 함수.

    매개변수:
    - user_id: 삭제할 사용자의 식별자
    """
    try:
        print("삭제 시작")
        agentUtil.destroy_agent(user_id)
        agentUtil.destroy_task(user_id)
        print("삭제 완료")
        return True
    except Exception as e:
        print("삭제 실패")
        print(e)
        return False