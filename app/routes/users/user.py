from fastapi import APIRouter, HTTPException
# from app.db.firestore import get_user, create_user, update_user, delete_user
# from app.schemas.user import UserCreate, UserUpdate
from db import get_user, create_user, update_user, delete_user
from schemas.user import UserCreate, UserUpdate

router = APIRouter()

@router.get("/{user_id}")
def read_user(user_id: str):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/")
def create_new_user(user: UserCreate):
    return create_user(user.user_id, user.dict())

@router.put("/{user_id}")
def update_existing_user(user_id: str, user: UserUpdate):
    return update_user(user_id, user.dict())

@router.delete("/{user_id}")
def remove_user(user_id: str):
    return delete_user(user_id)
