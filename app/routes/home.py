#from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, HTTPException, UploadFile, File
#from pydantic import BaseModel
from pydantic import BaseModel, Field
import firebase_admin
from firebase_admin import credentials, firestore, auth  # 🔹 auth 모듈 추가
import bcrypt  # 🔹 bcrypt 라이브러리 추가

from pydantic import BaseModel

import socket
import os


# Firebase 초기화 (중복 방지)
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/blueback/app/core/fbstorekey.json")
    firebase_admin.initialize_app(cred)

# Firestore 클라이언트
db = firestore.client()

# FastAPI 라우터
main_router = APIRouter()



# ==========================
# 🔹 서버 정보 응답 모델
# ==========================
class ServerInfoResponse(BaseModel):
    ip_address: str
    message: str


# =============================
# 🔹 현재 개발용 PC 서버의 IP 주소 가져오기
# =============================
def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        return "Unknown"


# ===========================
# 🔹 원본 동물 이미지 저장 API (임시방법)
# ===========================

# 🔹 서버에 이미지 저장할 폴더 경로
# ORIGINALS_FOLDER = "./server-storage/originals"
ORIGINALS_FOLDER = r"C:\animal-storage\originals"

# 🔹 폴더가 없으면 생성
os.makedirs(ORIGINALS_FOLDER, exist_ok=True)
# 🔹 응답 모델 정의
class ImageUploadResponse(BaseModel): #예제 응답
    imageId: str  = Field(..., example="originals001")
    filePath: str = Field(..., example="./server-storage/originals\\f59bdbbf-a9ee-4550-8eaf-f9859821b4b6.png")
    message: str  = Field(..., example="Original image stored successfully on the server")

# ===========================
# 🔹 동물 캐릭터 저장 API (임시방법)
# ===========================

# 🔹 변환된 캐릭터 이미지를 저장할 폴더 경로
#CHARACTERS_FOLDER = "./server-storage/characters"
CHARACTERS_FOLDER = r"C:\animal-storage\characters"

# 🔹 폴더가 없으면 생성
os.makedirs(CHARACTERS_FOLDER, exist_ok=True)

# 🔹 응답 모델 정의 (추가 필드 포함)
class CharacterUploadResponse(BaseModel):
    characterId: str = Field(..., example="char123")
    nickname: str = Field(..., example="Brave Fox") 
    filePath: str = Field(..., example="./server-storage/characters/transformed_abc.png")
    typesOfAnimals: str = Field(..., example="Fox")
    appearances: str = Field(..., example="Golden fur, blue eyes")
    fundamentals: str = Field(..., example="Brave and fast")
    message: str = Field(..., example="Character image stored successfully on the server!")



# ==========================
# 🔹 기본 API 엔드포인트 (테스트용)
# ==========================
@main_router.get("/")
def read_root():
    """ 기본 API 엔드포인트 - 서버 정상 동작 확인용 """
    return {"message": "Hello, FastAPI!"}


# 🔹 Firestore에 개발용 서버 IP 주소 저장
@main_router.post("/register-server-ip", 
             summary="개발용 서버 IP 등록",
             description="FastAPI 실행 중인 서버의 IP 주소를 Firestore에 저장하는 API",
             response_model=ServerInfoResponse)

def register_server_ip():
    try:
        server_ip = get_local_ip()

        # Firestore에 서버 IP 저장
        server_ref = db.collection("server_info").document("development_pc")
        server_ref.set({
            "ip_address": server_ip,
            "registeredAt": firestore.SERVER_TIMESTAMP
        })

        return {"ip_address": server_ip, "message": "Server IP registered successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# =======================================
# 🔹 Firestore에서 개발용 서버 IP 조회 API
# =======================================
@main_router.get("/get-server-ip", 
            summary="개발용 서버 IP 조회",
            description="Firestore에 저장된 개발용 서버의 IP 주소를 가져오는 API",
            response_model=ServerInfoResponse)
def get_server_ip():
    try:
        server_ref = db.collection("server_info").document("development_pc").get()
        if not server_ref.exists:
            raise HTTPException(status_code=404, detail="Server IP not registered")

        server_data = server_ref.to_dict()
        return {"ip_address": server_data["ip_address"], "message": "Server IP retrieved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# 🔹 원본 이미지 저장 API (임시용)
# ===========================
@main_router.post("/upload-original-image", 
             summary="개발 서버에 원본 동물 이미지 저장",
             description="사용자가 업로드한 동물 이미지를 개발용 서버에 저장하고 Firestore에 저장 위치를 기록하는 API",
             response_model=ImageUploadResponse)  # 응답 모델 적용
async def upload_original_image(user_id: str, file: UploadFile = File(...)):
    try:
        # 🔹 고유 파일명 생성
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(ORIGINALS_FOLDER, unique_filename)

        # 🔹 파일 저장
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # 🔹 Firestore에 저장 위치 기록
        image_ref = db.collection("collected_images").document()
        image_ref.set({
            "userId": user_id,
            "filePath": file_path,  # 서버 내 파일 경로 저장
            "uploadedAt": firestore.SERVER_TIMESTAMP,
            "status": "pending"
        })

        return {"imageId": image_ref.id, "filePath": file_path, "message": "Original image stored successfully on the server!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
# ========================
# 🔹 생성 이미지 저장 API (임시용)
# ========================
@main_router.post("/upload-character-image", 
             summary="개발 서버에 변환된 캐릭터 이미지 저장",
             description="사용자가 변환한 캐릭터 이미지를 개발용 서버에 저장하고 Firestore에 저장 위치를 기록하는 API",
             response_model=CharacterUploadResponse)
async def upload_character_image(
    user_id: str, 
    nickname: str,  # 🔹 캐릭터_닉네임 
    original_image_id: str, 
    types_of_animals: str,  # 🔹 동물 종류 (예: "Fox", "Dog")
    appearances: str,  # 🔹 외형 정보 (예: "Golden fur, blue eyes")
    fundamentals: str,  # 🔹 기본 성격, 능력 (예: "Brave and fast")
    file: UploadFile = File(...)
):
    try:
        # 🔹 원본 이미지 Firestore에서 확인
        original_image_doc = db.collection("collected_images").document(original_image_id).get()
        if not original_image_doc.exists:
            raise HTTPException(status_code=404, detail="Original image not found")

        # 🔹 고유 파일명 생성
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(CHARACTERS_FOLDER, unique_filename)

        # 🔹 파일 저장
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # 🔹 Firestore에 캐릭터 저장 위치 기록
        char_ref = db.collection("characters").document()
        char_ref.set({
            "userId": user_id,
            "nickname": nickname,  # 🔹 닉네임 추가
            "originalImageId": original_image_id,
            "filePath": file_path,  # 서버 내 파일 경로 저장
            "typesOfAnimals": types_of_animals,  # 🔹 동물 종류 추가
            "appearances": appearances,  # 🔹 외형 추가
            "fundamentals": fundamentals,  # 🔹 기본 특성 추가
            "uploadedAt": firestore.SERVER_TIMESTAMP
        })

        return {
            "characterId": char_ref.id,
            "nickname": nickname, 
            "filePath": file_path,            
            "typesOfAnimals": types_of_animals,
            "appearances": appearances,
            "fundamentals": fundamentals,
            "message": "Character image stored successfully on the server!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
