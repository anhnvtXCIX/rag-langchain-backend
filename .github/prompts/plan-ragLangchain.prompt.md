## Plan: Complete RAG App Feature Checklist

Deliver the app in four phases: first make all stubbed endpoints functional (auth, chat, documents), then add true RAG (embedding and retrieval), then harden security/performance, then finalize ops/deployment. This sequence minimizes blockers because chat/doc features depend on working auth and ownership checks.

**Steps**
1. Phase 1 (MVP foundation): Implement all currently stubbed route handlers and core dependencies.
2. Implement authentication and authorization first (*blocks steps 3-6*): register/login with password hashing, JWT issuance/verification, and current-user dependency used by chat/document routes.
3. Implement chat workflows (*depends on 2*): create/list sessions and create/list messages with ownership checks and pagination limits.
4. Implement document workflows (*depends on 2*): file upload endpoint, metadata persistence, document listing, file validation (type/size), and baseline status transitions.
5. Add basic LLM response generation in chat (*depends on 3; parallel with 4 once auth is done*): provider config, request handling, error fallback, and assistant message persistence.
6. Add API robustness (*parallel with 3-5*): CORS middleware, global exception handling, standardized error responses, request logging.
7. Phase 2 (RAG completion): connect vector store and retrieval path.
8. Implement document processing pipeline (*depends on 4*): extract text, chunking, embedding generation, and vector upsert; update status pending/processing/ready/failed.
9. Implement retrieval-augmented chat path (*depends on 5 and 8*): similarity retrieval, prompt context injection, and sources returned in message payload.
10. Complete document lifecycle (*depends on 8*): reprocess/update and delete endpoints that also clean vector entries.
11. Phase 3 (Hardening): security, scale, and test depth.
12. Add rate limiting, stricter validation, ownership audits, and DB pool tuning (*parallelizable items*).
13. Add thorough automated tests (*depends on 2-10*): auth integration tests, chat/doc API tests, RAG retrieval assertions, error-path tests.
14. Phase 4 (Ops readiness): deployment and observability.
15. Add startup/readiness checks, container setup, and CI pipeline (lint/type/test/build) (*depends on stable implementation and tests*).

**Relevant files**
- /Users/anhnvt/projects/lab/rag-langchain/app/routes/auth.py — implement register/login handlers now returning 501.
- /Users/anhnvt/projects/lab/rag-langchain/app/routes/chat.py — implement session/message CRUD, ownership checks, pagination.
- /Users/anhnvt/projects/lab/rag-langchain/app/routes/documents.py — implement upload/list/update/delete behavior and status transitions.
- /Users/anhnvt/projects/lab/rag-langchain/app/dependencies.py — add authenticated-user dependency and shared auth utilities.
- /Users/anhnvt/projects/lab/rag-langchain/app/config.py — extend provider/vector/task settings and validation for required env vars.
- /Users/anhnvt/projects/lab/rag-langchain/app/models/chat_session.py — reuse ownership relation and updated_at indexing behavior.
- /Users/anhnvt/projects/lab/rag-langchain/app/models/message.py — reuse message role/content/sources structure for assistant output + citations.
- /Users/anhnvt/projects/lab/rag-langchain/app/models/document.py — reuse status enum transitions for processing pipeline.
- /Users/anhnvt/projects/lab/rag-langchain/alembic/versions/e3c9721fe007_add_composite_descending_indexes.py — preserve index strategy for chat listing performance.
- /Users/anhnvt/projects/lab/rag-langchain/pyproject.toml — add runtime/test/tooling dependencies.
- /Users/anhnvt/projects/lab/rag-langchain/README.md — document env vars, setup, and endpoint behavior.

**Verification**
1. Auth smoke: register/login returns token; protected route rejects missing token and accepts valid token.
2. Chat flow: create session, send message, list messages, and confirm ownership isolation across two users.
3. Document flow: upload valid file, reject invalid type/oversize file, list files, and verify status progression.
4. RAG flow: upload and process document, then ask a grounded question and confirm source references in response.
5. Stability checks: invalid payloads return structured 4xx (not 500), error logs contain request context.
6. Performance baseline: paginate large lists and verify indexed queries are used.
7. Release checks: run migrations on clean DB, start stack, health/readiness endpoints report dependency state.

**Decisions**
- Included scope: backend completion of auth/chat/document/RAG plus minimum production hardening.
- Excluded scope for now: frontend UI work, advanced account management (password reset UX), multi-tenant org features.
- Sequencing rule: no RAG integration before auth and ownership checks are active.

**Further Considerations**
1. LLM provider choice should be fixed early (OpenAI vs Anthropic vs self-hosted) because it affects prompting, retries, and cost controls.
2. Background processing choice (Celery/Redis vs lightweight in-process jobs) should align with deployment target and expected document volume.
3. Storage target (local disk vs object storage) should be finalized before production rollout to avoid migration of file paths later.
