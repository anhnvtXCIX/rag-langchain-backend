import os
import tempfile

# These must be set before any `app.*` import triggers Settings() construction
# (get_settings() is @lru_cache'd module-level in app/core/config.py).
os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://unused:unused@localhost/unused")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="rag_test_uploads_"))
# Explicit empty string (not a pop/unset) so this wins over a real GOOGLE_API_KEY
# that may be set in the developer's .env file — pydantic-settings gives OS env
# vars precedence over .env values, but only if the OS env var is actually present.
os.environ["GOOGLE_API_KEY"] = ""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.rag.pipeline as pipeline_module
from app.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    # StaticPool: a single shared connection so the in-memory SQLite DB is
    # visible across the app's session, the background pipeline task's own
    # session, and the test's own db_session fixture.
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def test_session_maker(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(test_session_maker) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session_maker, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # app/rag/pipeline.py's process_document() calls get_session_maker()
    # directly, bypassing get_db() — so the dependency override above does
    # not redirect the background document-processing task to the test DB.
    # BackgroundTasks run synchronously as part of ASGITransport request
    # handling, so this must be patched unconditionally for every test.
    monkeypatch.setattr(
        pipeline_module, "get_session_maker", lambda: test_session_maker
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict[str, Any]:
    unique = uuid.uuid4().hex[:8]
    payload = {
        "username": f"user_{unique}",
        "email": f"user_{unique}@example.com",
        "password": "supersecret1",
    }
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    return {**payload, "access_token": resp.json()["access_token"]}


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient, registered_user: dict[str, Any]
) -> AsyncClient:
    client.headers.update(
        {"Authorization": f"Bearer {registered_user['access_token']}"}
    )
    return client


@pytest.fixture
def fake_rag(monkeypatch):
    """Patch the RAG call sites as bound inside app.services.chat_service.

    chat_service imports generate_answer/get_chat_model/get_embeddings/
    search_chunks by name, so patching app.rag.generation/app.rag.vector_store
    directly would not affect chat_service's already-bound references.
    """
    import app.services.chat_service as chat_service_module

    monkeypatch.setattr(chat_service_module, "get_chat_model", lambda: object())
    monkeypatch.setattr(chat_service_module, "get_embeddings", lambda: object())

    async def _fake_search_chunks(
        query: str, *, user_id: int, k: int
    ) -> list[LCDocument]:
        return [
            LCDocument(
                page_content="Fake retrieved chunk content.",
                metadata={"document_id": 1, "filename": "fake.txt", "user_id": user_id},
            )
        ]

    async def _fake_generate_answer(question, context_chunks, history) -> str:
        return "This is a fake generated answer."

    monkeypatch.setattr(chat_service_module, "search_chunks", _fake_search_chunks)
    monkeypatch.setattr(chat_service_module, "generate_answer", _fake_generate_answer)


@pytest.fixture
def fake_pipeline_rag(monkeypatch):
    """Patch add_chunks/delete_document_chunks at every place they're bound
    (app.rag.pipeline for the background processing task, and
    app.services.document_service for the DELETE endpoint's own call), so
    document uploads/deletes never touch a real Chroma/Gemini embedding call.
    """
    import app.services.document_service as document_service_module

    async def _noop_add_chunks(chunks) -> None:
        return None

    async def _noop_delete_document_chunks(document_id: int) -> None:
        return None

    monkeypatch.setattr(pipeline_module, "add_chunks", _noop_add_chunks)
    monkeypatch.setattr(
        pipeline_module, "delete_document_chunks", _noop_delete_document_chunks
    )
    monkeypatch.setattr(
        document_service_module, "delete_document_chunks", _noop_delete_document_chunks
    )
