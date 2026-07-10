from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    id: int
    original_filename: str
    status: str


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    stored_path: str
    file_size: int = Field(ge=0)
    status: str
    created_at: datetime
    updated_at: datetime
