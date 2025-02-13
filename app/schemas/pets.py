from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ✅ 반려동물 생성 요청 스키마
class PetCreateRequest(BaseModel):
    user_id: str
    pet_id: str
    pet_name: str
    species: str
    trait_id: str

# ✅ Firestore에서 불러온 반려동물 정보 스키마
class PetResponse(BaseModel):
    user_id: str
    pet_id: str
    name: str
    species: str
    personality: str
    prompt_template: str
    speech_pattern: str
    speech_style: str
    created_at: Optional[datetime]  # Firestore Timestamp를 datetime으로 변환
