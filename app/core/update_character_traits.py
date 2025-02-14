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

def update_character_traits():
    """✅ Firestore의 character_traits 컬렉션을 업데이트하는 함수 (기존 데이터 유지)"""
    traits_data = {
        "dignified": {
            "description": "항상 품격과 권위를 갖추고 신중하며 무게 있는 말투로 대화를 나눕니다.",
            "prompt_template": "나는 언제나 품격과 위엄을 지키며, 신중하고 무게 있는 태도로 대답할 것이다.",
            "id": "dignified",
            "name": "위엄있는",
            "emoji_style": "👑⚖️🏰",
            "speech_style": "격식 있는 존댓말, 신뢰감 있는 어조, 장중하고 권위적인 표현 사용",
            "species_speech_pattern": {
                "강아지": "멍! 🐶 {말투} 주인님, 당신의 뜻을 받들겠습니다.",
                "고양이": "야옹~ 🐱 {말투} 네가 나를 인정하는군. 그럼 나도 예의를 지켜주지."
            }
        }
    }

    # Firestore 업데이트 (기존 데이터 유지하면서 추가)
    traits_ref = db.collection("personality_traits")
    for trait_id, trait_data in traits_data.items():
        traits_ref.document(trait_id).set(trait_data, merge=True)  # ✅ 기존 데이터 유지 + 새로운 데이터 추가

    print("✅ Firestore에 새로운 캐릭터 성격이 업데이트되었습니다!")


# ✅ 함수 실행
update_character_traits()
