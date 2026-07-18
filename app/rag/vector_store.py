from functools import lru_cache

import anyio
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import get_settings
from app.rag.errors import LLMNotConfiguredError


@lru_cache
def get_chroma_client():
    # Must be a process-wide singleton: multiple PersistentClients against
    # the same path can conflict.
    return chromadb.PersistentClient(path=get_settings().chroma_persist_dir)


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    # Falsy check: .env files often leave GOOGLE_API_KEY= empty rather than
    # omitting it, which yields "" instead of None.
    if not settings.google_api_key:
        raise LLMNotConfiguredError
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
    )


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    return Chroma(
        client=get_chroma_client(),
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
    )


async def add_chunks(chunks: list[Document]) -> None:
    await get_vector_store().aadd_documents(chunks)


async def search_chunks(query: str, *, user_id: int, k: int) -> list[Document]:
    return await get_vector_store().asimilarity_search(
        query, k=k, filter={"user_id": user_id}
    )


async def delete_document_chunks(document_id: int) -> None:
    # langchain_chroma.Chroma.delete only accepts ids, so drop to the raw
    # collection to delete by metadata filter. Both the collection lookup
    # and the delete hit the on-disk Chroma backend, so the whole sequence
    # runs off the event loop, not just the delete call.
    def _delete() -> None:
        collection = get_chroma_client().get_or_create_collection(
            get_settings().chroma_collection_name
        )
        collection.delete(where={"document_id": document_id})

    await anyio.to_thread.run_sync(_delete)  # pyright: ignore[reportAttributeAccessIssue]
