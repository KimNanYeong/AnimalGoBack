from fastapi import APIRouter, HTTPException, Query
import os
from fastapi.responses import FileResponse
from services.image_service import get_character

router = APIRouter()

# 이미지를 보여주는 엔드포인트
@router.get("/show_image", tags=["image"], summary="이미지 불러오기", description="서버에 저장된 이미지를 불러옵니다")
async def show_image(
    character_id: str = Query(...,description="캐릭터 고유 아이디")
    ,type:str = Query("character",description="이미지 타입(original=원본, character=캐릭터)\n기본은 character")
    ):
    try:
        character_info = await get_character(character_id)
        file_path = ""
        # file_path = "/Users/parkgunhee/Downloads/bbbb.jpg"
        if type == "original":
            file_path = character_info['original_path']
        else:
            file_path = character_info['character_path']
        if os.path.exists(file_path):
            return FileResponse(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))