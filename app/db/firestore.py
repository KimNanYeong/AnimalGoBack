from core.firebase import db

def get_user(user_id: str):
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def create_user(user_id: str, user_data: dict):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.set(user_data)
    return {"id": user_id, **user_data}

def update_user(user_id: str, update_data: dict):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update(update_data)
    return {"id": user_id, **update_data}

def delete_user(user_id: str):
    db.collection("users").document(user_id).delete()
    return {"message": "User deleted"}
