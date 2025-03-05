import websocket
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import List
from core.firebase import db
from services.VillageService import VillageService
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
            # service.create_message(websocket, character_list, relationship)
                # await manager.broadcast(f"Message: {chat_message}")
            # result = await VillageService.create_message(data_dict)
            
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

