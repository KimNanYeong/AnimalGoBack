import firebase_admin
from firebase_admin import credentials, firestore
import json

# Firestore 초기화 (이미 초기화된 경우 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("core/firebase_config.json")  # 환경 설정 파일
    firebase_admin.initialize_app(cred)

# Firestore DB 가져오기
db = firestore.client()

def save_to_firestore(user_id: str, character_id: str, original_path: str, processed_path: str):
    doc_ref = db.collection("users").document(user_id).collection("characters").document(character_id)
    doc_ref.set({
        "original_image": original_path,
        "processed_image": processed_path
    })