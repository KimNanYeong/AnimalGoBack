from fastapi import APIRouter
from services.characters_service import create_character
from schemas.characters import CharacterCreateRequest, CharacterResponse  # ✅ 스키마 가져오기

router = APIRouter()

@router.post("/characters/", response_model=CharacterResponse)
def create_character_api(request: CharacterCreateRequest):
    """🔥 캐릭터 생성 API"""
    character_data = create_character(
        user_id=request.user_id,
        charac_id=request.charac_id,
        nickname=request.nickname,
        animaltype=request.animaltype,
        personality=request.personality
    )
    
    return character_data
