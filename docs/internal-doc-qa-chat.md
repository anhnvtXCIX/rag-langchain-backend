# Plan: Simple Chat App with RAG for Document Q&A

> **Status (2026-07-14):** Core app + RAG pipeline are implemented. This file records the original product intent; where the implementation deliberately deviates, see "As-built deviations" at the bottom — the code and `CLAUDE.md` are the source of truth for current behavior.

## Business Requirements

**Target users:** Internal team / employees (knowledge base assistant)

**Authentication:** Required — users must log in

**Document types supported:**
- Word documents (.docx)
- Plain text / Markdown

**Document scope:** Per-user — each user manages and queries their own private documents

**Document management:**
- Upload documents
- List / view uploaded documents
- Delete documents
- Re-upload / update a document

**Chat behavior:**
- Multi-turn conversations (memory within a session)
- Answers include source attribution (which document/section the answer came from)
- Chat sessions persist across logins (users can return to past conversations)

**Scale:** Medium — 10–100 users, tens of documents per user

---

**Additional constraints:**
- No admin role — all users are peers
- File size limit: up to 5 MB per upload
- LLM provider: Google Gemini 2.5 Flash Lite

---

## Tech Stack

| Layer | Choice |
|---|---|
| API service | Python FastAPI |
| RAG framework | LangChain |
| LLM | Google Gemini 2.5 Flash Lite |
| Embedding model | Google text-embedding-004 |
| Vector DB | Chroma (server mode, Docker) |
| Relational DB | MySQL (Docker) |
| Message broker | RabbitMQ (Docker) |
| Background tasks | Celery |
| File storage | Local folder (Docker bind-mount) |
| Auth | JWT (username + password → token) |
| Frontend | None — API only |
| Infrastructure | Docker Compose |
| Python package and project manager | uv |

---

## Architecture

### Services (Docker Compose)

- `api` — FastAPI application
- `worker` — Celery worker (shares codebase with `api`)
- `mysql` — relational data (users, documents metadata, chat sessions/messages)
- `rabbitmq` — message broker between API and Celery worker
- `chromadb` — vector store (Chroma server mode)
- `uploads/` — bind-mounted local volume, structured as `uploads/{user_id}/{doc_id}/`

### Key Flows

#### Auth
- `POST /auth/register` — create user, store hashed password in MySQL
- `POST /auth/login` — validate credentials, return JWT token

#### Document Upload
1. `POST /documents/upload` — receive file, validate type (`.docx`, `.txt`, `.md`) and size (≤ 5 MB), save to `uploads/{user_id}/{doc_id}/`, insert MySQL record (`status: pending`), publish Celery task
2. Celery worker: parse document → chunk text → embed with Google text-embedding-004 → store vectors in Chroma (tagged with `user_id` + `doc_id` metadata) → update MySQL record (`status: ready`)

#### Document Management
- `GET /documents` — list user's documents (MySQL, filtered by `user_id`)
- `DELETE /documents/{id}` — remove from MySQL, delete vectors from Chroma, delete file from disk
- `PUT /documents/{id}` — replace file, delete old Chroma vectors, re-trigger processing pipeline

#### Chat
- `POST /chat/sessions` — create a new chat session (MySQL)
- `POST /chat/sessions/{id}/messages` — receive user message → retrieve top-k relevant chunks from Chroma (filtered by `user_id`) → build prompt with LangChain (include prior messages for multi-turn context) → call Gemini 2.5 Flash Lite → return answer with source attribution (document name + chunk reference) → persist user message and assistant reply to MySQL
- `GET /chat/sessions` — list user's past sessions
- `GET /chat/sessions/{id}/messages` — load full message history of a session

---

## As-built deviations (2026-07-14)

The implementation intentionally differs from the spec above in these ways:

| Spec above | As built | Why |
|---|---|---|
| 5 MB upload limit; `.docx`/`.txt`/`.md` | **10 MB**; also **`.pdf`** | Broader early-phase support |
| Embedding: `text-embedding-004` | **`gemini-embedding-001`** (`GEMINI_EMBEDDING_MODEL`) | text-embedding-004 retired by Google (Jan 2026) |
| Celery worker + RabbitMQ | **FastAPI `BackgroundTasks`** (in-process) | No extra infra for lab scale; `process_document(document_id)` keeps a Celery-compatible signature for a later swap |
| Chroma server mode (Docker) | **Embedded Chroma** (`PersistentClient`, `CHROMA_PERSIST_DIR`) | Zero extra processes in dev; `CHROMA_HOST`/`PORT` settings kept for a future switch |
| Files at `uploads/{user_id}/{doc_id}/` | Flat `uploads/{user_id}_{uuid}{ext}` | Simpler; path stored on the DB row |
| `PUT /documents/{id}` replaces the file | **Re-processes the existing file** (retry/re-index; no new file accepted) | "Replace" = upload new + delete old; PUT doubles as recovery for `failed` docs |
| Chat returns the answer | Returns **both** persisted messages (`ChatTurnResponse`: `user_message` + `assistant_message` with `sources`) | Client gets server-assigned ids/timestamps without a re-fetch |
| Docker Compose stack | **Not yet built** (dev runs `uv run fastapi dev` + local MySQL) | Deferred to ops phase |
