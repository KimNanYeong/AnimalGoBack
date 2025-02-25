import faiss
import os
import numpy as np
from firebase_admin import firestore

# Firestore 연결
db = firestore.client()

# FAISS 저장 경로
FAISS_INDEX_DIR = "db/faiss"
dimension = 768

def get_faiss_index_path(chat_id):
    """채팅방별 FAISS 벡터 저장 경로 반환"""
    return os.path.join(FAISS_INDEX_DIR, f"faiss_index_{chat_id}.bin")

def ensure_faiss_directory():
    """FAISS 저장 경로가 없으면 자동 생성"""
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)

def save_faiss_index(chat_id, index):
    """FAISS 인덱스를 저장"""
    ensure_faiss_directory()
    faiss.write_index(index, get_faiss_index_path(chat_id))

def load_faiss_index(chat_id):
    """FAISS 인덱스를 불러오기"""
    index_path = get_faiss_index_path(chat_id)
    if os.path.exists(index_path):
        return faiss.read_index(index_path)
    return faiss.IndexFlatL2(dimension)  # 빈 인덱스 반환
