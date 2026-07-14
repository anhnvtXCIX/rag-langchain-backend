from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Changing these invalidates existing vectors: all documents must be
# re-processed after a change, so they are constants rather than settings.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(
    text: str,
    *,
    user_id: int,
    document_id: int,
    filename: str,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    # user_id enables per-user retrieval filtering; document_id enables
    # vector cleanup when a document is deleted or re-processed.
    metadata = {
        "user_id": user_id,
        "document_id": document_id,
        "filename": filename,
    }
    return [
        Document(page_content=chunk, metadata=dict(metadata))
        for chunk in splitter.split_text(text)
    ]
