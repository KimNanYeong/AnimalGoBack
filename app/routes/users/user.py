from fastapi import APIRouter, HTTPException
# from app.db.firestore import get_user, create_user, update_user, delete_user
# from app.schemas.user import UserCreate, UserUpdate

router = APIRouter()

@router.get("/get_appearance/{user_id}/{character_id}")
async def get_appearance(user_id: str, character_id: str):
    """
    사용자 외모 정보를 받아와 img_prompt에 포함시킬 데이터를 반환하는 API
    :param user_id: 사용자 고유 ID
    :param character_id: 캐릭터 고유 ID
    :return: 외모 정보와 img_prompt에 필요한 텍스트 설명 반환
    """
    # 여기서 외모 데이터는 예시로 하드코딩했지만, 실제 데이터는 DB나 다른 API에서 가져옵니다.
    appearance_data = {
        "hair_color": "blonde",
        "eye_color": "blue",
        "outfit": "casual clothes",
        "expression": "smiling",
        "additional_features": "wearing glasses"
    }

    # 외모 데이터를 기반으로 img_prompt 생성
    img_prompt = f"A character with {appearance_data['hair_color']} hair, {appearance_data['eye_color']} eyes, {appearance_data['outfit']}, {appearance_data['expression']}, and {appearance_data['additional_features']}."

    return {"img_prompt": img_prompt, "appearance_data": appearance_data}
