import asyncio
import os
import json
import requests
import urllib.request
import websocket
import io
from PIL import Image
import random
from core.firebase import db
import routes.home.character_api as home_charac

COMFYUI_SERVER_URL = "127.0.0.1:8188"  # ComfyUI 서버 URL
COMFYUI_WORKFLOW_PATH = "app/db/comfyui_workflow.json"  # 워크플로우 JSON 파일 경로
# DEFAULT_OUTPUT_FILENAME = "output/generated_image.png"  # 생성된 이미지 저장 경로

def generate_random_seed():
    """64비트 정수 범위 내 랜덤 seed 생성"""
    return random.randint(0, 2**63 - 1)

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
        "image_path": data.get("original_path")
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
            print(f"Received message: {data}")
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

# async def get_image(prompt_id: str, character_id: str):
#     # ComfyUI 서버에 요청을 보냅니다.
#     ws = websocket.WebSocket()
#     ws.connect(f"ws://{COMFYUI_SERVER_URL}/ws")
    
#     print(f"Waiting for image data for prompt ID: {prompt_id}")
    
#     while True:
#         message = ws.recv()
#         if isinstance(message, str):
#             # text = message.decode('utf-8')
#             data = json.loads(message)
#             print(f"Received message: {data}")
#             if data['type'] == 'executing':
#                 if data['data']['node'] is None and data['data']['prompt_id'] == prompt_id:
#                     print("Execution completed")
#                     break
#             if data['type'] == 'status':
#                 if data['data']['status']['exec_info']['queue_remaining'] == 0:
#                     print("Execution completed")
#                     break
#         elif isinstance(message, bytes):
#             img_io = io.BytesIO(message[8:])
#             img = Image.open(img_io)

#             # 이미지 포맷(예: 'JPEG', 'PNG') 확인 후 소문자로 변환
#             img_format = img.format.lower() if img.format else 'jpeg'

#             # JPEG인 경우 RGB 모드로 변환 (필요한 경우)
#             if img_format == 'jpeg' and img.mode != 'RGB':
#                 img = img.convert('RGB')

#             # 메모리 내 새로운 BytesIO 객체에 이미지 저장
#             output_io = io.BytesIO()
#             img.save(output_io, format=img.format)
#             # 파일 객체처럼 동작하도록 filename 속성 추가 (예: "character.jpeg")
#             setattr(output_io, "filename", f"character.{img_format}")

#             # 버퍼의 포인터를 처음으로 되돌림
#             output_io.seek(0)

#             # 생성된 메모리 내 파일 객체를 업로드
#             await home_charac.upload_character_image(character_id, output_io)
#             # file_obj = io.BytesIO(message)
#             # setattr(file_obj, "filename", "charter.jpg")
#             # print("Received binary data (likely image)")
#             # home_charac.upload_character_image(character_id, file_obj)
    
#     ws.close()
