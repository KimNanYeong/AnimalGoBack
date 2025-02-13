from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CharacterCreateRequest(BaseModel):
    user_id: str
    charac_id: str
    nickname: str
    animaltype: str
    personality: str

class CharacterResponse(BaseModel):
    user_id: str
    charac_id: str
    nickname: str
    animaltype: str
    personality: str
    create_at: Optional[datetime]  # ✅ Firestore의 Timestamp 변환
