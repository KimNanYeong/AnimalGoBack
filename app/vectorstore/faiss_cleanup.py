import os

# ✅ FAISS 인덱스 파일 저장 디렉토리
FAISS_INDEX_DIR = "db/faiss"

def delete_faiss_index(chat_id):
    """🔥 FAISS 인덱스 삭제 기능"""
    index_path = os.path.join(FAISS_INDEX_DIR, f"faiss_index_{chat_id}.bin")
    if os.path.exists(index_path):
        os.remove(index_path)
        print(f"✅ FAISS 인덱스 삭제 완료: {index_path}")
    else:
        print(f"⚠️ FAISS 인덱스 없음: {index_path}")
