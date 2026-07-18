from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    google_api_key: str | None = None
    upload_dir: str = "uploads"
    celery_broker_url: str | None = None
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "chroma_data"
    chroma_collection_name: str = "documents"
    gemini_chat_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    rag_top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
