import os
import json
import requests
from core.firebase import save_to_firestore

COMFYUI_SERVER_URL = "http://<server-ip>:5000"  # ComfyUI 서버 URL
COMFYUI_WORKFLOW_PATH = "../db/comfyui_workflow.json"  # 워크플로우 JSON 파일 경로

async def get_saved_images(user_id: str, character_id: str):
    """
    Firestore에서 저장된 이미지 경로를 가져오는 함수.
    :param user_id: 사용자 ID
    :param character_id: 캐릭터 ID
    :return: 로컬에 저장된 이미지 반환
    """
    uploaded_image_path = os.path.join("C:/AnimalGo/uploads", str(user_id), str(character_id), "original.jpg")
    processed_image_path = os.path.join("C:/AnimalGo/processed_images", str(user_id), str(character_id), "processed.jpg")

    if os.path.exists(uploaded_image_path):
        return {"image_path": uploaded_image_path}
    
    if os.path.exists(processed_image_path):
        return {"image_path": processed_image_path}
    
    raise Exception("No images found")

async def generate_image(user_id: str, character_id: str, img_prompt: str):
    # 워크플로우 JSON 파일 읽기
    with open(COMFYUI_WORKFLOW_PATH, 'r') as file:
        workflow_data = json.load(file)

    # 외모 API에서 받은 img_prompt를 'text' 필드에 삽입
    workflow_data["6"]["inputs"]["text"] = workflow_data["6"]["inputs"]["text"].format(img_prompt=img_prompt)

    # ComfyUI 서버에 워크플로우 요청
    endpoint = f"{COMFYUI_SERVER_URL}/workflow"
    response = requests.post(endpoint, json=workflow_data)

    if response.status_code == 200:
        # 이미지 경로 생성
        image_dir = f"C:/AnimalGo/uploads/{user_id}/{character_id}"
        os.makedirs(image_dir, exist_ok=True)
        original_image_path = os.path.join(image_dir, "original.jpg")
        
        # 이미지 데이터를 파일로 저장
        with open(original_image_path, "wb") as f:
            f.write(response.content)

        # 생성된 이미지 경로 리턴
        return original_image_path, original_image_path
    else:
        return None, None

def save_image_paths(user_id: str, character_id: str, original_path: str, processed_path: str):
    save_to_firestore(user_id, character_id, original_path, processed_path)
