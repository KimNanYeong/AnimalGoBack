from fastapi import APIRouter
from core.firebase import db

router = APIRouter()

@router.get("/get_metadata",tags=["create"],summary="외모,성격 특징 가져오기",description="외모,성격 특징을 가져옵니다")
async def get_appearance():
    collection = db.collection("appearance_traits").get()
    
    appearance_list = []
    for doc in collection:
        # print(doc.id)
        # print(doc.to_dict())
        appearance_list.append(doc.to_dict())
    print(collection)

    collection = db.collection("personality_traits").get()
    personality_list = []
    for doc in collection:
        # print(doc.id)
        # print(doc.to_dict())
        doc_dict = doc.to_dict()
        personality_list.append({
            "id" : doc_dict["id"],
            "name" : doc_dict['name'],
        })
    return {"result" : True, "appearance_list" : appearance_list, "personaliry_list" : personality_list}

# @router.get("/get_personality",tags=["create"],summary="성격 특징 가져오기",description="성격 특징을 가져옵니다")
# async def get_personality():
#     collection = db.collection("personality_traits").get()
#     personality_list = []
#     for doc in collection:
#         # print(doc.id)
#         # print(doc.to_dict())
#         doc_dict = doc.to_dict()
#         personality_list.append({
#             "id" : doc_dict["id"],
#             "name" : doc_dict['name'],
#         })
#         # personality_list.append(doc.to_dict())
#     print(collection)
#     return {"result" : True, "personality_list" : personality_list}

