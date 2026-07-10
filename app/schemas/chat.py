from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime
