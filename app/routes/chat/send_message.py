from fastapi import APIRouter, HTTPException, Query
from services.chat_service import generate_ai_response, save_message

router = APIRouter()

@router.post("/send_message")
async def chat_with_ai(
    user_input: str = Query(..., description="User input"),
    user_id: str = Query(..., description="User ID"),
    pet_id: str = Query(..., description="Pet ID")
):
    # 입력값 검증
    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Empty message not allowed")

    chat_id = f"{user_id}_{pet_id}"

    # ✅ 사용자 메시지 저장 (먼저 저장)
    save_message(chat_id, "user", user_input)

    # AI 응답 생성
    ai_response, error = generate_ai_response(user_id, pet_id, user_input)
    if error:
        raise HTTPException(status_code=500, detail=error)

    return {"response": ai_response}