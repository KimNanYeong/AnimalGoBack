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
        print(f"✅ FAISS 인덱스 로드 완료! ({chat_id}) 저장된 개수: {index.ntotal}")

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
                print(f"✅ 사용자 정보 저장: {key} = {value}")

        # ✅ AI 캐릭터 정보 저장
        charac_patterns = {
            "성향": r"(넌|너는) (.+?)(야|이야|하는 걸 좋아해)"
        }
        for key, pattern in charac_patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(2).strip()
                character_profiles[charac_id][key] = value
                print(f"✅ 캐릭터 정보 저장: {key} = {value}")

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
    print(f"✅ FAISS 저장 완료! (chat_id={chat_id}) 저장된 문장 개수: {index.ntotal}")

def search_similar_messages(chat_id, charac_id, query, top_k=5):
    """사용자 및 AI 정보 기반 검색 (자연스러운 대화 스타일 적용)"""

    # ✅ "내가 누구였지?" 또는 "내 정보" 관련 질문
    if "내가 누구였지" in query or "내 정보" in query:
        if chat_id in user_profiles and user_profiles[chat_id]:
            profile_info = ", ".join([f"{k}: {v}" for k, v in user_profiles[chat_id].items()])
            responses = [
                f"음... 내가 기억하기로는 {profile_info}라고 하셨던 것 같은데, 맞나요? 😊",
                f"기억을 더듬어 보면... {profile_info}! 혹시 더 추가할 정보가 있으신가요? 🧐",
                f"당신에 대해 곰곰이 생각해봤어요. {profile_info}라고 하셨었죠? 🐻"
            ]
            return [random.choice(responses)]
        else:
            return ["음... 아직 qqq님의 정보를 잘 모르겠어요! 알려주시면 다음부터 기억할게요! 😊"]

    # ✅ "너는 누구야?" 또는 "너는 뭐 좋아해?" 관련 질문
    if "너는 누구야" in query or "너는 뭐 좋아해" in query:
        if charac_id in character_profiles and character_profiles[charac_id]:
            charac_info = ", ".join([f"{k}: {v}" for k, v in character_profiles[charac_id].items()])
            return [f"나는 {charac_info}를 좋아하는 AI야! 😊"]
        else:
            return ["음... 아직 제 정체성에 대한 정보가 부족하네요! 저에 대해 조금 더 알려주시면 기억해볼게요! 🤖"]

    # ✅ "내가 뭘 좋아했지?" 패턴 검색
    if "내가 뭘 좋아했지" in query or "내가 좋아하는 것" in query:
        if chat_id in user_profiles and "취미" in user_profiles[chat_id]:
            hobby = user_profiles[chat_id]["취미"]
            return [f"qqq님은 {hobby}를 좋아하셨잖아요! 😊"]
        else:
            return ["음... 아직 qqq님의 취향을 모르겠어요! 좋아하는 걸 알려주시면 다음부터 꼭 기억할게요! 😊"]

    # ✅ 기존 FAISS 검색 수행
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
