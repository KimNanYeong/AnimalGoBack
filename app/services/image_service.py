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

# async def schedule_village_image_task(village_prompt_id: str, character_info: dict) -> None:
#     """마을 이미지 저장 작업을 비동기로 스케줄링합니다."""
#     await asyncio.create_task(save_village_image(village_prompt_id, character_info))

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
    with open (COMFYUI_PROFILE_WORKFLOW_PATH,'r',encoding="utf-8") as file:
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
        workflow_data["2"]["inputs"]["image"] = character_info["image_path"]
    else:
        raise KeyError("JSON 데이터에 2번 노드가 없가나 inputs 필드가 없습니다.")

    return workflow_data

# async def get_profile(prompt_id: str, character_info: dict):
#     # 현재 이벤트 루프를 가져옴
#     loop = asyncio.get_running_loop()
#     # 별도의 스레드에서 동기 WebSocket 객체를 생성
#     ws = await loop.run_in_executor(None, websocket.WebSocket)
#     # 별도의 스레드에서 WebSocket 서버에 연결
#     await loop.run_in_executor(None, ws.connect, f"ws://{COMFYUI_SERVER_URL}/ws")
#     print(f"Waiting for image data for prompt ID: {prompt_id}")
#
#     try:
#         # WebSocket 메시지를 수신하기 위한 무한 루프
#         while True:
#             # 별도의 스레드에서 동기 ws.recv() 함수를 호출하여 메시지를 수신
#             message = await loop.run_in_executor(None, ws.recv)
#             if isinstance(message, str):
#                 # 문자열 메시지인 경우 JSON 파싱 후 데이터 추출
#                 data = json.loads(message)
#                 print(f"Received message: {data}")
#                 # 메시지 타입이 'executing'일 때 작업 완료 조건 확인
#                 if data['type'] == 'executing':
#                     if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
#                         print("Execution completed")
#                         break
#                     # 참고: 'status' 타입 조건은 실제로 'executing' 타입 하위 조건과 중복될 수 있음
#                     if data['type'] == "status":
#                         if data['data']['status']['exec_info']['queue_remaining'] == 0:
#                             print("Execution completed")
#                             break
#             elif isinstance(message, bytes):
#                 # 바이트 메시지인 경우, 이미지 데이터 처리
#                 img_io = io.BytesIO(message[8:])  # 앞 8바이트는 메타 데이터라고 가정하고 제외
#                 img = Image.open(img_io)  # 이미지 열기
#                 # 이미지 포맷 및 색상 모드 확인 (JPEG인 경우 RGB로 변환 필요)
#                 img_format = img.format.lower() if img.format else 'jpeg'
#                 if img_format == 'jpeg' and img.mode != 'RGB':
#                     img = img.convert('RGB')
#                 output_io = io.BytesIO()  # 이미지 데이터를 저장할 BytesIO 객체 생성
#                 img.save(output_io, format=img.format)  # 이미지 저장
#                 # BytesIO 객체에 파일 이름 속성 설정 (비표준 방식)
#                 setattr(output_io, "filename", f"character.{img_format}")
#                 output_io.seek(0)  # 파일 포인터를 처음으로 되돌림
#
#                 # 사용자별 저장 폴더 경로 구성
#                 user_id = character_info["user_id"]
#                 user_folder = os.path.join(BASE_STORAGE_FOLDER, user_id, "characters")
#                 os.makedirs(user_folder, exist_ok=True)  # 폴더가 없으면 생성
#
#                 # 고유 파일명 생성
#                 file_extension = output_io.filename.split(".")[-1]
#                 unique_filename = f"{uuid.uuid4()}.{file_extension}"
#                 character_path = os.path.join(user_folder, unique_filename)
#                 character_abs_path = os.path.abspath(character_path)  # 절대 경로 구하기
#
#                 # 파일에 이미지 데이터 저장
#                 with open(character_path, "wb") as buffer:
#                     buffer.write(output_io.read())
#                 # 별도의 스레드에서 WebSocket 연결 종료
#                 await loop.run_in_executor(None, ws.close)
#
#                 # 캐릭터 정보에 생성된 캐릭터 이미지 경로 업데이트
#                 character_info["character_path"] = character_path
#                 # 워크플로우 JSON 데이터를 업데이트하기 위한 비동기 호출
#                 workflow = await json_update(character_info["animal_type"],
#                                              character_info["appearance"],
#                                              character_abs_path)
#                 # httpx.AsyncClient를 사용하여 ComfyUI 서버에 POST 요청 전송
#                 async with httpx.AsyncClient() as client:
#                     response = await client.post(f"http://{COMFYUI_SERVER_URL}/prompt",
#                                                  json={"prompt": workflow})
#                 if response.status_code == 200:
#                     # 새로운 프롬프트 ID 추출
#                     new_prompt_id = response.json().get("prompt_id")
#                     # (주석 처리된 스케줄링 함수 호출; 필요 시 사용)
#                     # if prompt_id:
#                     #     asyncio.create_task(schedule_village_image_task(new_prompt_id, character_info))
#
#                     # 빌리지 이미지 수신 처리를 위한 내부 반복문
#                     while True:
#                         if isinstance(message, str):
#                             data = json.loads(message)
#                             print(f"Received message: {data}")
#                             # 빌리지 이미지 생성 후 작업 완료 조건 확인
#                             if data['type'] == 'executing':
#                                 if data['data']['node'] is None and data['data']['prompt_id'] == new_prompt_id:
#                                     print("Execution completed")
#                                     break
#                                 if data['type'] == "status":
#                                     if data['data']['status']['exec_info']['queue_remaining'] == 0:
#                                         print("Execution completed")
#                                         break
#                         elif isinstance(message, bytes):
#                             # 빌리지 이미지 데이터 처리
#                             img_io = io.BytesIO(message[8:])
#                             img = Image.open(img_io)
#                             img_format = img.format.lower() if img.format else 'jpeg'
#                             if img_format == 'jpeg' and img.mode != 'RGB':
#                                 img = img.convert('RGB')
#                             output_io = io.BytesIO()
#                             img.save(output_io, format=img.format)
#                             setattr(output_io, "filename", f"character.{img_format}")
#                             output_io.seek(0)
#                             # 사용자별 저장 폴더 재구성
#                             user_id = character_info["user_id"]
#                             user_folder = os.path.join(BASE_STORAGE_FOLDER, user_id, "characters")
#                             os.makedirs(user_folder, exist_ok=True)
#                             # 빌리지 이미지용 고유 파일명 생성
#                             file_extension = output_io.filename.split(".")[-1]
#                             unique_filename = f"village_{uuid.uuid4()}.{file_extension}"
#                             village_path = os.path.join(user_folder, unique_filename)
#                             # 빌리지 이미지 데이터를 파일로 저장
#                             with open(village_path, "wb") as buffer:
#                                 buffer.write(output_io.read())
#                             # 데이터베이스에서 캐릭터 문서를 찾아 업데이트
#                             character_ref = db.collection("characters").document(character_info["character_id"])
#                             character_ref.update({
#                                 "character_path": character_info["character_path"],
#                                 "village_path": village_path,
#                                 "status": "completed",
#                                 "character_update_at": datetime.datetime.now()
#                             })
#                     break  # 외부 while 루프 종료
#     except Exception as e:
#         # 예외 발생 시 에러 메시지 출력
#         print(e)
#     finally:
#         try:
#             # 작업 완료 후 WebSocket을 종료
#             await loop.run_in_executor(None, ws.close)
#         except Exception as e1:
#             print("ws.close()호출 중 예외 발생")

