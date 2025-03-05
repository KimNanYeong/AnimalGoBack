import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 특정 문서의 필드 값 수정
doc_ref = db.collection("test_users").document("김영호")

try:
    doc_ref.update({"국어": 100})  # 기존 '영어' 점수를 80으로 수정
    print("✅ Firestore 문서의 '국어' 점수가 변경되었습니다!")

except Exception as e:
    print(f"❌ Firestore 업데이트 오류: {e}")
