from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.dependencies import CurrentUserDep, DbSessionDep
from app.models.document import Document
from app.rag.pipeline import process_document
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentTooLargeError,
    MissingFilenameError,
    UnsupportedFileExtensionError,
    UnsupportedFileTypeError,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def _document_to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        stored_path=document.stored_path,
        file_size=document.file_size,
        status=document.status.value,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[DocumentResponse]:
    service = DocumentService(db, get_settings())
    documents = await service.list_documents(user_id=current_user.id)
    return [_document_to_response(document) for document in documents]


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    service = DocumentService(db, get_settings())
    try:
        document = await service.upload_document(user_id=current_user.id, file=file)
    except MissingFilenameError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required"
        ) from exc
    except UnsupportedFileExtensionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file extension"
        ) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type"
        ) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the size limit",
        ) from exc

    background_tasks.add_task(process_document, document.id)

    return DocumentUploadResponse(
        id=document.id,
        original_filename=document.original_filename,
        status=document.status.value,
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    service = DocumentService(db, get_settings())
    try:
        document = await service.update_document(
            document_id=document_id,
            user_id=current_user.id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc
    background_tasks.add_task(process_document, document.id)
    return _document_to_response(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> dict[str, str]:
    service = DocumentService(db, get_settings())
    try:
        await service.delete_document(document_id=document_id, user_id=current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc
    # TODO: Consider implementing a background task to delete the vectorized documents asynchronously if needed.
    return {"detail": "Document deleted"}
