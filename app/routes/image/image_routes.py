from fastapi import APIRouter, HTTPException
from services.image_service import get_saved_images, generate_image, save_image_paths, get_appearance

router = APIRouter()

# 이미지를 Firestore에서 가져오는 엔드포인트
@router.get("/get_image/{user_id}/{character_id}")
async def get_image(user_id: str, character_id: str):
    """
    Firestore에서 저장된 이미지를 가져옵니다.
    :param user_id: 사용자 고유 ID
    :param character_id: 캐릭터 고유 ID
    :return: 로컬에 저장된 이미지 반환
    """
    try:
        return await get_saved_images(user_id, character_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 캐릭터 생성 및 ComfyUI로 이미지 생성 후 Firestore에 저장하는 엔드포인트
@router.post("/create_character/{user_id}/{character_id}")
async def create_character(user_id: str, character_id: str, prompt: str, is_first_time: bool = False):
    """
    캐릭터를 생성하고, ComfyUI로 이미지를 생성 후 Firestore에 저장합니다.
    :param user_id: 사용자 고유 ID
    :param character_id: 캐릭터 고유 ID
    :param prompt: 이미지 생성에 사용할 텍스트 프롬프트
    :param is_first_time: 첫 번째 생성인지 여부
    :return: 이미지 생성 성공 메시지
    """
    try:
        # 외모 API에서 img_prompt 받기
        appearance_response = await get_appearance(user_id, character_id)
        img_prompt = appearance_response["img_prompt"]
        
        # 원본 이미지 생성 및 로컬 저장
        original_image_path, processed_image_path = await generate_image(user_id, character_id, img_prompt)

        # Firestore에 이미지 경로 저장
        save_image_paths(user_id, character_id, original_image_path, processed_image_path)
        
        return {"message": "Character created and images saved successfully!", 
                "original_image_path": original_image_path, 
                "processed_image_path": processed_image_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
