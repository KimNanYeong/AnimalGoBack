from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta


db = firestore.client()

def create_pet(user_id: str, pet_id: str, pet_name: str, species: str, trait_id: str):
    """Firestore에 반려동물 데이터를 저장하는 함수"""

    # ✅ Firestore에서 성격 정보 가져오기
    trait_ref = db.collection("character_traits").document(trait_id)
    trait_doc = trait_ref.get()

    if not trait_doc.exists:
        raise HTTPException(status_code=404, detail="Trait not found")

    trait_data = trait_doc.to_dict()

    # ✅ Firestore `SERVER_TIMESTAMP` 사용
    pet_data = {
        "user_id": user_id,
        "pet_id": pet_id,
        "name": pet_name,
        "species": species,
        "personality": trait_data["name"],
        "prompt_template": trait_data["prompt_template"],
        "speech_pattern": trait_data.get("species_speech_pattern", {}).get(species, "{말투}"),
        "speech_style": trait_data.get("speech_style", "기본 말투"),
        "created_at": firestore.SERVER_TIMESTAMP  # ✅ Firestore Timestamp로 저장
    }

    db.collection("user_pets").document(f"{user_id}_{pet_id}").set(pet_data)
    return pet_data

def get_pet(user_id: str, pet_id: str):
    """Firestore에서 반려동물 정보를 조회하는 함수"""
    pet_ref = db.collection("user_pets").document(f"{user_id}_{pet_id}")
    pet_doc = pet_ref.get()

    if not pet_doc.exists:
        raise HTTPException(status_code=404, detail="Pet not found")

    pet_data = pet_doc.to_dict()

    # ✅ Firestore Timestamp를 Python `datetime`으로 변환
    if isinstance(pet_data.get("created_at"), datetime):
        pet_data["created_at"] = pet_data["created_at"].isoformat()  # ISO 8601 형식 변환

    return pet_data
