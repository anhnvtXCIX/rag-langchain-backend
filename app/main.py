from fastapi import FastAPI

from app.logging_config import configure_app_logging, setup_logging
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router

app = FastAPI(title="rag-langchain API", version="0.1.0")

# Setup logging configuration
setup_logging()
configure_app_logging(app)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
