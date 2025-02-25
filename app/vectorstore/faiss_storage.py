import faiss
import numpy as np
import os
from firebase_admin import firestore
from sentence_transformers import SentenceTransformer
from vectorstore.faiss_init import save_faiss_index, load_faiss_index

FAISS_INDEX_DIR = "db/faiss"

db = firestore.client()
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def store_chat_in_faiss(chat_id):
    """🔥 Firestore 채팅 데이터를 FAISS에 저장 (Firestore 문서 ID도 함께 저장)"""
    index = faiss.IndexFlatL2(768)
    messages_ref = db.collection(f"chats/{chat_id}/messages").order_by("timestamp").stream()

    texts = []
    vectors = []
    doc_ids = []  # ✅ Firestore 문서 ID 저장 (FAISS 검색 후 원본 문장 찾기 용도)

    for msg in messages_ref:
        msg_data = msg.to_dict()
        text = msg_data["content"]
        doc_id = msg.id  # ✅ Firestore 문서 ID 저장

        if text not in texts:
            texts.append(text)
            doc_ids.append(doc_id)  # ✅ 문서 ID 저장
            vector = model.encode(text)  # ✅ 리스트 변환 없이 직접 벡터화
            vectors.append(vector)

    if vectors:
        vectors = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(vectors)
        index.add(vectors)

        # ✅ Firestore에 FAISS 인덱스와 문서 ID 매핑 정보 저장
        doc_ref = db.collection("faiss_indices").document(chat_id)
        doc_ref.set({"doc_ids": doc_ids})  # ✅ Firestore에 문서 ID 목록 저장

    save_faiss_index(chat_id, index)
    print(f"✅ FAISS 인덱스 저장 완료: {chat_id} (문서 {len(texts)}개)")

def load_existing_faiss_indices():
    """🔥 기존의 FAISS 인덱스를 불러오기"""
    existing_indices = {}

    for file_name in os.listdir(FAISS_INDEX_DIR):
        if file_name.endswith(".bin"):
            chat_id = file_name.replace("faiss_index_", "").replace(".bin", "")
            existing_indices[chat_id] = load_faiss_index(chat_id)

    return existing_indices
