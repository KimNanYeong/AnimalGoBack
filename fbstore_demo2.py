import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 기존 문서에 새로운 필드 추가
doc_ref = db.collection("test_users").document("김영호")

try:
    doc_ref.update({"논리학": 99})  # 기존 문서에 '과학' 필드 추가
    print("✅ Firestore 문서에 '논리학' 필드가 추가되었습니다!")
    

except Exception as e:
    print(f"❌ Firestore 업데이트 오류: {e}")