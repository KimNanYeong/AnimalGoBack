from fastapi import APIRouter, HTTPException
from core.firebase import db
import logging

# ✅ 로깅 설정
logging.basicConfig(filename='log/create_router.log', level=logging.DEBUG)

router = APIRouter()

@router.get("/get_metadata", tags=["create"], summary="외모,성격 특징 가져오기", description="외모,성격 특징을 가져옵니다")
async def get_appearance():
    logging.info("Request received to get metadata")

    try:
        collection = db.collection("appearance_traits").get()
        appearance_list = []
        for doc in collection:
            appearance_list.append(doc.to_dict())
        logging.info(f"Appearance traits retrieved: {appearance_list}")

        collection = db.collection("personality_traits").get()
        personality_list = []
        for doc in collection:
            doc_dict = doc.to_dict()
            personality_list.append({
                "id": doc_dict["id"],
                "name": doc_dict['name'],
            })
        logging.info(f"Personality traits retrieved: {personality_list}")

        response = {"result": True, "appearance_list": appearance_list, "personaliry_list": personality_list}
        logging.info(f"Response: {response}")
        return response

    except Exception as e:
        logging.error(f"Error retrieving metadata: {str(e)}")
        raise HTTPException(status_code=500, detail="Metadata retrieval failed")

