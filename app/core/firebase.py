import firebase_admin
from firebase_admin import credentials, firestore
import os

# 환경 변수에서 Firebase 인증 키 경로 가져오기
# FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "firebase_config.json")
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "core/firebase_config.json")

# Firebase 초기화
cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)

# Firestore DB 가져오기
db = firestore.client()