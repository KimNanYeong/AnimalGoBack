import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 저장할 데이터
data = {
    "이름": "김영호",
    "국어": 70,
    "영어": 50,
    "수학": 55
}

try:
    # Firestore에 데이터 추가
    doc_ref = db.collection("test_users_001").document(data["이름"])  # 문서 ID를 이름으로 설정
    doc_ref.set(data)

    print(f"✅ Firestore에 '{data['이름']}'의 점수 데이터가 저장되었습니다!")

except Exception as e:
    print(f"❌ Firestore 저장 오류: {e}")