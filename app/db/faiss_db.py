import faiss
import numpy as np
from firebase_admin import firestore
from sentence_transformers import SentenceTransformer
import os
import re
import random

# ✅ Firestore 연결
db = firestore.client()

user_profiles = {}  # ✅ 사용자 정보 저장 {chat_id: {"직업": "개발자", "취미": "코딩"}}
character_profiles = {}  # ✅ AI 캐릭터 정보 저장 {charac_id: {"취미": "책 읽기"}}


# ✅ 문장 임베딩 모델 로드
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


# ✅ FAISS 벡터 DB 초기화
dimension = 768
doc_store = {}  # ✅ 채팅방별로 문서를 저장 {chat_id: {문서 ID: 텍스트 저장}}
FAISS_INDEX_DIR = "db/faiss"  # ✅ FAISS 저장 디렉토리

def get_faiss_index_path(chat_id):
    """채팅방(chat_id)별로 FAISS 벡터 저장 경로 반환"""
    return os.path.join(FAISS_INDEX_DIR, f"faiss_index_{chat_id}.bin")

def ensure_faiss_directory():
    """FAISS 저장 경로가 없으면 자동으로 생성"""
    if not os.path.exists(FAISS_INDEX_DIR):
        os.makedirs(FAISS_INDEX_DIR)
        # print(f"✅ FAISS 저장 경로 생성됨: {FAISS_INDEX_DIR}")

def save_faiss_index(chat_id, index):
    """채팅방별 FAISS 벡터 DB를 파일로 저장"""
    ensure_faiss_directory()  # ✅ 경로 확인 후 생성
    faiss.write_index(index, get_faiss_index_path(chat_id))
    # print(f"✅ FAISS 인덱스 저장 완료! ({chat_id})")

def load_faiss_index(chat_id):
    """채팅방별 FAISS 벡터 DB를 파일에서 불러오기"""
    index_path = get_faiss_index_path(chat_id)

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        # print(f"✅ FAISS 인덱스 로드 완료! ({chat_id}) 저장된 개수: {index.ntotal}")

        # ✅ doc_store 동기화
        if chat_id not in doc_store:
            doc_store[chat_id] = {}
        
        messages_ref = db.collection(f"chats/{chat_id}/messages").stream()
        for msg in messages_ref:
            msg_data = msg.to_dict()
            text = msg_data["content"]
            doc_id = len(doc_store[chat_id])
            doc_store[chat_id][doc_id] = text  # Firestore 데이터와 동기화
        
        return index
    else:
        return faiss.IndexFlatL2(dimension)
    
def load_existing_faiss_indices():
    """서버 시작 시 저장된 모든 FAISS 인덱스를 불러옴"""
    if not os.path.exists(FAISS_INDEX_DIR):
        print(f"⚠️ FAISS 인덱스 디렉토리가 존재하지 않음: {FAISS_INDEX_DIR}")
        return

    for file in os.listdir(FAISS_INDEX_DIR):
        if file.endswith(".bin"):
            chat_id = file.replace("faiss_index_", "").replace(".bin", "")
            load_faiss_index(chat_id)
            print(f"✅ 기존 FAISS 인덱스 로드 완료: {chat_id}")

def delete_faiss_index(chat_id):
    """채팅방 삭제 시 FAISS 벡터 파일도 삭제"""
    index_path = get_faiss_index_path(chat_id)
    
    if os.path.exists(index_path):
        os.remove(index_path)
        print(f"🗑️ FAISS 인덱스 삭제 완료: {index_path}")
    else:
        print(f"⚠️ FAISS 인덱스 없음, 삭제 불필요: {index_path}")


