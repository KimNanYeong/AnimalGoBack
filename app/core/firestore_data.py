import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# ✅ Firebase 인증 키 JSON 파일 경로 (본인의 Firebase 서비스 계정 키 파일 경로 설정)
FIREBASE_CRED_PATH = "firebase_config.json"

# ✅ Firebase 초기화 (이미 초기화된 경우 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)

# ✅ Firestore 클라이언트 생성
db = firestore.client()

def convert_firestore_timestamps(data):
    """Firestore의 Timestamp 객체(DatetimeWithNanoseconds)를 사람이 읽을 수 있는 문자열로 변환"""
    if isinstance(data, dict):
        return {key: convert_firestore_timestamps(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_firestore_timestamps(item) for item in data]
    elif isinstance(data, datetime):  # ✅ Firestore Timestamp 변환
        return data.strftime("%Y년 %m월 %d일 %p %I시 %M분 %S초 UTC%z")  # 🔹 YYYY년 MM월 DD일 AM/PM HH:MM:SS UTC+9
    else:
        return data

def get_document_with_subcollections(doc_ref):
    """✅ Firestore 문서의 모든 데이터와 서브컬렉션을 가져오는 함수"""
    doc_data = doc_ref.get().to_dict()
    doc_data = convert_firestore_timestamps(doc_data)  # 🔹 Timestamp 변환 적용

    # ✅ 서브컬렉션 데이터 추가
    subcollections = doc_ref.collections()
    for subcollection in subcollections:
        subcollection_data = {}
        for sub_doc in subcollection.stream():
            subcollection_data[sub_doc.id] = convert_firestore_timestamps(sub_doc.to_dict())
        
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

    print("✅ Firestore 데이터를 JSON 파일로 저장 완료! (firestore_backup.json)")

# ✅ 함수 실행
export_firestore_to_json()
