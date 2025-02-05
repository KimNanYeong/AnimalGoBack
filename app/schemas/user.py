from pydantic import BaseModel

class UserCreate(BaseModel):
    user_id: str
    name: str
    email: str

class UserUpdate(BaseModel):
    name: str = None
    email: str = None