def store_chat_in_faiss(chat_id, charac_id):
    """Firestore에서 채팅 기록을 가져와 FAISS에 저장 (사용자 및 AI 정보 포함)"""
    global user_profiles, character_profiles  # ✅ 글로벌 변수 보장

    index = faiss.IndexFlatL2(dimension)  # ✅ 새로운 FAISS 인덱스 생성
    doc_store.setdefault(chat_id, {})  # ✅ 문장 저장소 초기화
    user_profiles.setdefault(chat_id, {})  # ✅ 사용자 정보 기본값 설정
    character_profiles.setdefault(charac_id, {})  # ✅ 캐릭터 정보 기본값 설정

    messages_ref = db.collection(f"chats/{chat_id}/messages").order_by("timestamp").stream()

    vectors = []  # ✅ 벡터 저장 리스트
    texts = []  # ✅ 원본 텍스트 저장 리스트

    for msg in messages_ref:
        msg_data = msg.to_dict()
        text = msg_data["content"]

        # ✅ 사용자 정보 저장 (패턴 기반 추출)
        user_patterns = {
            "정체성": r"나는 (.+?)(야|이야|해)",
            "취미": r"내 취미는 (.+?)(야|이야)",
            "직업": r"내 직업은 (.+?)(야|이야)",
            "사는 곳": r"내가 사는 곳은 (.+?)(야|이야)",
            "나이": r"나는 (\d+)살(이야|야)",
            "MBTI": r"내 MBTI는 (.+?)(야|이야)"
        }

        for key, pattern in user_patterns.items():
            match = re.search(pattern, text)  # ✅ `re.search()`로 문장 내 전체 검색
            if match:
                value = match.group(1).strip()
                user_profiles[chat_id][key] = value
                # print(f"✅ 사용자 정보 저장: {key} = {value}")

        # ✅ AI 캐릭터 정보 저장
        charac_patterns = {
            "성향": r"(넌|너는) (.+?)(야|이야|하는 걸 좋아해)"
        }
        for key, pattern in charac_patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(2).strip()
                character_profiles[charac_id][key] = value
                # print(f"✅ 캐릭터 정보 저장: {key} = {value}")

        # ✅ FAISS에 저장할 문장 벡터화
        if text not in texts:  # ✅ 중복 방지
            texts.append(text)
            vector = model.encode([text])[0]  # ✅ 문장 벡터 생성
            vectors.append(vector)

    # ✅ FAISS 인덱스에 벡터 추가
    if vectors:
        vectors = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(vectors)  # ✅ 벡터 정규화
        index.add(vectors)
        for i, text in enumerate(texts):
            doc_store[chat_id][i] = text

    # ✅ FAISS 인덱스 저장
    save_faiss_index(chat_id, index)
    # print(f"✅ FAISS 저장 완료! (chat_id={chat_id}) 저장된 문장 개수: {index.ntotal}")

def get_recent_messages(chat_id, limit=10):
    """Firestore에서 최근 n개의 메시지를 가져오는 함수"""
    messages_ref = db.collection(f"chats/{chat_id}/messages").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    messages = messages_ref.stream()

    recent_messages = []
    for msg in messages:
        msg_data = msg.to_dict()
        recent_messages.append({"content": msg_data["content"], "timestamp": msg_data["timestamp"]})

    return recent_messages

def search_user_hobby(chat_id):
    """사용자의 취미를 최근 대화에서 직접 검색"""
    messages = get_recent_messages(chat_id, limit=10)  # 최근 10개 대화 가져오기
    hobby_keywords = ["취미", "좋아하는", "내가 좋아하는", "나는", "내 취미는"]
    
    for msg in messages:
        content = msg["content"]
        for keyword in hobby_keywords:
            if keyword in content:
                return content.replace("내 취미는", "🐶 멍멍! 너의 취미는") + "야! 🚲"
    
    return None  # 취미 정보가 없으면 None 반환

def search_similar_messages(chat_id, charac_id, query, top_k=5):
    """FAISS 검색을 수행하면서, '취미' 관련 질문일 경우 우선적으로 기억한 정보 반환"""

    # ✅ 사용자의 취미 질문에 대한 즉시 응답
    if "내가 뭘 좋아했지" in query or "내 취미가 뭐였지" in query or "내가 좋아하는 것" in query:
        # 🔹 Firestore 또는 FAISS에서 취미 정보를 우선 검색
        hobby_response = search_user_hobby(chat_id)
        if hobby_response:
            return [hobby_response]
        
        if chat_id in user_profiles and "취미" in user_profiles[chat_id]:
            hobby = user_profiles[chat_id]["취미"]
            return [f"🐶 멍멍! {hobby}가 너의 취미였지! 기억하고 있어! 🚲"]

        return ["음... 아직 너의 취미를 잘 모르겠어! 알려주면 내가 꼭 기억할게! 😊"]

    # ✅ 기존 FAISS 검색 수행 (변경 없음)
    index = load_faiss_index(chat_id)
    if index.ntotal == 0:
        return ["음... 이번 질문은 처음 듣는 것 같아요! 조금 더 설명해 주시면 좋을 것 같아요! 😊"]

    query_vector = model.encode([query])[0]
    query_vector = np.array([query_vector], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    scores, indices = index.search(query_vector, min(top_k, index.ntotal))

    seen_texts = set()
    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx in doc_store.get(chat_id, {}):
            text = doc_store[chat_id][idx]
            if text not in seen_texts:
                results.append((text, 1 - score))
                seen_texts.add(text)

    prioritized_results = sorted(results, key=lambda x: x[1], reverse=True)

    if prioritized_results:
        similar_texts = [text for text, _ in prioritized_results[:top_k]]
        return [f"음... 비슷한 대화를 찾아보니 '{similar_texts[0]}'라고 말씀하신 적이 있어요! 😊"]

    return ["음... 이번 질문은 처음 듣는 것 같아요! 조금 더 설명해 주시면 좋을 것 같아요! 😊"]
