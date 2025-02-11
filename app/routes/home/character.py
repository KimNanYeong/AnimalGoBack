from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import os
import uuid
from app.core.firebase import db
from firebase_admin import firestore

router = APIRouter()

# 🔹 변환된 캐릭터 이미지를 저장할 폴더 경로
CHARACTERS_FOLDER = r"C:\animal-storage\characters"
os.makedirs(CHARACTERS_FOLDER, exist_ok=True)

class CharacterUploadResponse(BaseModel):
    characterId: str = Field(..., example="char123")
    nickname: str = Field(..., example="Brave Fox")
    filePath: str = Field(..., example="./server-storage/characters/transformed_abc.png")
    typesOfAnimals: str = Field(..., example="Fox")
    appearances: str = Field(..., example="Golden fur, blue eyes")
    fundamentals: str = Field(..., example="Brave and fast")
    message: str = Field(..., example="Character image stored successfully!")

@router.post("/upload-character-image", response_model=CharacterUploadResponse)
async def upload_character_image(
    user_id: str,
    nickname: str,
    original_image_id: str,
    types_of_animals: str,
    appearances: str,
    fundamentals: str,
    file: UploadFile = File(...)
):
    try:
        original_image_doc = db.collection("collected_images").document(original_image_id).get()
        if not original_image_doc.exists:
            raise HTTPException(status_code=404, detail="Original image not found")

        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(CHARACTERS_FOLDER, unique_filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        char_ref = db.collection("characters").document()
        char_ref.set({
            "userId": user_id,
            "nickname": nickname,
            "originalImageId": original_image_id,
            "filePath": file_path,
            "typesOfAnimals": types_of_animals,
            "appearances": appearances,
            "fundamentals": fundamentals,
            "uploadedAt": firestore.SERVER_TIMESTAMP
        })

        return {
            "characterId": char_ref.id,
            "nickname": nickname,
            "filePath": file_path,
            "typesOfAnimals": types_of_animals,
            "appearances": appearances,
            "fundamentals": fundamentals,
            "message": "Character image stored successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
