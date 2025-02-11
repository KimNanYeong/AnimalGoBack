from fastapi import FastAPI, APIRouter
import uvicorn
from core.firebase import db
from routes.home import main_router
from routes.user import router as user_router

# FastAPI 앱 생성
app = FastAPI()
app.include_router(main_router)
app.include_router(user_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)