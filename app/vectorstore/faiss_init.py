import faiss
import os
import numpy as np
from sentence_transformers import SentenceTransformer

# ✅ Firestore 관련 코드 제거 (로컬 저장만 사용)
# db = firestore.client()  # 🔥 Firestore 제거

# ✅ FAISS 저장 경로
FAISS_INDEX_DIR = "db/faiss"
dimension = 768

# ✅ FAISS 인덱스 캐싱 (서버 시작 시 미리 로드하지 않음)
existing_indices = {}

def get_faiss_index_path(chat_id):
    """🔥 채팅방별 FAISS 벡터 저장 경로 반환"""
    return os.path.join(FAISS_INDEX_DIR, f"faiss_index_{chat_id}.bin")

def ensure_faiss_directory():
    """🔥 FAISS 저장 경로가 없으면 자동 생성"""
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)
        print(f"✅ FAISS 저장 폴더 생성됨: {FAISS_INDEX_DIR}")

def save_faiss_index(chat_id, index):
    """🔥 FAISS 인덱스를 저장"""
    ensure_faiss_directory()  # ✅ 폴더 자동 생성
    faiss.write_index(index, get_faiss_index_path(chat_id))
    print(f"✅ FAISS 인덱스 저장 완료: {get_faiss_index_path(chat_id)}")

def get_faiss_index(chat_id):
    """🔥 필요한 경우에만 FAISS 인덱스를 불러오기"""
    if chat_id in existing_indices:
        return existing_indices[chat_id]
    
    index_path = get_faiss_index_path(chat_id)
    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        print(f"✅ 기존 FAISS 인덱스 로드 완료: {index_path}")
    else:
        print(f"⚠️ FAISS 인덱스 없음. 새로 생성: {index_path}")
        index = faiss.IndexFlatL2(dimension)  # 🔥 새로운 빈 FAISS 인덱스 생성

    existing_indices[chat_id] = index  # ✅ 캐싱하여 불필요한 로드 방지
    return index

# ✅ SentenceTransformer 모델 캐싱 (서버 시작 시 한 번만 로드)
global_model = None

def get_sentence_model():
    """🔥 SentenceTransformer 모델을 한 번만 로드하여 캐싱"""
    global global_model
    if global_model is None:
        print("🔥 SentenceTransformer 모델 로드 중...")
        global_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    return global_model
