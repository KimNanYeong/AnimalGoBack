import websocket
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import List
from core.firebase import db
from services.VillageService import VillageService
from app.services.affinity import AffinityService
import json
import asyncio

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
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # print("클라이언트로부터 받은 메시지:", data)
            # data_dict = json.loads(data)
            # character_list = data_dict['characters']
            # relationship = await VillageService.get_relationship(character_list)
            # VillageService.create_message(websocket, character_list, relationship)
                # await manager.broadcast(f"Message: {chat_message}")
            # result = await VillageService.create_message(data_dict)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("Client left the chat")

@router.get("/village/get_characters/{user_id}",tags=["village"])
async def get_characters(user_id:str, background_tasks:BackgroundTasks):
    # try:
    character_list = await service.get_character(user_id)
    background_tasks.add_task(crew_ai_task, character_list)
    return {"result" : True,"character_list" : character_list}
    # except e:
    #     print(e.message)
    #     return {"result" : False}

# @router.get("/village/create_agent")
# async def create_agent(websocket: WebSocket):
#     result = await service.crew_ai_task(websocket)
#     return {"result" : True}

async def crew_ai_task(character_list: List):
    while True:
        if not manager.active_connections:
            print("소켓 연결이 끊어져서 crew_ai_task를 종료합니다.")
            break
        # Crew AI 로직 구현 (DB 혹은 메모리 상태 업데이트, 행동 결정 등)
        result = {"action": "update", "data": "Crew AI 결과"}
        print(result)
        await manager.broadcast(json.dumps(result))
        await asyncio.sleep(2)  # 주기적으로 업데이트 (예: 2초 간격)

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