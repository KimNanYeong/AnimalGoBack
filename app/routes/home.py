from fastapi import APIRouter
import firebase_admin
from firebase_admin import firestore
import db.firestore as fs

main_router = APIRouter()

@main_router.get("/")
def read_root():
    # fs.create_user("1",{"test":"test"})
    return {"message": "Hello, FastAPI!"}