"""Конфигурация приложения.

Все секреты и настройки читаются из переменных окружения / файла .env
через pydantic-settings (см. .env.example).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Telegram ----------
    bot_token: str

    # ---------- LLM (Генерация ответов - DeepSeek) ----------
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # ---------- Embeddings (Векторизация - Ollama) ----------
    # По умолчанию направляем на контейнер ollama. В .env можно переопределить.
    embedding_api_key: str = "ollama"
    embedding_base_url: str = "http://ollama:11434/v1"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768  # ВАЖНО: у nomic-embed-text размерность 768, а не 1536!
    embedding_batch_size: int = 64

    # ---------- PostgreSQL ----------
    postgres_user: str = "rag"
    postgres_password: str = "rag"
    postgres_db: str = "rag"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # ---------- Qdrant ----------
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # ---------- RAG-пайплайн ----------
    chunk_size: int = 500  # токенов
    chunk_overlap: int = 50  # токенов
    top_k: int = 5
    max_pdf_size_mb: int = 20
    history_turns: int = 3  # сколько пар вопрос-ответ передаётся в контекст LLM

    # ---------- Приложение ----------
    log_level: str = "INFO"
    data_dir: Path = Path("data")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Синглтон настроек: чтение .env происходит один раз за процесс."""
    return Settings()
