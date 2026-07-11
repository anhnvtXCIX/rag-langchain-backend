from pathlib import Path
from uuid import uuid4

import anyio
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.document import Document, DocumentStatus

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/markdown",
    "text/markdown",
    "text/plain",
}


class MissingFilenameError(Exception):
    pass


class UnsupportedFileExtensionError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class DocumentTooLargeError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class DocumentService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def list_documents(self, user_id: int) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def upload_document(self, user_id: int, file: UploadFile) -> Document:
        if not file.filename:
            raise MissingFilenameError

        suffix = Path(file.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileExtensionError
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedFileTypeError

        content = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise DocumentTooLargeError

        upload_dir = Path(self.settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        stored_path = upload_dir / f"{user_id}_{uuid4().hex}{suffix}"
        await anyio.to_thread.run_sync(stored_path.write_bytes, content)  # pyright: ignore[reportAttributeAccessIssue]

        document = Document(
            user_id=user_id,
            original_filename=file.filename,
            stored_path=str(stored_path),
            file_size=len(content),
            status=DocumentStatus.pending,
        )

        try:
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
        except Exception:
            if await anyio.to_thread.run_sync(stored_path.exists):  # pyright: ignore[reportAttributeAccessIssue]
                await anyio.to_thread.run_sync(stored_path.unlink)  # pyright: ignore[reportAttributeAccessIssue]
            raise

        return document

    async def update_document(self, document_id: int, user_id: int) -> Document:
        document = await self._get_owned_document(
            document_id=document_id, user_id=user_id
        )
        document.status = DocumentStatus.pending
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def delete_document(self, document_id: int, user_id: int) -> None:
        document = await self._get_owned_document(
            document_id=document_id, user_id=user_id
        )

        stored_path = Path(document.stored_path)
        if await anyio.to_thread.run_sync(stored_path.exists):  # pyright: ignore[reportAttributeAccessIssue]
            await anyio.to_thread.run_sync(stored_path.unlink)  # pyright: ignore[reportAttributeAccessIssue]

        await self.db.delete(document)
        await self.db.commit()

    async def _get_owned_document(self, document_id: int, user_id: int) -> Document:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError
        return document
