import os
import json
import requests
import urllib.request
import websocket
from db.firestore import save_to_firestore
from core.firebase import db

COMFYUI_SERVER_URL = "http://127.0.0.1:8188"  # ComfyUI 서버 URL
COMFYUI_WORKFLOW_PATH = "app/db/comfyui_workflow.json"  # 워크플로우 JSON 파일 경로
# DEFAULT_OUTPUT_FILENAME = "output/generated_image.png"  # 생성된 이미지 저장 경로


async def fetch_character_info(charac_id: str) -> dict:
    """
    Firestore에서 캐릭터 정보를 조회하여,
    동물타입(animal_type), 외모(appearance), 이미지 경로(original_path)를 반환.
    
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
