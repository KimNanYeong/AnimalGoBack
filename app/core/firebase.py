import firebase_admin
from firebase_admin import credentials, firestore
import os

# ✅ Firebase 인증 키 경로 설정 (환경 변수 우선, 없으면 기본값 사용)
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", os.path.join(os.path.dirname(__file__), "firebase_config.json"))

# ✅ Firebase 앱이 여러 번 초기화되는 오류 방지
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase 초기화 완료")
else:
    print("⚠️ Firebase가 이미 초기화되었습니다.")

# ✅ Firestore 클라이언트 생성
db = firestore.client()
