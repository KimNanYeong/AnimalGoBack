import asyncio
import os
import json
import uuid

import httpx
import requests
import urllib.request
import websocket
import io
from PIL import Image
import random
from core.firebase import db
import routes.home.character_api as home_charac
import datetime

COMFYUI_SERVER_URL = "127.0.0.1:8188"  # ComfyUI 서버 URL
COMFYUI_WORKFLOW_PATH = r"app/db/comfyui_workflow.json"  # 워크플로우 JSON 파일 경로
COMFYUI_PROFILE_WORKFLOW_PATH = r"app/db/profile_workflow.json"
print(f"파일 경로 확인: {COMFYUI_WORKFLOW_PATH}")
# DEFAULT_OUTPUT_FILENAME = "output/generated_image.png"  # 생성된 이미지 저장 경로
BASE_STORAGE_FOLDER = "C:/animal-storage"

def generate_random_seed():
    """64비트 정수 범위 내 랜덤 seed 생성"""
    return random.randint(0, 2**63 - 1)

async def schedule_village_image_task(village_prompt_id: str, character_info: dict) -> None:
    """마을 이미지 저장 작업을 비동기로 스케줄링합니다."""
    await asyncio.create_task(save_village_image(village_prompt_id, character_info))

async def fetch_character_info(charac_id: str) -> dict:
    """
    Firestore에서 캐릭터 정보를 조회하여,
    동물타입(animaltype), 외모(appearance), 이미지 경로(original_path)를 반환.
    
    :param charac_id: Firestore 문서 ID
    :return: {"animal_type": str, "appearance": str, "image_path": str}
    """
    # Firestore 컬렉션 'characters'에서 해당 캐릭터 문서를 조회
    doc_ref = db.collection("characters").document(charac_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise ValueError(f"캐릭터 정보를 찾을 수 없습니다. (ID: {charac_id})")
    print(doc.to_dict())

    data = doc.to_dict()
    return {
        "animal_type": data.get("animaltype"),
        "appearance": data.get("appearance"),
        "image_path": data.get("original_path"),
        "user_id" : data.get("user_id"),
        "character_id" : charac_id,
    }

async def json_update(animal_type: str, appearance: str, image_path: str):
    # 워크플로우 JSON 파일 읽기
    with open(COMFYUI_WORKFLOW_PATH, 'r') as file:
        workflow_data = json.load(file)
    
    new_image_path = image_path  # 원하는 이미지 경로로 변경
    if "10" in workflow_data and "inputs" in workflow_data["10"]:
        workflow_data["10"]["inputs"]["image"] = new_image_path
        print(f"[update_workflow_json] Updated node 10 image path -> {image_path}")
    else:
        raise KeyError("JSON 데이터에 10번 노드가 없거나 inputs 필드가 없습니다.")
    
    # new_6 = appearance  # 원하는 이미지 경로로 변경
    print(workflow_data["6"]["inputs"]["text"] + ", " + animal_type + ", " + appearance)
    if "6" in workflow_data and "inputs" in workflow_data["6"]:
        # workflow_data["6"]["inputs"]["text"] = workflow_data["6"]["inputs"]["text"] + ", " + animal_type + ", "  + appearance
        old_text = workflow_data["6"]["inputs"]["text"]
        new_text = f"{old_text}, {animal_type}, {appearance}"
        workflow_data["6"]["inputs"]["text"] = new_text
        print(f"[update_workflow_json] Updated node 6 text -> {new_text}")
    else:
        raise KeyError("JSON 데이터에 6번 노드가 없거나 inputs 필드가 없습니다.")

    # 16번 노드의 seed 값을 업데이트
    new_seed = generate_random_seed()  # 새로운 랜덤 seed 생성
    if "16" in workflow_data and "inputs" in workflow_data["16"]:
        workflow_data["16"]["inputs"]["seed"] = new_seed
        print(f"[update_workflow_json] Updated node 16 seed -> {new_seed}")
    else:
        raise KeyError("JSON 데이터에 16번 노드가 없거나 inputs 필드가 없습니다.")

    return workflow_data

async def get_character(character_id:str):
    doc_ref = db.collection("characters").document(character_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise ValueError(f"캐릭터 정보를 찾을 수 없습니다. (ID: {character_id})")
    data = doc.to_dict()
    return data


# def queue_prompt(prompt: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     ComfyUI 서버에 프롬프트(워크플로우) 데이터를 전송하여 큐잉합니다.
#     """
#     # (서버와 통신하는 코드 필요, 여기에 추가)
#     return {"prompt_id": "dummy_prompt_id"}  # 테스트용 리턴 값

# def get_image(prompt_id: str) -> Image.Image:
#     """
#     WebSocket을 통해 이미지 바이너리를 받아와 Pillow Image 객체로 변환합니다.
#     """
#     # (서버와 통신하는 코드 필요, 여기에 추가)
#     return None  # 테스트용 리턴 값

# def generate_image(workflow_data: Dict[str, Any]) -> str:
#     """
#     ComfyUI 서버에 워크플로우 데이터를 전송하여 이미지를 생성하는 함수
#     """
#     try:
#         # ComfyUI 서버와 통신해 프롬프트 큐잉
#         prompt_id = queue_prompt(COMFYUI_SERVER_URL, workflow_data).get("prompt_id")
#         if not prompt_id:
#             raise RuntimeError("Prompt ID를 가져오지 못했습니다.")

#         # WebSocket을 통해 이미지 수신
#         result_image = get_image(COMFYUI_SERVER_URL, prompt_id)
        
#         if result_image:
#             os.makedirs(os.path.dirname(DEFAULT_OUTPUT_FILENAME), exist_ok=True)
#             result_image.save(DEFAULT_OUTPUT_FILENAME)
#             return DEFAULT_OUTPUT_FILENAME
#         else:
#             return ""
    
#     except Exception as e:
#         print(f"[generate_image] 에러 발생: {e}")
#         return ""

async def get_image(prompt_id: str, character_id: str):
    loop = asyncio.get_running_loop()
    # blocking한 WebSocket 객체 생성 및 연결은 별도 스레드에서 실행
    ws = await loop.run_in_executor(None, websocket.WebSocket)
    await loop.run_in_executor(None, ws.connect, f"ws://{COMFYUI_SERVER_URL}/ws")
    
    print(f"Waiting for image data for prompt ID: {prompt_id}")

    while True:
        # ws.recv()는 blocking 함수이므로 run_in_executor로 호출
        message = await loop.run_in_executor(None, ws.recv)
        
        if isinstance(message, str):
            data = json.loads(message)
            # print(f"Received message: {data}")
            if data['type'] == 'executing':
                if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
                    print("Execution completed")
                    break
            if data['type'] == 'status':
                if data['data']['status']['exec_info']['queue_remaining'] == 0:
                    print("Execution completed")
                    break
        elif isinstance(message, bytes):
            img_io = io.BytesIO(message[8:])
            img = Image.open(img_io)
            
            # 이미지 포맷 확인 및 필요시 변환
            img_format = img.format.lower() if img.format else 'jpeg'
            if img_format == 'jpeg' and img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 새로운 BytesIO 객체에 이미지 저장
            output_io = io.BytesIO()
            img.save(output_io, format=img.format)
            setattr(output_io, "filename", f"character.{img_format}")
            output_io.seek(0)
            
            # 업로드는 비동기 함수이므로 바로 await 호출
            await home_charac.upload_character_image(character_id, output_io)
    
    # WebSocket 종료도 blocking이므로 run_in_executor로 처리
    await loop.run_in_executor(None, ws.close)

async def create_profile(character_info:dict):
    #프로필 워크플로우 읽기
    print(f"character_info: {character_info}")
    print(f"COMFYUI_PROFILE_WORKFLOW_PATH: {COMFYUI_PROFILE_WORKFLOW_PATH}")
    with open (COMFYUI_PROFILE_WORKFLOW_PATH,'r') as file:
        workflow_data = json.load(file)

    prompt = f"""
    highly detailed,
    chibi character, 
    SD style, 
    small body, 
    big head, 
    exaggerated expressions, 
    {character_info["animal_type"]},
    {character_info["appearance"]}, 
    front-facing view, 
    looking directly at viewe,
    head centered
    """

    #프롬프트 변경
    if "6" in workflow_data and "inputs" in workflow_data["6"]:
        workflow_data["6"]["inputs"]["text"] = prompt
    else:
        raise KeyError("JSON 데이터에 6번 노드가 없거나 inputs 필드가 없습니다.")

    #이미지 경로 변경
    if "2" in workflow_data and "inputs" in workflow_data["2"]:
        workflow_data["2"]["inputs"]["text"] = character_info["image_path"]
    else:
        raise KeyError("JSON 데이터에 2번 노드가 없가나 inputs 필드가 없습니다.")

    return workflow_data

async def get_profile(prompt_id:str, character_info:dict):
    loop = asyncio.get_running_loop()
    ws = await loop.run_in_executor(None, websocket.WebSocket)
    await loop.run_in_executor(None, ws.connect, f"ws://{COMFYUI_SERVER_URL}/ws")

    print(f"Waiting for image data for prompt ID: {prompt_id}")
    try :
        while True:
            message = await loop.run_in_executor(None, ws.recv)

            if isinstance(message, str):
                data = json.loads(message)
                # print(f"Received message 11111: {data}")
                if data['type'] == 'executing':
                    if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
                        print("Execution completed")
                        break
                    if data['type'] == "status":
                        if data['data']['status']['exec_info']['queue_remaining'] == 0:
                            print("Execution completed")
                            break
            elif isinstance(message, bytes):
                img_io = io.BytesIO(message[8:])
                img = Image.open(img_io)

                img_format = img.format.lower() if img.format else 'jpeg'
                if img_format == 'jpeg' and img.mode != 'RGB':
                    img = img.convert('RGB')

                output_io = io.BytesIO()
                img.save(output_io, format=img.format)
                setattr(output_io, "filename", f"character.{img_format}")
                output_io.seek(0)

                #사용자별 저장 폴더 경로 생성
                user_id = character_info["user_id"]
                user_folder = os.path.join(BASE_STORAGE_FOLDER,user_id,"characters")
                os.makedirs(user_folder,exist_ok=True)

                #고유 파일명 생성
                file_extension = output_io.filename.split(".")[-1]
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                character_path = os.path.join(user_folder,unique_filename)
                character_abs_path = os.path.abspath(character_path)
                #파일 저장
                with open(character_path, "wb") as buffer:
                    buffer.write(output_io.read())

                await loop.run_in_executor(None, ws.close)

                # 빌리지 이미지 생성
                character_info["character_path"] = character_path
                workflow = await json_update(character_info["animal_type"],character_info["appearance"],character_abs_path)

                async with httpx.AsyncClient() as client:
                    response = await client.post(f"http://{COMFYUI_SERVER_URL}/prompt",json={"prompt":workflow})

                if response.status_code == 200:
                    new_prompt_id = response.json().get("prompt_id")

                    if prompt_id:
                        await loop.run_in_executor(None, ws.close)
                        asyncio.create_task(schedule_village_image_task(new_prompt_id,character_info))
                break
    except Exception as e:
        print(e)
    finally:
        try:
            await loop.run_in_executor(None, ws.close)
        except Exception as e1:
            print("ws.close()호출 중 예외 발생")

async def save_village_image(prompt_id:str, character_info:dict):
    loop = asyncio.get_running_loop()
    ws = await loop.run_in_executor(None, websocket.WebSocket)
    await loop.run_in_executor(None, ws.connect, f"ws://{COMFYUI_SERVER_URL}/ws")
    try:
        while True:
            message = await loop.run_in_executor(None, ws.recv)

            if isinstance(message, str):
                data = json.loads(message)
                # print(f"Received message 22222: {data}")
                if data['type'] == 'executing':
                    if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
                        print("Execution completed")
                        break
                    if data['type'] == "status":
                        if data['data']['status']['exec_info']['queue_remaining'] == 0:
                            print("Execution completed")
                            break
            elif isinstance(message, bytes):
                img_io = io.BytesIO(message[8:])
                img = Image.open(img_io)

                img_format = img.format.lower() if img.format else 'jpeg'
                if img_format == 'jpeg' and img.mode != 'RGB':
                    img = img.convert('RGB')
                output_io = io.BytesIO()
                img.save(output_io, format=img.format)
                setattr(output_io, "filename", f"character.{img_format}")
                output_io.seek(0)

                #사용자별 저장 폴더 경로 생성
                user_id = character_info["user_id"]
                user_folder = os.path.join(BASE_STORAGE_FOLDER,user_id,"characters")
                os.makedirs(user_folder,exist_ok=True)

                #고유 파일명 생성
                file_extension = output_io.filename.split(".")[-1]
                unique_filename = f"village_{uuid.uuid4()}.{file_extension}"
                village_path = os.path.join(user_folder,unique_filename)

                #파일 저장
                with open(village_path, "wb") as buffer:
                    buffer.write(output_io.read())

                character_ref = db.collection("characters").document(character_info["character_id"])

                character_ref.update({
                    "character_path":character_info["character_path"],
                    "village_path":village_path,
                    "status" : "completed",
                    "character_update_at" : datetime.datetime.now()
                })

                await loop.run_in_executor(None, ws.close)
    except Exception as e:
        print(e)
    finally:
        try:
            await loop.run_in_executor(None, ws.close)
        except Exception as e1:
            print("ws.close()호출 중 예외 발생")