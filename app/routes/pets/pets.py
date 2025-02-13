from fastapi import APIRouter
from services.pets_service import create_pet, get_pet
from schemas.pets import PetCreateRequest, PetResponse  # ✅ 스키마 가져오기

router = APIRouter()

@router.post("/pets/", response_model=PetResponse)  # ✅ 응답 데이터 형식 지정
def create_pet_api(request: PetCreateRequest):
    """🔥 반려동물 생성 API"""
    pet_data = create_pet(
        user_id=request.user_id,
        pet_id=request.pet_id,
        pet_name=request.pet_name,
        species=request.species,
        trait_id=request.trait_id
    )
    
    return pet_data  # ✅ 스키마에 맞게 반환됨

@router.get("/api/pets/{user_id}/{pet_id}", response_model=PetResponse)
def read_user_pet(user_id: str, pet_id: str):
    """🔥 특정 반려동물 정보 조회 API"""
    pet_data = get_pet(user_id, pet_id)
    return pet_data  # ✅ 스키마에 맞게 반환됨
