from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime

db = firestore.client()

def create_character(user_id: str, charac_id: str, nickname: str, animaltype: str, personality: str):
    """🔥 Firestore에 캐릭터 정보를 저장하는 함수"""

    # ✅ Firestore에서 성격 정보 가져오기
    personality_ref = db.collection("personality").document(personality)
    personality_doc = personality_ref.get()

    if personality_doc is None or not personality_doc.exists:
        raise HTTPException(status_code=404, detail=f"Personality data not found for ID: {personality}")

    personality_data = personality_doc.to_dict()

    # ✅ Firestore에 캐릭터 저장할 데이터 구성
    character_data = {
        "charac_id": charac_id,  # ✅ 고유 ID
        "user_id": user_id,
        "nickname": nickname,
        "animaltype": animaltype,
        "personality": personality_data.get("id", personality),  # ✅ personality ID 저장
        "create_at": firestore.SERVER_TIMESTAMP  # ✅ Firestore에서 자동으로 현재 시간 저장
    }

    # ✅ Firestore에 `characters` 컬렉션에 데이터 저장
    db.collection("characters").document(f"{user_id}_{charac_id}").set(character_data)

    # ✅ FastAPI 응답을 반환할 때 `create_at`을 `datetime`으로 변환
    character_data["create_at"] = datetime.utcnow().isoformat()  # ✅ ISO 8601 변환

    return character_data


def get_character(user_id: str, charac_id: str):
    """🔥 Firestore에서 캐릭터 정보 조회"""

    char_ref = db.collection("characters").document(f"{user_id}_{charac_id}")
    char_doc = char_ref.get()

    if not char_doc.exists():
        raise HTTPException(status_code=404, detail="Character not found")

    char_data = char_doc.to_dict()

    # ✅ Firestore Timestamp → Python datetime 변환
    if isinstance(char_data.get("create_at"), firestore.firestore.Timestamp):
        char_data["create_at"] = char_data["create_at"].isoformat()  # ✅ ISO 형식 변환

    return char_data
