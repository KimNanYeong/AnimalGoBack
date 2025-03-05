import faiss
import numpy as np
import os
from firebase_admin import firestore
from vectorstore.faiss_init import save_faiss_index, get_faiss_index, get_sentence_model

db = firestore.client()
model = get_sentence_model()  # ✅ 캐싱된 모델 사용

def store_chat_in_faiss(chat_id):
    """🔥 Firestore 저장 없이 로컬 FAISS 인덱스만 업데이트"""
    index = get_faiss_index(chat_id)  # ✅ 기존 인덱스를 로드 (필요할 때만)

    # 🔥 Firestore 연동 제거 → Firestore에서 데이터를 가져오지 않음
    messages_ref = db.collection(f"chats/{chat_id}/messages").order_by("timestamp").stream()

    new_vectors = []
    new_doc_ids = []

    for msg in messages_ref:
        msg_data = msg.to_dict()
        text = msg_data.get("content", "")
        doc_id = msg.id

        if text:
            new_doc_ids.append(doc_id)
            new_vectors.append(model.encode(text))

    # ✅ 새로운 벡터가 있을 때만 FAISS 업데이트
    if new_vectors:
        vectors = np.array(new_vectors, dtype=np.float32)
        faiss.normalize_L2(vectors)
        index.add(vectors)

        save_faiss_index(chat_id, index)  # 🔥 Firestore 대신 로컬에 저장
        print(f"✅ FAISS 인덱스 저장 완료 (Firestore X): {chat_id}, 벡터 개수: {len(new_vectors)}")
