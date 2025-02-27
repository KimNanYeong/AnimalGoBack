from fastapi import APIRouter, Form, HTTPException
from firebase_admin import firestore
from services.ai_chats import auto_chat, check_character_exists  # 변경된 함수 이름 사용
from pydantic import BaseModel

router = APIRouter()
db = firestore.client()

# ========================
# 🔹 캐릭터 간 AI 대화 API 
# ========================
@router.post("/ai_characters_chats",
    summary="AI 캐릭터 간 대화 생성",
    tags=["Basic"],
    description="""
    Gemini 2.0 API를 사용하여 두 캐릭터 간 자동 대화를 4회 반복합니다.
    캐릭터는 Firestore `characters` 컬렉션의 문서 ID를 기반으로 선택해야 합니다.
    자동 생성된 chat_id는 `{charac_1}_{charac_2}` 형식입니다.
    """
)
async def start_ai_conversation(
    charac_1: str = Form(..., description="첫 번째 캐릭터 ID (Firestore의 document ID)"),
    charac_2: str = Form(..., description="두 번째 캐릭터 ID (Firestore의 document ID)")
):
    """
    두 캐릭터 간 자동 대화를 4회 반복 실행합니다.
    """
    chat_id = f"{charac_1}_{charac_2}"  # chat_id 자동 생성

    # Firestore에서 캐릭터 존재 여부 확인
    if not check_character_exists(charac_1) or not check_character_exists(charac_2):
        raise HTTPException(status_code=404, detail="캐릭터 ID가 Firestore에 존재하지 않습니다.")

    # Gemini 2.0 API 기반 자동 대화 실행 (Crew AI 없이 프롬프트를 통한 대화)
    result = auto_chat(charac_1, charac_2)
    return result
