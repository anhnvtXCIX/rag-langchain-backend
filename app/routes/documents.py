from fastapi import APIRouter, HTTPException

from app.schemas.document import DocumentResponse, DocumentUploadResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents() -> list[DocumentResponse]:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document() -> DocumentUploadResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: int) -> DocumentResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{document_id}")
async def delete_document(document_id: int) -> dict[str, str]:
    raise HTTPException(status_code=501, detail="Not implemented")
