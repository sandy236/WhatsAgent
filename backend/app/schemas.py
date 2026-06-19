from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class MessageCreate(BaseModel):
    conversation_id: Optional[int]
    role: str
    content: str

class ChatRequest(BaseModel):
    conversation_id: Optional[int]
    prompt: str
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: List[Dict[str, str]] = []

class DocumentRecord(BaseModel):
    id: int
    title: str
    source: str
    doc_type: str
    url: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class ApiEntrySchema(BaseModel):
    id: Optional[int]
    name: str
    url: HttpUrl
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None

class SettingSchema(BaseModel):
    key: str
    value: str

class StatsResponse(BaseModel):
    total_documents: int
    total_urls: int
    total_chats: int
    total_vectors: int

class UploadResponse(BaseModel):
    message: str
    document_id: int
