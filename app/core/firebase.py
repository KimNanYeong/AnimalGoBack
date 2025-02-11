import firebase_admin
from firebase_admin import credentials, firestore
import os

# Firestore 인증 정보 설정 (경로 확인)
config_path = os.path.join(os.path.dirname(__file__), "firebase_config.json")

# Firebase 앱이 여러 번 초기화되는 오류 방지
if not firebase_admin._apps:
    cred = credentials.Certificate(config_path)
    firebase_admin.initialize_app(cred)

# Firestore 클라이언트 생성
db = firestore.client()
