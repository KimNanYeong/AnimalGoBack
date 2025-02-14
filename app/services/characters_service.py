from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime
from services import initialize_chat
from db.faiss_db import delete_faiss_index  # ✅ FAISS 벡터 삭제 함수 추가


db = firestore.client()

def create_character(user_id: str, charac_id: str, nickname: str, animaltype: str, personality: str):
    """🔥 Firestore에 캐릭터 정보를 저장하고 자동으로 채팅방을 생성하는 함수"""

    # ✅ Firestore에서 성격 정보 가져오기
    personality_ref = db.collection("personality_traits").document(personality)
    personality_doc = personality_ref.get()

    if personality_doc is None or not personality_doc.exists:
        raise HTTPException(status_code=404, detail=f"Personality data not found for ID: {personality}")

    personality_data = personality_doc.to_dict()

    # ✅ Firestore에 캐릭터 저장할 데이터 구성
    character_data = {
        "charac_id": charac_id,
        "user_id": user_id,
        "nickname": nickname,
        "animaltype": animaltype,
        "personality": personality_data.get("id", personality),
        "create_at": firestore.SERVER_TIMESTAMP
    }

    # ✅ Firestore에 `characters` 컬렉션에 데이터 저장
    db.collection("characters").document(f"{user_id}_{charac_id}").set(character_data)

    # ✅ 캐릭터 생성 후 자동으로 채팅방 생성
    initialize_chat(user_id, charac_id, character_data)

    # ✅ FastAPI 응답을 반환할 때 `create_at`을 `datetime`으로 변환
    character_data["create_at"] = datetime.utcnow().isoformat()

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

from db.faiss_db import delete_faiss_index  # ✅ FAISS 벡터 삭제 함수 추가

def delete_character(user_id: str, charac_id: str):
    """🔥 캐릭터를 삭제하면 연결된 채팅방 및 FAISS 데이터도 삭제"""

    char_ref = db.collection("characters").document(f"{user_id}_{charac_id}")
    char_doc = char_ref.get()

    if not char_doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    # ✅ Firestore에서 캐릭터 데이터 삭제
    char_ref.delete()
    print(f"✅ Character {charac_id} deleted")

    # ✅ Firestore에서 연결된 채팅방 및 메시지 삭제
    chat_id = f"{user_id}_{charac_id}"
    chat_ref = db.collection("chats").document(chat_id)

    chat_doc = chat_ref.get()
    if chat_doc.exists:
        # 🔥 채팅 메시지 전체 삭제
        messages_ref = chat_ref.collection("messages")
        messages = messages_ref.stream()
        for message in messages:
            message.reference.delete()
            print(f"✅ Deleted message: {message.id}")

        # 🔥 채팅방 삭제
        chat_ref.delete()
        print(f"✅ Chat {chat_id} deleted")

    # ✅ FAISS 인덱스 삭제 추가
    delete_faiss_index(chat_id)
    print(f"🗑️ FAISS 인덱스 삭제 완료: {chat_id}")

    return {"message": f"Character {charac_id} and its chat & FAISS index deleted successfully"}