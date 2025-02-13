from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    sender: str
    content: str
    timestamp: str

class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: List[ChatMessage]
