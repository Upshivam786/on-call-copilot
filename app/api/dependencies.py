"""Dependency injection for API routes."""

from typing import AsyncGenerator

from app.database import get_db_session
from app.config import settings


# Placeholder for future dependencies:
# - get_redis_client
# - get_retriever
# - get_agent
# - get_current_user (auth)

__all__ = ["get_db_session", "settings"]
