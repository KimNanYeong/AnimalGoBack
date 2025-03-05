import faiss
import numpy as np
from vectorstore.faiss_init import get_faiss_index, get_sentence_model
from firebase_admin import firestore

# ✅ Firestore 연결
db = firestore.client()

# ✅ 모델 캐싱 (서버 실행 시 한 번만 로드)
model = get_sentence_model()

def search_similar_messages(chat_id, query, top_k=5):
    """🔥 Firestore 전체 로드를 없애고 필요한 문서만 조회"""
    index = get_faiss_index(chat_id)  # ✅ 기존 인덱스를 필요할 때만 로드
    if index.ntotal == 0:
        return ["음... 이번 질문은 처음 듣는 것 같아요!"]

    query_vector = model.encode(query)
    query_vector = np.array([query_vector], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    # ✅ 디버깅 로그 추가
    print(f"[DEBUG] FAISS 인덱스 차원: {index.d}")
    print(f"[DEBUG] 입력 벡터 차원: {query_vector.shape[1]}")

    if query_vector.shape[1] != index.d:
        raise ValueError(f"FAISS 인덱스 차원({index.d})과 입력 벡터 차원({query_vector.shape[1]})이 다릅니다!")


    scores, indices = index.search(query_vector, min(top_k, index.ntotal))

    # 🔥 Firestore에서 필요한 문서 ID만 가져오기
    doc_ref = db.collection("faiss_indices").document(chat_id)
    doc_data = doc_ref.get().to_dict()
    doc_ids = doc_data.get("doc_ids", []) if doc_data else []

    results = []
    seen_texts = set()

    # 🔥 Firestore에서 개별 문서만 가져오기 (전체 로드 X)
    doc_snapshots = db.get_all([db.collection(f"chats/{chat_id}/messages").document(doc_ids[idx]) 
                                for idx in indices[0] if 0 <= idx < len(doc_ids)])

    for score, doc in zip(scores[0], doc_snapshots):
        msg_data = doc.to_dict()
        if msg_data:
            original_text = msg_data["content"]
            if original_text not in seen_texts and 1 - score > 0.7:
                seen_texts.add(original_text)
                results.append((original_text, 1 - score))

    return [text for text, _ in sorted(results, key=lambda x: x[1], reverse=True)][:top_k]
