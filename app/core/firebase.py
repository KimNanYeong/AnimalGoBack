import firebase_admin
from firebase_admin import credentials, firestore
import os

# 환경 변수에서 Firebase 인증 키 경로 가져오기
# FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "firebase_config.json")
# FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "core/firebase_config.json")
# FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "fbstorekey.json")
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "C:/blueback/app/core/fbstorekey.json")


# Firebase 초기화 (한 번만 실행)
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase 초기화 완료:")
else:
    print("Firebase가 이미 초기화되었습니다.")


# Firestore DB 가져오기 # Firestore 클라이언트 생성
db = firestore.client()