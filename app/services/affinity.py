from core.firebase import db
from google.cloud import firestore
from typing import Optional

class AffinityService:
    def __init__(self):
        self.collection = db.collection("affinity")

    async def get_affinity(self, character_id: str) -> Optional[dict]:
        """
        특정 캐릭터의 친밀도 정보를 가져옴
        """
        affinity_ref = self.collection.document(character_id)
        doc = affinity_ref.get()

        if doc.exists:
            return {"result": True, "affinity": doc.to_dict()}
        else:
            return {"result": False, "message": f"Character {character_id} not found"}

    async def update_affinity(self, character_id: str, change: int):
        """
        캐릭터의 친밀도를 업데이트 (증가 또는 감소)
        """
        affinity_ref = self.collection.document(character_id)
        doc = affinity_ref.get()

        if doc.exists:
            affinity_data = doc.to_dict()
            new_points = int(affinity_data["points"]) + change  # 🔹 문자열을 정수로 변환
            new_level = int(affinity_data["level"])  # 🔹 level도 int로 변환

            # 레벨업 조건 (예: 100포인트마다 레벨업)
            if new_points >= 100:
                new_level += 1
                new_points = 0  # 포인트 초기화

            affinity_ref.update({
                "points": new_points,
                "level": new_level,
                "last_interaction": firestore.SERVER_TIMESTAMP
            })
            return {"result": True, "message": f"Affinity updated for {character_id}, New Points: {new_points}"}
        else:
            return {"result": False, "message": f"Character {character_id} not found"}
