import os
from firebase_admin import firestore
from services.chat_service import get_personality_data  # 필요한 함수들만 임포트
import google.generativeai as genai

# 🔥 Gemini 2.0 API 키 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

genai.configure(api_key=GEMINI_API_KEY)
db = firestore.client()
GEMINI_MODEL = "gemini-2.0-flash-thinking-exp-01-21"

model = genai.GenerativeModel(GEMINI_MODEL)

def generate_gemini_response(prompt):
    """Gemini 2.0 API를 호출하여 AI 응답 생성"""
    # print ("111", GEMINI_API_KEY)   
    # print ("11111", GEMINI_MODEL)   
    # print ("1111111", model)   
    response = model.generate_content(prompt)
    # print ("222", GEMINI_API_KEY )    
    return response.text.strip()

def check_character_exists(character_id):
    """Firestore에서 특정 캐릭터가 존재하는지 확인"""
    character_ref = db.collection("characters").document(character_id).get()
    return character_ref.exists  # 올바른 exists 구문 적용

def auto_chat(charac_1, charac_2):
    """
    Gemini 2.0 API를 활용하여 두 캐릭터 간 자동 대화를 4회 반복합니다.
    Crew AI 관련 코드는 제거하였으며, 프롬프트에 성격 및 말투 데이터를 포함합니다.
    """
    # 🔥 캐릭터 존재 여부 확인
    if not check_character_exists(charac_1) or not check_character_exists(charac_2):
        return {"error": "캐릭터 ID가 Firestore에 존재하지 않습니다."}

    chat_id = f"{charac_1}_{charac_2}"  # 자동 생성된 chat_id
    # 🔥 캐릭터 정보 불러오기
    character_a = db.collection("characters").document(charac_1).get().to_dict()
    character_b = db.collection("characters").document(charac_2).get().to_dict()

    # 캐릭터 A 관련 데이터
    ca_personality_id = character_a["personality"]
    ca_animaltype = character_a["animaltype"]
    ca_nickname = character_a["nickname"]
    ca_personality_data = get_personality_data(ca_personality_id)
    ca_speech_style = ca_personality_data.get("speech_style", "기본 말투")
    ca_species_speech_pattern = ca_personality_data.get("species_speech_pattern", {}).get(ca_animaltype, "")
    ca_emoji_style = ca_personality_data.get("emoji_style", "")

    # 캐릭터 B 관련 데이터
    cb_personality_id = character_b["personality"]
    cb_animaltype = character_b["animaltype"]
    cb_nickname = character_b["nickname"]
    cb_personality_data = get_personality_data(cb_personality_id)
    cb_speech_style = cb_personality_data.get("speech_style", "기본 말투")
    cb_species_speech_pattern = cb_personality_data.get("species_speech_pattern", {}).get(cb_animaltype, "")
    cb_emoji_style = cb_personality_data.get("emoji_style", "")

    # 프롬프트 구성 (각 캐릭터의 관점으로 서로에게 대화하도록 구성)

    print ("charac_a: ", ca_animaltype, " ::: ", ca_nickname)
    print ("charac_b: ", cb_animaltype, " ::: ", cb_nickname)

    ca_prompt = f"""
    📌 **역할**
    - 나는 캐릭터(동물) {ca_animaltype} "{ca_nickname}"입니다.
    - 나의 성격은 "{ca_personality_id}"이며, "{ca_speech_style}" 스타일로 대화합니다.

    📌 **대화 스타일**
    - {ca_animaltype}의 입장에서 감정을 담아 자연스럽게 대화하세요.
    - "{ca_species_speech_pattern}" 같은 말투를 활용하세요.
    - 문장은 간결하고 직관적으로 유지하세요.
    - 과한 감탄사나 반복적인 말투는 피하세요.
    - 조급한 말투 대신 여유로운 느낌을 유지하세요.

    📌 **이모지 사용**
    - "{ca_emoji_style}" 이모지를 자연스럽게 사용하세요. (최대 1~2개)

    📌 **상대방과의 대화**
    - 나는 "{ca_nickname}"이라고 부릅니다.
    - 자연스러운 대화체로 답변하세요.
    """

    cb_prompt = f"""
    📌 **역할**
    - 나는 캐릭터(동물) {cb_animaltype} "{cb_nickname}"입니다.
    - 나의 성격은 "{ca_personality_id}"이며, "{cb_speech_style}" 스타일로 대화합니다.

    📌 **대화 스타일**
    - {cb_animaltype}의 입장에서 감정을 담아 자연스럽게 대화하세요.
    - "{cb_species_speech_pattern}" 같은 말투를 활용하세요.
    - 문장은 간결하고 직관적으로 유지하세요.
    - 과한 감탄사나 반복적인 말투는 피하세요.
    - 조급한 말투 대신 여유로운 느낌을 유지하세요.

    📌 **이모지 사용**
    - "{cb_emoji_style}" 이모지를 자연스럽게 사용하세요. (최대 1~2개)

    📌 **상대방과의 대화**
    - 나는 "{cb_nickname}"이라고 부릅니다.
    - 자연스러운 대화체로 답변하세요.

    📌 **대화 주제**
    - "식생활, 운동, 위험한 장소에 대해 랜덤하게 선택하여 대화합니다.(최대 1~2개)

    """

    conversation_log = []
    current_speaker = charac_1
    next_speaker = charac_2

    # 4회 반복하여 대화 진행
    for i in range(6):
        # 현재 화자에 따라 적절한 프롬프트 사용
        if current_speaker == charac_1:
            prompt = f"{current_speaker}가 {next_speaker}에게 대화를 시작합니다.\n\n{ca_prompt}"
        else:
            prompt = f"{current_speaker}가 {next_speaker}에게 대화를 시작합니다.\n\n{cb_prompt}"

        message = generate_gemini_response(prompt)
        conversation_log.append({"current_speaker": current_speaker, "message": message})

        # 🔄 화자 변경 (current_speaker <-> next_speaker)
        current_speaker, next_speaker = next_speaker, current_speaker

        # # 🔥 Firestore에 대화 저장  -- 초반 테스트 - 저장 보류
        # chat_ref.set(
        #     {
        #         "last_message": {"content": message, "sender": current_speaker},
        #         "last_active_at": firestore.SERVER_TIMESTAMP,
        #         "messages": firestore.ArrayUnion([{"user_id": current_speaker, "message": message}])
        #     },
        #     merge=True
        # )


    return {"chat_id": chat_id, "conversation": conversation_log}
