import logging
from pathlib import Path

import anyio

from app.database import get_session_maker
from app.models.document import Document, DocumentStatus
from app.rag.chunking import chunk_text
from app.rag.extraction import extract_text
from app.rag.vector_store import add_chunks, delete_document_chunks

logger = logging.getLogger(__name__)


# Takes a primitive id (not an ORM instance) so this signature works
# unchanged as a Celery task if background processing is externalized later.
async def process_document(document_id: int) -> None:
    # Background tasks run after the response is sent, when the
    # request-scoped session from get_db() is already closed — so this
    # task owns its own session.
    async with get_session_maker()() as db:
        document = await db.get(Document, document_id)
        if document is None:
            return

        document.status = DocumentStatus.processing
        await db.commit()

        try:
            text: str = await anyio.to_thread.run_sync(  # pyright: ignore[reportAttributeAccessIssue]
                extract_text, Path(document.stored_path)
            )
            chunks = chunk_text(
                text,
                user_id=document.user_id,
                document_id=document.id,
                filename=document.original_filename,
            )
            # Clear stale vectors first so re-processing is idempotent.
            await delete_document_chunks(document.id)
            await add_chunks(chunks)
            document.status = DocumentStatus.ready
        except Exception:
            logger.exception(
                "Document processing failed", extra={"document_id": document_id}
            )
            document.status = DocumentStatus.failed

        await db.commit()
