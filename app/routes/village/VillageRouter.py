import websocket
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import List
from core.firebase import db
from services.VillageService import VillageService
from app.services.affinity import AffinityService
import json
import asyncio
import util.AgentUtil as AgentUtil

router = APIRouter()
service = VillageService()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket,user_id:str):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # print("클라이언트로부터 받은 메시지:", data)
            # data_dict = json.loads(data)
            # character_list = data_dict['characters']
            # relationship = await VillageService.get_relationship(character_list)
            # VillageService.create_message(websocket, character_list, relationship)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await AgentUtil.destroy_agent(user_id)
        await manager.broadcast("Client left the chat")

@router.get("/village/get_characters/{user_id}",tags=["village"])
async def get_characters(user_id:str, background_tasks:BackgroundTasks):

    try:
        character_list = await service.get_character(user_id)
        # background_tasks.add_task(crew_ai_task, character_list,user_id)
        return {"result" : True,"character_list" : character_list}
    except e:
        print(e.message)
        return {"result" : False}

# async def crew_ai_task(character_list: List,user_id:str):
    # result = await AgentUtil.create_agent(user_id,character_list)
    # if result:
    #     while True:
    #         try:
    #             print("@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    #             print("좌표 재설정")
    #             if not manager.active_connections:
    #                 print("소켓 연결이 끊어져서 crew_ai_task를 종료합니다.")
    #                 await AgentUtil.destroy_agent(user_id)
    #                 break
    #             result_map =  await AgentUtil.run_crew(user_id)
    #             if not result_map.get('result'):
    #                 raise ValueError("result_map이 False입니다. result_map: {}".format(result_map))
    #
    #             # await manager.broadcast(json.dumps(message))
    #             json_message = json.dumps(result_map['result_message'])
    #             await manager.broadcast(json_message)
    #             print("@@@@@@@@@@@@@@@@")
    #             await asyncio.sleep(10)
    #         except Exception as e:
    #             print(e)
    #             await asyncio.sleep(10)


affinity_service = AffinityService()

AFFINITY_CHANGE = {
    "feeding": 5,    # 선물 주면 친밀도 +10
    "ignore": -5   # 싸우면 친밀도 -15
}

@router.post("/village/action/{character_id}/{action}", tags=["village"])
async def village_action(character_id: str, action: str):
    """
    빌리지에서 특정 행동을 하면 친밀도를 업데이트
    """
    if action not in AFFINITY_CHANGE:
        return {"result": False, "message": "Invalid action"}

    change = AFFINITY_CHANGE[action]
    return await affinity_service.update_affinity(character_id, change)

@router.get("/village/get_affinity/{character_id}", tags=["village"])
async def get_affinity(character_id: str):
    """
    특정 캐릭터의 친밀도 조회
    """
    return await affinity_service.get_affinity(character_id)