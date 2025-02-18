from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DETAILS = "mongodb://localhost:27017"  # MongoDB URI
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.my_database  # 데이터베이스 이름
collection = database.my_collection  # 컬렉션 이름