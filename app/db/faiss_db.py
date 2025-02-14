import faiss
import numpy as np
from firebase_admin import firestore
from sentence_transformers import SentenceTransformer
import os

# ✅ Firestore 연결
db = firestore.client()

# ✅ 문장 임베딩 모델 로드
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# ✅ FAISS 벡터 DB 초기화
dimension = 384  # SBERT 출력 벡터 차원
doc_store = {}  # ✅ 채팅방별로 문서를 저장 {chat_id: {문서 ID: 텍스트 저장}}
FAISS_INDEX_DIR = "db/faiss"  # ✅ FAISS 저장 디렉토리

def get_faiss_index_path(chat_id):
    """채팅방(chat_id)별로 FAISS 벡터 저장 경로 반환"""
    return os.path.join(FAISS_INDEX_DIR, f"faiss_index_{chat_id}.bin")

def ensure_faiss_directory():
    """FAISS 저장 경로가 없으면 자동으로 생성"""
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)
        print(f"✅ FAISS 저장 경로 생성됨: {FAISS_INDEX_DIR}")

def save_faiss_index(chat_id, index):
    """채팅방별 FAISS 벡터 DB를 파일로 저장"""
    ensure_faiss_directory()  # ✅ 경로 확인 후 생성
    faiss.write_index(index, get_faiss_index_path(chat_id))
    print(f"✅ FAISS 인덱스 저장 완료! ({chat_id})")

def load_faiss_index(chat_id):
    """채팅방별 FAISS 벡터 DB를 파일에서 불러오기"""
    index_path = get_faiss_index_path(chat_id)
    print(f"🟢 FAISS 인덱스 로드 시도: {index_path}")  # ✅ 디버깅용 출력

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        print(f"✅ FAISS 인덱스 로드 완료! ({chat_id}) 저장된 개수: {index.ntotal}")

        # ✅ 기존 문서 데이터도 불러오기
        if chat_id not in doc_store:
            doc_store[chat_id] = {}
        return index
    else:
        print(f"⚠️ FAISS 인덱스 없음, 새로 생성 ({chat_id})")
        return faiss.IndexFlatL2(dimension)  # 차원 수는 모델에 맞게 조정

def delete_faiss_index(chat_id):
    """채팅방 삭제 시 FAISS 벡터 파일도 삭제"""
    index_path = get_faiss_index_path(chat_id)
    
    if os.path.exists(index_path):
        os.remove(index_path)
        print(f"🗑️ FAISS 인덱스 삭제 완료: {index_path}")
    else:
        print(f"⚠️ FAISS 인덱스 없음, 삭제 불필요: {index_path}")

def store_chat_in_faiss(chat_id):
    """Firestore에서 채팅 기록을 가져와 FAISS에 저장 (채팅방별 저장)"""
    index = load_faiss_index(chat_id)  # ✅ 기존 FAISS 인덱스 불러오기
    messages_ref = db.collection(f"chats/{chat_id}/messages").stream()

    if chat_id not in doc_store:
        doc_store[chat_id] = {}

    for msg in messages_ref:
        msg_data = msg.to_dict()
        text = msg_data["content"]

        # ✅ 이미 저장된 문장인지 확인 (중복 방지)
        if text in doc_store[chat_id].values():
            continue  # 중복 문장은 추가하지 않음

        vector = model.encode([text])[0]  # 문장을 벡터로 변환

        # ✅ 벡터 정규화 (FAISS 검색 정확도 향상)
        vector = np.array([vector])
        faiss.normalize_L2(vector)

        index.add(vector)  # 채팅방별 FAISS 저장
        doc_store[chat_id][len(doc_store[chat_id])] = text  # 문서 ID와 원문 저장

    # ✅ 채팅방별 FAISS 저장 (index를 전달해야 함!)
    save_faiss_index(chat_id, index)  # 🔥 수정된 부분
    print(f"✅ FAISS 저장 완료! (chat_id={chat_id}) 저장된 문장 개수: {index.ntotal}")

def search_similar_messages(chat_id, query, top_k=5):
    """채팅방별 FAISS 벡터 DB에서 유사한 메시지 검색"""
    index = load_faiss_index(chat_id)

    query_vector = model.encode([query])[0]
    query_vector = np.array([query_vector])  # ✅ 정규화 적용
    faiss.normalize_L2(query_vector)

    _, indices = index.search(query_vector, top_k)

    # ✅ 채팅방별 문서 저장소에서 검색된 문장 반환
    if chat_id in doc_store:
        return [doc_store[chat_id].get(i, "[데이터 없음]") for i in indices[0]]
    else:
        return []
