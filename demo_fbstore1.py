import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 특정 문서의 필드 값 수정
doc_ref = db.collection("characters").document("D6fDykRbuZNiiNWRKHrE")

try:
    doc_ref.update({"nickname": "사냥본능ccc"})  # 기존 '영어' 점수를 80으로 수정
    print("✅ Firestore 문서의 nickname 필드가 변경되었습니다!")

    doc_ref.update({"animaltype": "사냥본능ccc"})  # 기존 '영어' 점수를 80으로 수정
    print("✅ Firestore 문서의 animaltype 필드가 추가되었습니다!")


except Exception as e:
    print(f"❌ Firestore 업데이트 오류: {e}")
