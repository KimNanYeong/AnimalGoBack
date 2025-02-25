import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from vectorstore.faiss_init import load_faiss_index
import services.firestore_utils as firestore_utils  # ✅ 순환 참조 방지

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def search_similar_messages(chat_id, query, top_k=5):
    """🔥 FAISS 검색 수행 후 의미 있는 문장만 반환하도록 개선"""
    index = load_faiss_index(chat_id)
    if index.ntotal == 0:
        return ["음... 이번 질문은 처음 듣는 것 같아요!"]  # ✅ 빈 인덱스일 경우 기본 메시지 반환

    # ✅ 쿼리 벡터 변환
    query_vector = model.encode(query)
    query_vector = np.array([query_vector], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    # ✅ FAISS 검색 수행 (top_k 개수만 가져오기)
    scores, indices = index.search(query_vector, min(top_k, index.ntotal))

    # ✅ Firestore에서 대화 데이터 가져오기
    chat_messages = firestore_utils.get_chat_messages(chat_id)

    results = []
    seen_texts = set()  # ✅ 중복 제거를 위한 `set()`
    
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(chat_messages):
            original_text = chat_messages[idx]["content"]

            # ✅ 중복 문장 방지 및 의미 없는 문장 필터링
            if original_text not in seen_texts and 1 - score > 0.7:  # ✅ 유사도가 0.7 이상일 때만 포함
                seen_texts.add(original_text)
                results.append((original_text, 1 - score))

    # ✅ 유사도가 높은 순으로 정렬 후 반환
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    
    return [text for text, _ in sorted_results[:top_k]]
