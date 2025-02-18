from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()
class MongoDB:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URL")
        self.db_name = os.getenv("MONGODB_NAME")
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """MongoDB와 연결을 설정합니다."""
        print("""MongoDB와 연결을 설정합니다.""")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client[self.db_name]

    async def close(self):
        """MongoDB와의 연결을 종료합니다."""
        print( """MongoDB와의 연결을 종료합니다.""")
        self.client.close()

    def get_db(self):
        """연결된 데이터베이스 인스턴스를 반환합니다."""
        return self.db

mongo = MongoDB()

async def connect_to_mongo():
    await mongo.connect()

async def close_mongo_connection():
    await mongo.close()