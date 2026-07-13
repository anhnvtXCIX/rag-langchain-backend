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
 config.py             # Environment-based settings
 database.py           # Async engine/session dependency
 dependencies.py       # Auth + DB dependencies
 models/               # SQLAlchemy models
 routers/              # API endpoints
 schemas/              # Request/response schemas
 services/             # Business logic
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
- `GOOGLE_API_KEY` (optional)
- `UPLOAD_DIR` (default: `uploads`)
- `CELERY_BROKER_URL` (optional)
- `CHROMA_HOST` (default: `localhost`)
- `CHROMA_PORT` (default: `8001`)

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

## Notes

- Current chat endpoint stores only user messages; assistant generation is not implemented yet.
- Document vectorization/embedding steps are marked as TODO in document routes.
