import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Firebase 인증 키 JSON 파일 경로
FIREBASE_CRED_PATH = "firebase_config.json"

# ✅ Firebase 초기화 (이미 초기화된 경우 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)

# ✅ Firestore 클라이언트 연결
db = firestore.client()

def update_chats_structure():
    """✅ Firestore의 chats 컬렉션 필드명 변경"""
    chats_ref = db.collection("chats")
    docs = chats_ref.stream()

    for doc in docs:
        chat_data = doc.to_dict()

        # ✅ 필드명 변경
        updated_data = {
            "chat_id": chat_data.get("chat_id"),
            "nickname": chat_data.get("character_name"),  # character_name → nickname
            "personality": chat_data.get("character_personality"),  # character_personality → personality
            "create_at": chat_data.get("created_at"),  # created_at → create_at
            "last_active_at": chat_data.get("last_active_at"),
            "last_message": chat_data.get("last_message"),
        }

        # ✅ 필요 없는 필드 제거 (species 필드 삭제 가능)
        if "species" in updated_data:
            del updated_data["species"]

        # ✅ Firestore 문서 업데이트
        chats_ref.document(doc.id).update(updated_data)
        print(f"✅ Updated chat: {doc.id}")

# ✅ 함수 실행
update_chats_structure()
