"""Tests for SQLModel models."""

import pytest
from uuid import uuid4

from app.models import Document, Chunk, Incident, ChatSession, ChatMessage


class TestDocumentModel:
    """Tests for Document model."""

    def test_document_creation(self):
        doc = Document(
            source_type="runbook",
            source_id="test-1",
            title="Test Runbook",
            content="Content here",
            metadata_={"service": "test"},
        )
        assert doc.source_type == "runbook"
        assert doc.source_id == "test-1"
        assert doc.title == "Test Runbook"
        assert doc.metadata_ == {"service": "test"}

    def test_document_defaults(self):
        doc = Document(source_type="postmortem")
        assert doc.source_type == "postmortem"
        assert doc.metadata_ == {}


class TestChunkModel:
    """Tests for Chunk model."""

    def test_chunk_creation(self):
        doc_id = uuid4()
        chunk = Chunk(
            document_id=doc_id,
            chunk_index=0,
            content="Chunk content",
            embedding="[0.1, 0.2, 0.3]",
            token_count=10,
            metadata_={"section": "intro"},
        )
        assert chunk.document_id == doc_id
        assert chunk.chunk_index == 0
        assert chunk.content == "Chunk content"
        assert chunk.embedding == "[0.1, 0.2, 0.3]"


class TestIncidentModel:
    """Tests for Incident model."""

    def test_incident_creation(self):
        inc = Incident(
            alert_name="HighErrorRate",
            severity="critical",
            status="resolved",
            root_cause="DB connection pool exhausted",
            resolution_steps="Rolled back deploy",
            services=["payments-api"],
            tags=["database", "connection"],
            raw_payload={"alert": "data"},
        )
        assert inc.alert_name == "HighErrorRate"
        assert inc.severity == "critical"
        assert inc.services == ["payments-api"]
        assert inc.tags == ["database", "connection"]


class TestChatModels:
    """Tests for Chat session/message models."""

    def test_session_creation(self):
        session = ChatSession(user_id="user-1", title="Test Session", context={"incident_id": "123"})
        assert session.user_id == "user-1"
        assert session.title == "Test Session"
        assert session.context == {"incident_id": "123"}

    def test_message_creation(self):
        session_id = uuid4()
        msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content="Response here",
            citations=[{"chunk_id": "abc", "score": 0.9}],
            tool_calls=[{"name": "search_knowledge", "arguments": {}}],
        )
        assert msg.session_id == session_id
        assert msg.role == "assistant"
        assert msg.citations == [{"chunk_id": "abc", "score": 0.9}]
        assert msg.tool_calls == [{"name": "search_knowledge", "arguments": {}}]