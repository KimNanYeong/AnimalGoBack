# from app.core.firebase import db
from core.firebase import db
from fastapi import HTTPException

# ✅ [1] 사용자(User) 데이터 조회 함수
def get_user(user_id: str):
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()  # ✅ Firestore 문서를 딕셔너리로 변환하여 반환
    return {"error": "User not found"}  # ❌ 사용자가 없으면 에러 메시지 반환

# ✅ [2] 사용자(User) 데이터 생성 함수
def create_user(user_id: str, user_data: dict):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.set(user_data)  # ✅ Firestore에 사용자 데이터 저장
    return {"id": user_id, **user_data}  # ✅ 저장된 데이터 반환

# ✅ [3] 사용자(User) 데이터 업데이트 함수
def update_user(user_id: str, update_data: dict):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update(update_data)  # ✅ Firestore 문서 업데이트
    return {"id": user_id, **update_data}  # ✅ 업데이트된 데이터 반환

# ✅ [4] 사용자(User) 데이터 삭제 함수
def delete_user(user_id: str):
    db.collection("users").document(user_id).delete()  # ✅ Firestore에서 사용자 문서 삭제
    return {"message": "User deleted"}  # ✅ 삭제 성공 메시지 반환

# ✅ [5] 특정 반려동물 데이터 조회 함수
def get_user_pet(user_id: str, pet_id: str):
    doc_ref = db.collection("user_pets").document(f"{user_id}_{pet_id}")
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()  # ✅ Firestore 문서를 딕셔너리로 변환하여 반환
    return {"error": "Pet not found"}  # ❌ 반려동물이 없으면 에러 메시지 반환

# ✅ [6] 특정 캐릭터 데이터 조회 함수
def get_character(character_id: str):
    """Firestore에서 특정 캐릭터 데이터를 가져오는 함수"""
    char_ref = db.collection("characters").document(character_id)
    char_doc = char_ref.get()

    if not char_doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    return char_doc.to_dict()

# def save_to_firestore(user_id: str, character_id: str, original_path: str, processed_path: str):
#     doc_ref = db.collection("users").document(user_id).collection("characters").document(character_id)
#     doc_ref.set({
#         "original_image": original_path,
#         "processed_image": processed_path
#     })