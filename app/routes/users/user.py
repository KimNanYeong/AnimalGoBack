from fastapi import APIRouter, HTTPException, BackgroundTasks
import httpx
import asyncio
# from services.image_service import fetch_character_info
import services.image_service as imgserv
# from services.image_service import get_saved_images

# app = FastAPI()
router = APIRouter()

COMFYUI_URL = "http://127.0.0.1:8188"

@router.post("/send-charater/{character_id}")
async def send_character(character_id: str, background_tasks: BackgroundTasks):
    """
    캐릭터 ID를 받아 캐릭터 정보를 반환하는 API
    :param character_id: 캐릭터 ID
    :return: 캐릭터 정보 반환
    """
    # try:
        # 캐릭터 정보를 가져오는 함수
    character_info = await imgserv.fetch_character_info(character_id)
    workflow_json = await imgserv.json_update(character_info["animal_type"], character_info["appearance"], character_info["image_path"])
    # workflow_json["character_id"] = character_id
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{COMFYUI_URL}/prompt", json = {"prompt": workflow_json})
        # prompt_id = response.json()
        # print(prompt_id)

    if response.status_code == 200:
        # response_data = response.json()
        prompt_id = response.json().get("prompt_id")
        # if response.json()["prompt_id"]:
        if prompt_id:
            asyncio.create_task(imgserv.get_image(prompt_id, character_id))
            # background_tasks.add_task(asyncio.to_thread, imgserv.get_image, response.json()["prompt_id"], character_id)
            print(response)
        return {"status": "success", "message": "ComfyUI 서버 연결됨"}
    else:
        return {"status": "error", "message": f"ComfyUI 응답 코드: {response.status_code}"}

    # except Exception as e:
    #     raise HTTPException(status_code=404, detail=str(e))

# @router.get("/check-comfyui")
# async def check_comfyui():
#     get_saved_images("user_id", "character_id")
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.get(f"{COMFYUI_URL}/prompt")  # ComfyUI 서버 상태 확인
#             if response.status_code == 200:
#                 return {"status": "success", "message": "ComfyUI 서버 연결됨"}
#             else:
#                 return {"status": "error", "message": f"ComfyUI 응답 코드: {response.status_code}"}
#     except httpx.RequestError:
#         return {"status": "error", "message": "ComfyUI 서버에 연결할 수 없음"}

# @router.get("/get_appearance/{user_id}/{character_id}")
# async def get_appearance(user_id: str, character_id: str):
#     """
#     사용자 외모 정보를 받아와 img_prompt에 포함시킬 데이터를 반환하는 API
#     :param user_id: 사용자 고유 ID
#     :param character_id: 캐릭터 고유 ID
#     :return: 외모 정보와 img_prompt에 필요한 텍스트 설명 반환
#     """
#     # 여기서 외모 데이터는 예시로 하드코딩했지만, 실제 데이터는 DB나 다른 API에서 가져옵니다.
#     appearance_data = {
#         "hair_color": "blonde",
#         "eye_color": "blue",
#         "outfit": "casual clothes",
#         "expression": "smiling",
#         "additional_features": "wearing glasses"
#     }

#     # 외모 데이터를 기반으로 img_prompt 생성
#     img_prompt = f"A character with {appearance_data['hair_color']} hair, {appearance_data['eye_color']} eyes, {appearance_data['outfit']}, {appearance_data['expression']}, and {appearance_data['additional_features']}."

#     return {"img_prompt": img_prompt, "appearance_data": appearance_data}
