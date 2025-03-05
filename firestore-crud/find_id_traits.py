import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/data/fbkeys/fbstorekey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_document_id_by_field(collection_name, field_name, value):
    """
    Firestore에서 특정 필드 값을 기준으로 문서 ID 찾기
    - **collection_name**: 검색할 컬렉션 이름 (예: "personality_traits")
    - **field_name**: 검색할 필드명 (예: "name")
    - **value**: 검색할 값 (예: "활발한")

    🔹 반환값:
    - 문서 ID (찾았을 경우)
    - None (없을 경우)
    """
    try:
        # 🔹 Firestore에서 특정 필드 값을 기준으로 문서 조회
        query = db.collection(collection_name).where(field_name, "==", value).stream()

        # 🔹 첫 번째 결과만 반환 (여러 개일 경우 첫 번째만 선택)
        for doc in query:
            print(f"✅ Found Document ID: {doc.id}")
            return doc.id

        # 🔹 결과가 없을 경우
        print("❌ 해당 값에 해당하는 문서를 찾을 수 없습니다.")
        return None

    except Exception as e:
        print(f"🔥 오류 발생: {e}")
        return None


# ✅ 테스트 실행
document_id = get_document_id_by_field("personality_traits", "name", "활발한")
print("📌 찾은 문서 ID:", document_id)