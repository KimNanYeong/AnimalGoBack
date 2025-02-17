from firebase_admin import firestore
from fastapi import HTTPException
from datetime import datetime
from services import initialize_chat
from db.faiss_db import delete_faiss_index  # ✅ FAISS 벡터 삭제 함수 추가


db = firestore.client()

def delete_character(user_id: str, charac_id: str):
    """🔥 캐릭터를 삭제하면 연결된 채팅방 및 FAISS 데이터도 삭제"""

    char_ref = db.collection("characters").document(f"{user_id}-{charac_id}")
    char_doc = char_ref.get()

    if not char_doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    # ✅ Firestore에서 캐릭터 데이터 삭제
    char_ref.delete()
    print(f"✅ Character {charac_id} deleted")

    # ✅ Firestore에서 연결된 채팅방 및 메시지 삭제
    chat_id = f"{user_id}-{charac_id}"
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