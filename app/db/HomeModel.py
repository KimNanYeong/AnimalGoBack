from core.Mongo import mongo



async def get_user_by_id(user_id:str):
    db = mongo.get_db()
    collection = db['users']
    user = await collection.find_one({"user_id":user_id})
    return user
    # collection = mongo.get_db()
    # user = await collection.find_one({"id":user_id})
    # return user