async def get_profile(prompt_id: str, character_info: dict):
    loop = asyncio.get_running_loop()
    ws = await loop.run_in_executor(None, websocket.WebSocket)
    await loop.run_in_executor(None, ws.connect, f"ws://{COMFYUI_SERVER_URL}/ws")

    # 메시지 처리를 위한 비동기 큐 생성
    message_queue = asyncio.Queue()

    async def websocket_receiver():
        try:
            while True:
                message = await loop.run_in_executor(None, ws.recv)
                await message_queue.put(message)
        except Exception as e:
            print(f"WebSocket 수신 중 오류: {e}")
            await message_queue.put(None)  # 종료 신호

    # 이미지 처리 및 저장 함수 (중복 코드 제거)
    async def process_image(message_bytes, prefix='character'):
        img_io = io.BytesIO(message_bytes[8:])
        img = Image.open(img_io)
        img_format = img.format.lower() if img.format else 'jpeg'

        if img_format == 'jpeg' and img.mode != 'RGB':
            img = img.convert('RGB')

        output_io = io.BytesIO()
        img.save(output_io, format=img.format)
        setattr(output_io, "filename", f"{prefix}.{img_format}")
        output_io.seek(0)

        user_id = character_info["user_id"]
        user_folder = os.path.join(BASE_STORAGE_FOLDER, user_id, "characters")
        os.makedirs(user_folder, exist_ok=True)

        file_extension = output_io.filename.split(".")[-1]
        unique_filename = f"{prefix}_{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(user_folder, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(output_io.read())

        return file_path

    # WebSocket 수신 태스크 시작
    receiver_task = asyncio.create_task(websocket_receiver())

    try:
        # 캐릭터 이미지 처리
        character_path = None
        village_path = None

        while True:
            try:
                # 타임아웃을 설정하여 무한 대기 방지
                message = await asyncio.wait_for(message_queue.get(), timeout=300)

                if message is None:  # 수신 태스크 종료
                    break

                if isinstance(message, str):
                    data = json.loads(message)
                    print(f"Received message: {data}")

                    # 작업 완료 조건
                    if data['type'] == 'executing' and data['data']['node'] is None:
                        if data['data']['prompt_id'] == prompt_id and not character_path:
                            print("캐릭터 이미지 작업 완료")
                        elif data['data']['prompt_id'] == new_prompt_id and character_path and not village_path:
                            print("빌리지 이미지 작업 완료")
                            break

                elif isinstance(message, bytes):
                    if not character_path:
                        character_path = await process_image(message)
                        character_info["character_path"] = character_path

                        # 워크플로우 업데이트 및 새 프롬프트 생성
                        workflow = await json_update(
                            character_info["animal_type"],
                            character_info["appearance"],
                            os.path.abspath(character_path)
                        )

                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"http://{COMFYUI_SERVER_URL}/prompt",
                                json={"prompt": workflow}
                            )

                        if response.status_code == 200:
                            new_prompt_id = response.json().get("prompt_id")

                    elif character_path and not village_path:
                        village_path = await process_image(message, prefix='village')

                        # 데이터베이스 업데이트
                        character_ref = db.collection("characters").document(character_info["character_id"])
                        character_ref.update({
                            "character_path": character_path,
                            "village_path": village_path,
                            "status": "completed",
                            "character_update_at": datetime.datetime.now()
                        })
                        await loop.run_in_executor(None, ws.close)
            except asyncio.TimeoutError:
                print("작업 시간 초과")
                break

    except Exception as e:
        print(f"프로세스 중 오류 발생: {e}")

    finally:
        # 리소스 정리
        receiver_task.cancel()
        try:
            await loop.run_in_executor(None, ws.close)
        except Exception as e:
            print(f"WebSocket 종료 중 오류: {e}")
