# rag-langchain

FastAPI backend skeleton for a retrieval-augmented generation (RAG) chat service.

This project currently provides:

- JWT-based authentication
- User-scoped chat sessions and messages
- User-scoped document upload/list/update/delete
- Async SQLAlchemy with MySQL
- Alembic migrations
- Structured request logging with correlation IDs

## Tech Stack

- Python 3.13+
- FastAPI
- SQLAlchemy 2.x (async)
- Alembic
- MySQL (via `aiomysql`)

## Project Structure

```text
app/
 main.py               # FastAPI app entrypoint
 database.py           # Async engine/session dependency
 dependencies.py       # Auth + DB dependencies
 models/               # SQLAlchemy models
 routers/              # API endpoints
 schemas/              # Request/response schemas
 services/             # Business logic
 core/                 # Core configs
alembic/
 versions/             # Database migrations
```

## Prerequisites

- Python 3.13+
- MySQL 8+
- `uv` package manager (recommended)

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

1. Create and sync environment:

```bash
uv sync
```

2. Copy environment template and adjust values:

```bash
cp .env.example .env
```

3. Create database (example):

```sql
CREATE DATABASE rag_langchain;
```

4. Apply migrations:

```bash
uv run alembic upgrade head
```

5. Run development server:

```bash
uv run fastapi dev
```

API becomes available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/health`

## Environment Variables

The app loads variables from `.env` via Pydantic settings.

Required:

- `DATABASE_URL`
- `JWT_SECRET_KEY`

Application settings:

- `JWT_ALGORITHM` (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: `60`)
- `GOOGLE_API_KEY` (required for RAG chat and document vectorization; without it, uploads fail processing and chat returns 503)
- `UPLOAD_DIR` (default: `uploads`)
- `CELERY_BROKER_URL` (optional, unused)
- `CHROMA_HOST` (default: `localhost`, unused — Chroma runs embedded)
- `CHROMA_PORT` (default: `8001`, unused — Chroma runs embedded)
- `CHROMA_PERSIST_DIR` (default: `chroma_data`)
- `CHROMA_COLLECTION_NAME` (default: `documents`)
- `GEMINI_CHAT_MODEL` (default: `gemini-2.5-flash-lite`)
- `GEMINI_EMBEDDING_MODEL` (default: `gemini-embedding-001`; changing it later invalidates existing vectors — delete `chroma_data/` and re-process documents via `PUT /documents/{id}`)
- `RAG_TOP_K` (default: `4`)

Logging settings:

- `ENV` (`dev` or `prod`, default: `dev`)
- `LOG_JSON` (`true/false`, optional; forced on when `ENV=prod`)
- `LOG_LEVEL` (default: `INFO`)

## API Overview

### Auth

- `POST /auth/register`
- `POST /auth/login`

Both return a bearer token:

```json
{
 "access_token": "<jwt>",
 "token_type": "bearer"
}
```

### Chat (requires Authorization header)

- `POST /chat/sessions`
- `GET /chat/sessions`
- `GET /chat/sessions/{session_id}/messages`
- `POST /chat/sessions/{session_id}/messages`

### Documents (requires Authorization header)

- `GET /documents`
- `POST /documents/upload` (multipart form field: `file`)
- `PUT /documents/{document_id}`
- `DELETE /documents/{document_id}`

Upload constraints:

- Max file size: 10 MB
- Allowed extensions: `.txt`, `.md`, `.pdf`, `.docx`
- Allowed MIME types: `text/plain`, `text/markdown`, `application/markdown`, `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

## Example Requests

Register:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
 -H "Content-Type: application/json" \
 -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'
```

Create a chat session:

```bash
curl -X POST http://127.0.0.1:8000/chat/sessions \
 -H "Authorization: Bearer <token>" \
 -H "Content-Type: application/json" \
 -d '{"title":"My first session"}'
```

Upload a document:

```bash
curl -X POST http://127.0.0.1:8000/documents/upload \
 -H "Authorization: Bearer <token>" \
 -F "file=@./notes.md"
```

## Migrations

Create a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe_change"
```

Apply latest migrations:

```bash
uv run alembic upgrade head
```

Check current migration status:

```bash
uv run alembic current
uv run alembic history
```

## RAG Pipeline

- Uploaded documents are processed in a FastAPI background task: text is extracted (`pypdf` / `python-docx` / plain text), chunked with LangChain's `RecursiveCharacterTextSplitter`, embedded with Google `gemini-embedding-001`, and stored in an embedded Chroma database (`CHROMA_PERSIST_DIR`). Document `status` moves `pending -> processing -> ready` (or `failed`; check the logs).
- `PUT /documents/{document_id}` re-processes the stored file (use it to retry a `failed` document). `DELETE` also removes the document's vectors.
- `POST /chat/sessions/{session_id}/messages` retrieves the top-k chunks from the caller's own documents, sends them with recent session history to Gemini, and returns both the persisted user message and the assistant reply with `sources` (document id, filename, snippet). Returns `503` if `GOOGLE_API_KEY` is not set.

## Notes

- Background processing is in-process (no Celery yet); a document stuck in `processing` after a restart can be re-processed with `PUT /documents/{document_id}`.
