import numpy as np
from sentence_transformers import SentenceTransformer
import vectorstore.faiss_search as faiss_search  # ✅ 순환 참조 방지
import time  # ✅ 실행 시간 측정을 위한 모듈 추가

# ✅ SentenceTransformer 모델 로드 (FAISS에서 사용 중인 것과 동일하게)
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def compute_cosine_similarity(vec1, vec2):
    """🔥 코사인 유사도 계산"""
    norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    if norm_product == 0:
        return 0  # 예외 처리: 벡터 길이가 0인 경우
    return np.dot(vec1, vec2) / norm_product

def filter_similar_messages(similar_messages, query, min_sim=0.4, max_sim=0.85):
    """🔥 FAISS 검색된 결과 중 의미 있는 문장만 반환 (유사도 필터링)"""
    if not similar_messages or not isinstance(similar_messages, list):
        return []  # 검색된 문장이 없거나 비정상적인 데이터일 경우 빈 리스트 반환

    query_vector = model.encode(query)  # ✅ 한 번만 벡터 변환하여 성능 최적화
    filtered_messages = []

    for message in similar_messages:
        if not isinstance(message, str) or message.strip() == "":
            continue  # ✅ 빈 문자열 또는 잘못된 데이터는 무시

        message_vector = model.encode(message)
        similarity = compute_cosine_similarity(query_vector, message_vector)

        # ✅ 유사도 범위 동적 조정
        if min_sim < similarity < max_sim and message != query:
            filtered_messages.append((message, similarity))

    # ✅ 유사도 높은 순으로 정렬 후 반환
    filtered_messages.sort(key=lambda x: x[1], reverse=True)
    return [msg for msg, _ in filtered_messages]

def get_similar_messages(chat_id, user_input, top_k=3):
    """🔥 FAISS 벡터 검색을 수행하고 필터링된 메시지 반환 (속도 최적화)"""
    start_time = time.time()  # ✅ FAISS 검색 시작 시간
    similar_messages = faiss_search.search_similar_messages(chat_id, user_input, top_k)
    end_time = time.time()  # ✅ FAISS 검색 완료 시간

    print(f"🔥 FAISS 검색 완료 ({chat_id}): {end_time - start_time:.3f}초")  # ✅ 실행 시간 출력

    if not similar_messages:
        return "과거에 비슷한 대화를 찾을 수 없어요!"

    # ✅ 유사도가 높은 메시지만 필터링
    filtered_messages = filter_similar_messages(similar_messages, user_input, min_sim=0.5, max_sim=0.85)

    return "\n".join(filtered_messages[:top_k]) if filtered_messages else "관련된 과거 대화가 없어요!"