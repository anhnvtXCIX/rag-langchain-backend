import uuid
from pathlib import Path

import app.rag.pipeline as pipeline_module
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.rag.pipeline import process_document


async def _create_user_and_document(db_session, tmp_path: Path, content: bytes) -> int:
    unique = uuid.uuid4().hex[:8]
    user = User(
        username=f"pipeline_{unique}",
        email=f"pipeline_{unique}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    stored_path = tmp_path / "doc.txt"
    stored_path.write_bytes(content)

    document = Document(
        user_id=user.id,
        original_filename="doc.txt",
        stored_path=str(stored_path),
        file_size=len(content),
        status=DocumentStatus.pending,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document.id


async def test_process_document_success_sets_ready(
    db_session, test_session_maker, monkeypatch, tmp_path, fake_pipeline_rag
):
    monkeypatch.setattr(pipeline_module, "get_session_maker", lambda: test_session_maker)
    document_id = await _create_user_and_document(
        db_session, tmp_path, b"Some real content for extraction."
    )

    await process_document(document_id)

    refreshed = await db_session.get(Document, document_id)
    await db_session.refresh(refreshed)
    assert refreshed.status == DocumentStatus.ready


async def test_process_document_failure_sets_failed(
    db_session, test_session_maker, monkeypatch, tmp_path
):
    monkeypatch.setattr(pipeline_module, "get_session_maker", lambda: test_session_maker)

    async def _raise_add_chunks(chunks):
        raise RuntimeError("boom")

    async def _noop_delete_document_chunks(document_id: int) -> None:
        return None

    monkeypatch.setattr(pipeline_module, "add_chunks", _raise_add_chunks)
    monkeypatch.setattr(pipeline_module, "delete_document_chunks", _noop_delete_document_chunks)

    document_id = await _create_user_and_document(
        db_session, tmp_path, b"Content that will fail to embed."
    )

    await process_document(document_id)

    refreshed = await db_session.get(Document, document_id)
    await db_session.refresh(refreshed)
    assert refreshed.status == DocumentStatus.failed


async def test_process_document_missing_document_id_is_noop(
    db_session, test_session_maker, monkeypatch
):
    monkeypatch.setattr(pipeline_module, "get_session_maker", lambda: test_session_maker)

    await process_document(999999)  # should return without raising
