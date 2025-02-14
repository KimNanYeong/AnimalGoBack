import firebase_admin
from firebase_admin import credentials, firestore

# 🔹 Firebase 인증 정보 설정 (JSON 키 파일 필요)
FIREBASE_CRED_PATH = "c:/data/fbkeys/fbkey.json"  # 🔹 Firebase 인증 키 파일 경로
cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)

# 🔹 Firestore 클라이언트 초기화
db = firestore.client()

# 🔹 성격 데이터 (한글 & 영어)
appearance_traits_data = {
    "cute": {"korean": "귀여움", "english": "Cute"},
    "pretty": {"korean": "이쁜", "english": "Pretty"},
    "scary": {"korean": "무서운", "english": "Scary"},
    "lovely": {"korean": "사랑스러운", "english": "Lovely"},
    "playful": {"korean": "장난스러운", "english": "Playful"},
    "chic": {"korean": "시크한", "english": "Chic"}
}

# ==========================
# 🔹 Firestore `appearance_traits` 컬렉션 데이터 추가
# ==========================
def initialize_appearance_traits():
    try:
        for key, value in appearance_traits_data.items():
            trait_ref = db.collection("appearance_traits").document(key)
            if not trait_ref.get().exists:
                trait_ref.set(value)
                print(f"✅ 외모 특성 추가됨: {value['korean']} ({value['english']})")
            else:
                print(f"🔹 이미 존재하는 데이터: {value['korean']} ({value['english']})")

        print("🔥 Firestore `appearance_traits` 데이터 설정 완료!")
    except Exception as e:
        print(f"❌ Firestore 설정 실패: {e}")

# 🔹 Firestore 초기화 실행
if __name__ == "__main__":
    initialize_appearance_traits()
