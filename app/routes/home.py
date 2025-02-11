from fastapi import APIRouter
import firebase_admin
from firebase_admin import firestore
from app.db.firestore import get_character  # ✅ get_character를 올바르게 import

main_router = APIRouter()

@main_router.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}
