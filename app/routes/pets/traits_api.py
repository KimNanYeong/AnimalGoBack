from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

router = APIRouter()
db = firestore.client()

@router.get("/traits/{species}/")
def get_traits(species: str):
    """
    🔥 Firestore에서 등록된 성격 프리셋 목록을 가져오는 API 🔥
    - 사용자가 요청한 동물 종(`species`)에 따라 말투가 달라지도록 함.
    - 예: `GET /traits/고양이/` → 고양이 스타일로 응답
    """
    traits_ref = db.collection("personality")  # ✅ `character_traits` → `personality`
    docs = traits_ref.stream()

    traits = []
    for doc in docs:
        trait_data = doc.to_dict()
        
        # ✅ 요청된 종(species)에 따른 말투 선택
        speech_pattern = trait_data.get("species_speech_pattern", {}).get(species, "{말투}")

        traits.append({
            "id": trait_data.get("id"),
            "name": trait_data.get("name"),
            "description": trait_data.get("description"),
            "speech_style": trait_data.get("speech_style"),
            "emoji_style": trait_data.get("emoji_style"),
            "speech_pattern": speech_pattern
        })

    if not traits:
        raise HTTPException(status_code=404, detail="No traits found")

    return {"traits": traits}
