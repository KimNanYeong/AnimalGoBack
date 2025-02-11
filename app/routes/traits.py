from fastapi import APIRouter, HTTPException
from firebase_admin import firestore

# ✅ FastAPI 라우터 생성
router = APIRouter()

# ✅ Firestore 클라이언트 연결
db = firestore.client()

# ✅ [1] 성격 프리셋 목록 조회 API
@router.get("/traits/")
def get_traits():
    """
    🔥 Firestore에서 등록된 성격 프리셋 목록을 가져오는 API 🔥
    
    - Firestore의 `character_traits` 컬렉션에서 모든 성격 데이터를 조회합니다.
    - 각 성격 데이터는 `id`, `name`, `description`을 포함하여 반환됩니다.
    - 등록된 성격 데이터가 없으면 404 에러를 반환합니다.

    📌 **사용 예시 (프론트엔드 요청)**
    ```http
    GET /traits/
    ```
    📌 **예상 응답**
    ```json
    {
        "traits": [
            {
                "id": "calm",
                "name": "조용한",
                "description": "조용하고 신중한 성격입니다."
            },
            {
                "id": "energetic",
                "name": "활발한",
                "description": "활발하고 에너지가 넘치는 성격입니다."
            }
        ]
    }
    ```
    """
    # ✅ Firestore에서 `character_traits` 컬렉션 가져오기
    traits_ref = db.collection("character_traits")
    docs = traits_ref.stream()

    # ✅ 성격 데이터를 리스트로 저장
    traits = []
    for doc in docs:
        trait_data = doc.to_dict()
        traits.append({
            "id": trait_data.get("id"),  # 성격 ID (예: "calm", "loyal")
            "name": trait_data.get("name"),  # 성격 이름 (예: "조용한")
            "description": trait_data.get("description")  # 성격 설명
        })

    # ✅ Firestore에 성격 데이터가 없는 경우 404 에러 반환
    if not traits:
        raise HTTPException(status_code=404, detail="No traits found")

    return {"traits": traits}
