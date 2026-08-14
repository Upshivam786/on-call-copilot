"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import create_app
from app.models import ChatSession, ChatMessage
from app.database import Base


@pytest.fixture
async def engine():
    """Create test database engine (PostgreSQL)."""
    eng = create_async_engine(
        "postgresql+asyncpg://oncall:oncall_dev_password@localhost:5434/oncall_copilot",
        echo=False,
        poolclass=NullPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def app(engine):
    """Create test app with database override."""
    from app.database import get_db_session

    app = create_app()

    async def override_get_db_session():
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "components" in data


class TestChatEndpoints:
    """Tests for chat endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Test creating a new chat session."""
        resp = await client.post("/api/v1/chat/sessions", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_list_sessions(self, client):
        """Test listing sessions."""
        resp = await client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_messages(self, client):
        """Test getting messages for a session."""
        # Create session first
        create_resp = await client.post("/api/v1/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_delete_session(self, client):
        """Test deleting a session."""
        create_resp = await client.post("/api/v1/chat/sessions", json={})
        session_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 204


class TestIngestEndpoints:
    """Tests for ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_trigger_ingestion(self, client):
        """Test triggering ingestion."""
        resp = await client.post(
            "/api/v1/ingest",
            json={"source": "markdown", "path": "./demo_docs"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_ingestion_status(self, client):
        """Test getting ingestion status."""
        # First trigger
        trigger = await client.post(
            "/api/v1/ingest",
            json={"source": "markdown", "path": "./demo_docs"},
        )
        job_id = trigger.json()["job_id"]

        resp = await client.get(f"/api/v1/ingest/status/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id