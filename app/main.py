from fastapi import FastAPI, APIRouter
import uvicorn
import firebase_admin
from firebase_admin import credentials, firestore
from routes.home import main_router

# Firestore 클라이언트 가져오기
# db = firestore.client()

# FastAPI 앱 생성
app = FastAPI()
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)