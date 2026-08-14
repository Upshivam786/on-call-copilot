"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    LOG_LEVEL: str = Field(default="INFO")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://oncall:oncall_dev_password@localhost:5432/oncall_copilot"
    )
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_TTL: int = Field(default=3600, description="Session TTL in seconds")

    # OpenAI / LLM
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_DIMENSIONS: int = Field(default=1536)
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_MAX_TOKENS: int = Field(default=2000)

    # Observability
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None)
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None)
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com")
    ENABLE_TRACING: bool = Field(default=False)

    # External integrations
    PAGERDUTY_API_KEY: Optional[str] = Field(default=None)
    PAGERDUTY_SUBDOMAIN: Optional[str] = Field(default=None)
    GITHUB_TOKEN: Optional[str] = Field(default=None)
    GITHUB_ORG: Optional[str] = Field(default=None)
    GITHUB_REPO: Optional[str] = Field(default=None)

    # API Server
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=1)

    # Retrieval
    RETRIEVAL_TOP_K: int = Field(default=20)
    RETRIEVAL_RERANK_TOP_K: int = Field(default=5)
    RETRIEVAL_SIMILARITY_THRESHOLD: float = Field(default=0.7)

    # Agent
    AGENT_MAX_TURNS: int = Field(default=8)
    AGENT_TIMEOUT_SECONDS: int = Field(default=30)

    # Ingestion
    INGESTION_BATCH_SIZE: int = Field(default=100)
    INGESTION_CHUNK_SIZE: int = Field(default=512)
    INGESTION_CHUNK_OVERLAP: int = Field(default=50)

    # UI
    UI_PORT: int = Field(default=8501)

    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
