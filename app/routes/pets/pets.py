from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from pydantic import BaseModel

# from app.db.firestore import get_user_pet  # ✅ Firestore에서 반려동물 정보 조회 함수 가져오기
from db import get_user_pet


# ✅ FastAPI 라우터 생성
router = APIRouter()

# ✅ Firestore 클라이언트 연결
db = firestore.client()

# ✅ [1] 요청 데이터 모델 정의 (반려동물 생성 요청 시 사용)
class PetCreateRequest(BaseModel):
    user_id: str  # 사용자 ID
    pet_id: str  # 반려동물 고유 ID
    pet_name: str  # 반려동물 이름
    species: str  # 반려동물 종류 (예: "강아지", "고양이")
    trait_id: str  # 반려동물의 성격 ID (예: "calm", "energetic", "loyal")

# ✅ [2] 반려동물(캐릭터) 생성 API
@router.post("/pets/")
def create_pet(request: PetCreateRequest):
    """
    🔥 새로운 반려동물을 생성하고 Firestore에 저장하는 API 🔥
    
    - 사용자가 입력한 `trait_id`를 Firestore에서 조회하여 성격 정보를 가져옵니다.
    - Firestore `user_pets` 컬렉션에 반려동물 데이터를 저장합니다.
    
    📌 **사용 예시 (프론트엔드 요청)**
    ```http
    POST /pets/
    Content-Type: application/json
    {
        "user_id": "user123",
        "pet_id": "pet001",
        "pet_name": "바둑이",
        "species": "강아지",
        "trait_id": "calm"
    }
    ```
    """
    # ✅ [3] Firestore에서 선택한 성격 정보 가져오기
    trait_ref = db.collection("character_traits").document(request.trait_id)
    trait_doc = trait_ref.get()

    if not trait_doc.exists:
        raise HTTPException(status_code=404, detail="Trait not found")  # ❌ 존재하지 않는 성격 ID라면 404 오류 발생

    trait_data = trait_doc.to_dict()  # Firestore 문서 데이터를 딕셔너리로 변환

    # ✅ [4] Firestore에 반려동물 데이터 저장
    pet_ref = db.collection("user_pets").document(f"{request.user_id}_{request.pet_id}")
    pet_ref.set({
        "user_id": request.user_id,
        "pet_id": request.pet_id,
        "name": request.pet_name,
        "species": request.species,
        "personality": trait_data["name"],  # 성격 이름 (예: "조용한")
        "prompt_template": trait_data["prompt_template"],  # AI 응답을 위한 프롬프트 템플릿
        "created_at": firestore.SERVER_TIMESTAMP  # Firestore 서버 시간 기록
    })

    return {
        "message": "Pet created successfully",
        "pet": {
            "user_id": request.user_id,
            "pet_id": request.pet_id,
            "name": request.pet_name,
            "species": request.species,
            "personality": trait_data["name"],
            "prompt_template": trait_data["prompt_template"]
        }
    }

# ✅ [5] 특정 반려동물 데이터 조회 API
@router.get("/api/pets/{user_id}/{pet_id}")
async def read_user_pet(user_id: str, pet_id: str):
    """
    🔥 특정 사용자의 반려동물 정보를 가져오는 API 🔥
    
    - Firestore에서 `user_pets` 컬렉션을 조회하여 해당 반려동물 데이터를 반환합니다.
    - 반려동물이 존재하지 않으면 404 오류를 반환합니다.
    
    📌 **사용 예시 (프론트엔드 요청)**
    ```http
    GET /api/pets/user123/pet001
    ```
    """
    pet_data = get_user_pet(user_id, pet_id)
    if "error" in pet_data:
        raise HTTPException(status_code=404, detail=pet_data["error"])  # ❌ 반려동물이 없으면 404 반환
    return pet_data
