from firebase_admin import firestore
from datetime import datetime, timedelta

db = firestore.client()

def get_character_data(user_id: str, charac_id: str):
    """Firestore에서 캐릭터 데이터 가져오기 (characters 컬렉션 사용)"""
    character_ref = db.collection("characters").document(f"{user_id}-{charac_id}")
    character_doc = character_ref.get()

    if not character_doc.exists:
        return {"nickname": "이름 없음", "personality_id": "default", "animaltype": "미확인"}

    character_data = character_doc.to_dict()

    # ✅ 기존 "personality" 값을 "personality_id"로 변경
    character_data["personality_id"] = character_data.get("personality", "default")

    return character_data

def get_personality_data(personality_id: str):
    """Firestore에서 성격 데이터를 가져오는 함수"""
    personality_ref = db.collection("personality_traits").document(personality_id)
    personality_doc = personality_ref.get()

    if not personality_doc.exists:
        return {
            "description": "기본 성격",
            "emoji_style": "🙂",
            "id": "default",
            "name": "기본",
            "prompt_template": "나는 친절한 말투로 대답할게!",
            "species_speech_pattern": {},
            "speech_style": "기본 말투"
        }

    return personality_doc.to_dict()

def save_message(chat_id: str, sender: str, content: str, is_response=False):
    """Firestore에 메시지 저장 (timestamp 타입 유지)"""
    messages_ref = db.collection("chats").document(chat_id).collection("messages")

    now = datetime.utcnow()  # ✅ Firestore의 timestamp 형식으로 저장

    # ✅ AI 응답인 경우 10ms 추가 (User → AI 순서 유지)
    if is_response:
        now += timedelta(milliseconds=10)

    message_data = {
        "sender": sender,
        "content": content,
        "timestamp": now  # ✅ Firestore에서 자동으로 Timestamp 형식으로 저장됨!
    }

    messages_ref.add(message_data)
    return message_data  # ✅ Firestore 저장 데이터 반환 (디버깅 및 검증 용이)

def initialize_chat(user_id: str, charac_id: str, character_data: dict = None):
    """🔥 채팅방이 존재하지 않으면 Firestore에 자동 생성"""
    chat_id = f"{user_id}-{charac_id}"
    chat_ref = db.collection("chats").document(chat_id)
    character_ref = db.collection("characters").document(f"{user_id}-{charac_id}")

    # ✅ Firestore에서 한 번만 조회하여 성능 최적화
    chat_doc = chat_ref.get()
    character_doc = character_ref.get()

    # ✅ 캐릭터가 삭제된 상태면 채팅방 생성하지 않음
    if not character_doc.exists:
        print(f"🚨 Character {charac_id} not found. Skipping chat creation.")
        return

    # ✅ character_data가 None일 경우 기본값 설정
    if not character_data:
        character_data = {
            "nickname": "이름 없음",
            "personality": "default",
            "animaltype": "미확인"
        }

    # ✅ 채팅방이 없을 경우에만 생성
    if not chat_doc.exists:
        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "nickname": character_data.get("nickname", "이름 없음"),
            "personality": character_data.get("personality", "default"),
            "animaltype": character_data.get("animaltype", "미확인"),
            "create_at": firestore.SERVER_TIMESTAMP,
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "last_message": None
        }
        chat_ref.set(chat_data)
        print(f"✅ Firestore: 채팅방 생성 완료 - {chat_id}")

def get_user_nickname(user_id: str):
    """Firestore에서 사용자 닉네임 가져오기"""
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        return user_doc.to_dict().get("user_nickname", user_id)
    return user_id  # 기본값 반환

def get_chat_messages(chat_id: str):
    """Firestore에서 채팅 기록을 가져오는 함수 (AI & 사용자 구분 포함)"""
    messages_ref = db.collection("chats").document(chat_id).collection("messages").order_by("timestamp")
    messages = messages_ref.stream()

    return [
        {
            "content": msg.to_dict()["content"],
            "sender": msg.to_dict()["sender"],  # ✅ AI인지 사용자 메시지인지 구분 추가
            "timestamp": msg.to_dict()["timestamp"]
        }
        for msg in messages
    ]
