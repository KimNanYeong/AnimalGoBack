from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import os
import uuid
# from app.core.firebase import db
from core.firebase import db
from firebase_admin import firestore

router = APIRouter()

# 🔹 서버에 이미지 저장할 폴더 경로
ORIGINALS_FOLDER = r"C:\animal-storage\originals"
os.makedirs(ORIGINALS_FOLDER, exist_ok=True)

class ImageUploadResponse(BaseModel):
    imageId: str = Field(..., example="originals001")
    filePath: str = Field(..., example="./server-storage/originals/f59bdbbf.png")
    message: str = Field(..., example="Original image stored successfully on the server!")

@router.post("/upload-original-image", response_model=ImageUploadResponse)
async def upload_original_image(user_id: str, file: UploadFile = File(...)):
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(ORIGINALS_FOLDER, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        image_ref = db.collection("collected_images").document()
        image_ref.set({
            "userId": user_id,
            "filePath": file_path,
            "uploadedAt": firestore.SERVER_TIMESTAMP,
            "status": "pending"
        })

        return {"imageId": image_ref.id, "filePath": file_path, "message": "Original image stored successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
