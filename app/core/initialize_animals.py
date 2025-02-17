import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Firebase 인증 키 JSON 파일 경로 (본인의 Firebase 서비스 계정 키 파일 경로 설정)
FIREBASE_CRED_PATH = "firebase_config.json"

# ✅ Firebase 초기화 (이미 초기화된 경우 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)

# ✅ Firestore 클라이언트 연결
db = firestore.client()


def initialize_animal_collection():
    """
    Firestore에 `animals` 컬렉션을 초기화하는 함수
    """
    animal_data = {
        "bird": "새",
        "cat": "고양이",
        "dog": "개",
        "horse": "말",
        "sheep": "양",
        "cow": "소",
        "elephant": "코끼리",
        "bear": "곰",
        "zebra": "얼룩말",
        "giraffe": "기린"
    }

    try:
        for animaltype_id, korean_name in animal_data.items():
            doc_ref = db.collection("animals").document(animaltype_id)  # 🔹 영어 이름을 문서 ID로 사용
            doc_ref.set({"english": animaltype_id, "korean": korean_name})  # 🔹 Firestore에 저장
            print(f"✅ {animaltype_id} → {korean_name} 저장 완료")

        print("🎉 Firestore `animals` 컬렉션 초기화 완료!")
    
    except Exception as e:
        print(f"🔥 오류 발생: {e}")

# ✅ 실행
initialize_animal_collection()