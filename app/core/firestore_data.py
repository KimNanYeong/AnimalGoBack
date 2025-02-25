import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta

# ✅ Firebase 인증 키 JSON 파일 경로
FIREBASE_CRED_PATH = "firebase_config.json"

# ✅ Firebase 초기화 (이미 초기화된 경우 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)

# ✅ Firestore 클라이언트 생성
db = firestore.client()

def convert_firestore_timestamps(data):
    """Firestore Timestamp 객체를 사람이 읽을 수 있는 문자열로 변환"""
    if isinstance(data, dict):
        return {key: convert_firestore_timestamps(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_firestore_timestamps(item) for item in data]
    elif isinstance(data, datetime):  # ✅ Firestore Timestamp 변환
        korea_timezone = timezone(timedelta(hours=9))  # ✅ UTC+9 (한국 시간)
        local_time = data.astimezone(korea_timezone)
        return local_time.strftime("%Y년 %m월 %d일 %p %I시 %M분 %S초 UTC+9")  # 🔹 Firestore UI와 동일한 형식
    else:
        return data

def get_document_with_subcollections(doc_ref):
    """✅ Firestore 문서의 모든 데이터와 서브컬렉션을 가져오는 함수"""
    doc_data = doc_ref.get().to_dict()
    doc_data = convert_firestore_timestamps(doc_data)  # 🔹 Timestamp 변환 적용

    # ✅ messages 정렬 추가 (Firestore에서 정렬된 상태로 가져옴)
    messages_ref = doc_ref.collection("messages").order_by("timestamp").stream()
    
    sorted_messages = []
    for msg in messages_ref:
        msg_data = msg.to_dict()
        sorted_messages.append({
            "id": msg.id,  
            "content": msg_data.get("content", ""),
            "sender": msg_data.get("sender", ""),
            "timestamp": msg_data.get("timestamp")  # ✅ Firestore Timestamp 유지
        })

    doc_data["messages"] = sorted_messages  # 🔹 Firestore에서 정렬된 데이터를 그대로 사용

    # ✅ 서브컬렉션 데이터 추가
    subcollections = doc_ref.collections()
    for subcollection in subcollections:
        subcollection_data = []
        for sub_doc in subcollection.stream():
            sub_doc_data = convert_firestore_timestamps(sub_doc.to_dict())
            sub_doc_data["id"] = sub_doc.id
            subcollection_data.append(sub_doc_data)

        doc_data[subcollection.id] = subcollection_data  # 🔹 서브컬렉션 추가

    return doc_data

def export_firestore_to_json():
    """✅ Firestore 데이터를 JSON 파일로 저장하는 함수 (서브컬렉션 포함)"""
    data = {}

    # ✅ Firestore의 최상위 컬렉션 목록 가져오기
    collections = db.collections()

    for collection in collections:
        collection_name = collection.id
        data[collection_name] = {}

        # ✅ 해당 컬렉션의 문서 가져오기 (서브컬렉션 포함)
        docs = db.collection(collection_name).stream()
        for doc in docs:
            data[collection_name][doc.id] = get_document_with_subcollections(doc.reference)

    # ✅ JSON 파일로 저장
    with open("firestore_backup.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print("✅ Firestore 데이터를 정렬하여 JSON 파일로 저장 완료! (firestore_backup_sorted.json)")

# ✅ 함수 실행
export_firestore_to_json()
