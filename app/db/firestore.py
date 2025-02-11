from app.core.firebase import db

# ✅ [1] 사용자(User) 데이터 조회 함수
def get_user(user_id: str):
    """
    🔥 Firestore에서 특정 사용자의 데이터를 조회하는 함수 🔥
    
    - `users` 컬렉션에서 `user_id`에 해당하는 사용자 데이터를 가져옵니다.
    - 사용자가 존재하지 않으면 `{"error": "User not found"}` 반환.

    📌 **사용 예시**
    ```python
    user_data = get_user("user123")
    ```
    📌 **예상 반환값**
    ```json
    {
        "id": "user123",
        "name": "홍길동",
        "email": "user123@email.com"
    }
    ```
    """
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()  # ✅ Firestore 문서를 딕셔너리로 변환하여 반환
    return {"error": "User not found"}  # ❌ 사용자가 없으면 에러 메시지 반환

# ✅ [2] 사용자(User) 데이터 생성 함수
def create_user(user_id: str, user_data: dict):
    """
    🔥 Firestore에 새로운 사용자 데이터를 생성하는 함수 🔥
    
    - `users` 컬렉션에 `user_id`를 키로 하여 데이터를 저장합니다.

    📌 **사용 예시**
    ```python
    new_user = create_user("user123", {"name": "홍길동", "email": "user123@email.com"})
    ```
    📌 **예상 반환값**
    ```json
    {
        "id": "user123",
        "name": "홍길동",
        "email": "user123@email.com"
    }
    ```
    """
    doc_ref = db.collection("users").document(user_id)
    doc_ref.set(user_data)  # ✅ Firestore에 사용자 데이터 저장
    return {"id": user_id, **user_data}  # ✅ 저장된 데이터 반환

# ✅ [3] 사용자(User) 데이터 업데이트 함수
def update_user(user_id: str, update_data: dict):
    """
    🔥 Firestore에서 특정 사용자의 데이터를 업데이트하는 함수 🔥
    
    - `users` 컬렉션에서 `user_id`에 해당하는 문서를 업데이트합니다.

    📌 **사용 예시**
    ```python
    updated_user = update_user("user123", {"email": "newemail@email.com"})
    ```
    📌 **예상 반환값**
    ```json
    {
        "id": "user123",
        "email": "newemail@email.com"
    }
    ```
    """
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update(update_data)  # ✅ Firestore 문서 업데이트
    return {"id": user_id, **update_data}  # ✅ 업데이트된 데이터 반환

# ✅ [4] 사용자(User) 데이터 삭제 함수
def delete_user(user_id: str):
    """
    🔥 Firestore에서 특정 사용자의 데이터를 삭제하는 함수 🔥
    
    - `users` 컬렉션에서 `user_id`에 해당하는 문서를 삭제합니다.

    📌 **사용 예시**
    ```python
    delete_message = delete_user("user123")
    ```
    📌 **예상 반환값**
    ```json
    {
        "message": "User deleted"
    }
    ```
    """
    db.collection("users").document(user_id).delete()  # ✅ Firestore에서 사용자 문서 삭제
    return {"message": "User deleted"}  # ✅ 삭제 성공 메시지 반환

# ✅ [5] 특정 반려동물 데이터 조회 함수
def get_user_pet(user_id: str, pet_id: str):
    """
    🔥 Firestore에서 특정 사용자의 반려동물 데이터를 조회하는 함수 🔥
    
    - `user_pets` 컬렉션에서 `user_id_pet_id` 키를 기반으로 반려동물 데이터를 가져옵니다.
    - 반려동물이 존재하지 않으면 `{"error": "Pet not found"}` 반환.

    📌 **사용 예시**
    ```python
    pet_data = get_user_pet("user123", "pet001")
    ```
    📌 **예상 반환값**
    ```json
    {
        "user_id": "user123",
        "pet_id": "pet001",
        "name": "바둑이",
        "species": "강아지",
        "trait_id": "calm"
    }
    ```
    """
    doc_ref = db.collection("user_pets").document(f"{user_id}_{pet_id}")
    doc = doc_ref.get()
    
    if doc.exists:
        return doc.to_dict()  # ✅ Firestore 문서를 딕셔너리로 변환하여 반환
    return {"error": "Pet not found"}  # ❌ 반려동물이 없으면 에러 메시지 반환
