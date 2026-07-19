import uuid

import pytest

from app.core.config import get_settings
from app.models.user import User
from app.services.document_service import DocumentService, MissingFilenameError


class _FakeUploadFile:
    def __init__(self, filename, content_type: str = "text/plain", content: bytes = b"data"):
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self, _size: int) -> bytes:
        return self._content


async def test_upload_document_without_filename_raises(db_session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"docsvc_{unique}",
        email=f"docsvc_{unique}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = DocumentService(db_session, get_settings())

    with pytest.raises(MissingFilenameError):
        await service.upload_document(user_id=user.id, file=_FakeUploadFile(filename=""))

    with pytest.raises(MissingFilenameError):
        await service.upload_document(user_id=user.id, file=_FakeUploadFile(filename=None))
