"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import Document, Chunk, Incident, ChatSession, ChatMessage


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create test database engine."""
    from sqlalchemy.pool import StaticPool

    eng = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """Create a new database session for each test."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def sample_document() -> Document:
    """Create a sample document."""
    return Document(
        source_type="runbook",
        source_id="test-runbook-1",
        title="Test Runbook",
        content="This is a test runbook for testing purposes.",
        metadata_={"service": "test-service", "team": "test-team"},
    )


@pytest.fixture
def sample_incident() -> Incident:
    """Create a sample incident."""
    return Incident(
        alert_name="TestAlert",
        severity="high",
        status="resolved",
        root_cause="Test root cause",
        resolution_steps="Test resolution steps",
        services=["test-service"],
        tags=["test"],
        raw_payload={"key": "value"},
    )