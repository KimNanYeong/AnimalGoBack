from fastapi import FastAPI
import uvicorn
import firebase_admin
from firebase_admin import credentials, firestore
from routes.home import main_router  # 🔹 home.py에서 router만 가져오기

# FastAPI 앱 생성
app = FastAPI(title="FastAPI with Firestore")
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)