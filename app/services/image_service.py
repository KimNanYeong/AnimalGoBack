import os
import json
import requests
import urllib.request
import websocket
import io
from PIL import Image
from db.firestore import save_to_firestore
from core.firebase import db
import routes.home.character_api as home_charac

COMFYUI_SERVER_URL = "127.0.0.1:8188"  # ComfyUI 서버 URL
COMFYUI_WORKFLOW_PATH = "app/db/comfyui_workflow.json"  # 워크플로우 JSON 파일 경로
# DEFAULT_OUTPUT_FILENAME = "output/generated_image.png"  # 생성된 이미지 저장 경로


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

    return workflow_data

async def get_image(prompt_id: str, character_id: str):
    # ComfyUI 서버에 요청을 보냅니다.
    ws = websocket.WebSocket()
    ws.connect(f"ws://{COMFYUI_SERVER_URL}/ws")
    
    print(f"Waiting for image data for prompt ID: {prompt_id}")
    
    while True:
        message = ws.recv()
        if isinstance(message, str):
            # text = message.decode('utf-8')
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

            # 이미지 포맷(예: 'JPEG', 'PNG') 확인 후 소문자로 변환
            img_format = img.format.lower() if img.format else 'jpeg'

            # JPEG인 경우 RGB 모드로 변환 (필요한 경우)
            if img_format == 'jpeg' and img.mode != 'RGB':
                img = img.convert('RGB')

            # 메모리 내 새로운 BytesIO 객체에 이미지 저장
            output_io = io.BytesIO()
            img.save(output_io, format=img.format)
            # 파일 객체처럼 동작하도록 filename 속성 추가 (예: "character.jpeg")
            setattr(output_io, "filename", f"character.{img_format}")

            # 버퍼의 포인터를 처음으로 되돌림
            output_io.seek(0)

            # 생성된 메모리 내 파일 객체를 업로드
            await home_charac.upload_character_image(character_id, output_io)
            # file_obj = io.BytesIO(message)
            # setattr(file_obj, "filename", "charter.jpg")
            # print("Received binary data (likely image)")
            # home_charac.upload_character_image(character_id, file_obj)
    
    ws.close()
