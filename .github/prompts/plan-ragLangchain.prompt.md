## Plan: Complete RAG App Feature Checklist

> **Status (2026-07-19): Phases 1–2 complete; Phase 3 item 10 (automated tests) landed.** Next up: item 9 (rate limiting, stricter validation, DB pool tuning) and Phase 4 ops readiness. Mark items `[x]` as they land and update this line, so anyone (human or agent) can see at a glance what's done and what's next.

Deliver the app in four phases: first make all stubbed endpoints functional (auth, chat, documents), then add true RAG (embedding and retrieval), then harden security/performance, then finalize ops/deployment. This sequence minimizes blockers because chat/doc features depend on working auth and ownership checks.

### Phase 1 — MVP foundation ✅ complete

- [x] 1. Authentication and authorization: register/login with password hashing, JWT issuance/verification, and current-user dependency used by chat/document routes.
- [x] 2. Chat workflows: create/list sessions and create/list messages with ownership checks.
- [x] 3. Document workflows: file upload endpoint, metadata persistence, document listing, file validation (type/size), and baseline status transitions.
- [x] 4. Basic LLM response generation in chat: provider config, request handling, error fallback (503 when unconfigured), and assistant message persistence. *(Delivered as part of Phase 2 — went straight to the retrieval-augmented path.)*
- [ ] 5. API robustness: CORS middleware, global exception handling, standardized error responses. *(Request logging + correlation IDs are done via `app/logging_config.py`; CORS and a global exception handler are still missing from `app/main.py`.)*

### Phase 2 — RAG completion ✅ complete (2026-07-14)

- [x] 6. Document processing pipeline: extract text, chunking, embedding generation, and vector upsert; status pending/processing/ready/failed. *(`app/rag/pipeline.py`, FastAPI background task.)*
- [x] 7. Retrieval-augmented chat path: similarity retrieval (filtered by `user_id`), prompt context injection, and sources returned in message payload. *(`ChatService.send_message` + `app/rag/generation.py`.)*
- [x] 8. Complete document lifecycle: reprocess/update (`PUT` re-processes the stored file) and delete that also cleans vector entries.

### Phase 3 — Hardening ⬜ next

- [ ] 9. Rate limiting, stricter validation, ownership audits, and DB pool tuning (parallelizable items).
- [x] 10. Thorough automated tests: auth integration tests, chat/doc API tests, RAG retrieval assertions (fake embeddings/LLM), error-path tests, and multi-tenant ownership checks. *(`tests/`, `uv run pytest` — in-memory SQLite via `Base.metadata.create_all`, RAG call sites mocked at `app.services.chat_service.*`/`app.rag.pipeline.*`. Alembic migrations and real MySQL/Gemini/Chroma remain unexercised by this suite — still manual.)*

### Phase 4 — Ops readiness ⬜

- [ ] 11. Startup/readiness checks (`/health` exists but reports no dependency state), Docker Compose stack, CI pipeline (lint/type/test/build).

**Relevant files**
- `app/routers/auth.py`, `app/routers/chat.py`, `app/routers/documents.py` — implemented route handlers.
- `app/rag/` — RAG infrastructure: `extraction.py`, `chunking.py`, `vector_store.py`, `generation.py`, `pipeline.py`.
- `app/dependencies.py` — authenticated-user dependency and shared auth utilities.
- `app/config.py` — provider/vector settings (`GOOGLE_API_KEY`, `GEMINI_*`, `CHROMA_PERSIST_DIR`, `RAG_TOP_K`).
- `app/models/chat_session.py`, `app/models/message.py` (role/content/sources), `app/models/document.py` (status enum).
- `alembic/versions/e3c9721fe007_add_composite_descending_indexes.py` — preserve index strategy for chat listing performance.
- `pyproject.toml` — `pytest`/`pytest-asyncio`/`pytest-cov`/`aiosqlite`/`httpx` dev deps and `[tool.pytest.ini_options]`.
- `tests/` — `conftest.py` (SQLite-in-memory DB + RAG mocking fixtures), `routers/`, `services/`, `rag/`.
- `README.md`, `CLAUDE.md` — current env vars, setup, and endpoint behavior (kept in sync as of 2026-07-14).

**Verification**
1. ✅ Auth smoke: register/login returns token; protected route rejects missing token and accepts valid token. *(2026-07-14)*
2. ✅ Chat flow: create session, send message, list messages, ownership isolation across two users. *(2026-07-14, isolation verified at vector level)*
3. ✅ Document flow: upload valid file, list files, status progression pending→processing→ready/failed. *(2026-07-14)*
4. ✅ RAG flow: upload and process document, grounded question returns source references; delete cleans vectors. *(2026-07-14 — with faked Google models; real-key run still pending on `GOOGLE_API_KEY` being set in `.env`)*
5. 🟡 Stability checks: invalid payloads return structured 4xx, not 500 — covered by `tests/` for auth/chat/document error paths. ⬜ Error logs containing request context is still unverified by tests.
6. ⬜ Performance baseline: paginate large lists and verify indexed queries are used.
7. ⬜ Release checks: run migrations on clean DB, start stack, health/readiness endpoints report dependency state.

**Decisions**
- Included scope: backend completion of auth/chat/document/RAG plus minimum production hardening.
- Excluded scope for now: frontend UI work, advanced account management (password reset UX), multi-tenant org features.
- Sequencing rule: no RAG integration before auth and ownership checks are active.
- **Resolved 2026-07-14:** LLM provider = Google Gemini (`gemini-2.5-flash-lite` chat, `gemini-embedding-001` embeddings). Background processing = FastAPI `BackgroundTasks` in-process (Celery swap kept easy: task takes only a document id). Vector store = embedded Chroma (`CHROMA_PERSIST_DIR`). Storage = local disk (revisit object storage before production rollout).
