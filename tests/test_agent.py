"""Tests for agent loop and tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.agent.tools.search_incidents import SearchIncidentsTool
from app.agent.tools.get_timeline import GetIncidentTimelineTool
from app.agent.tools.query_k8s import QueryK8sTool
from app.agent.tools.draft_postmortem import DraftPostmortemTool
from app.agent.state import AgentState, ToolCall
from app.agent.prompts import SYSTEM_PROMPT, get_tool_schemas


class TestTools:
    """Tests for agent tools."""

    @pytest.fixture
    def mock_retrieval_service(self):
        mock = MagicMock()
        mock.search = AsyncMock(return_value=[
            MagicMock(
                chunk_id="chunk-1",
                document_id="doc-1",
                content="Test content",
                title="Test Runbook",
                source_type="runbook",
                score=0.9,
                metadata={"source_id": "test-runbook"},
            )
        ])
        return mock

    @pytest.mark.asyncio
    async def test_search_knowledge_tool(self, mock_retrieval_service):
        """Test search_knowledge tool execution."""
        tool = SearchKnowledgeTool(retrieval_service=mock_retrieval_service)
        result = await tool.execute(query="high error rate", service="payments-api")

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Runbook"

    @pytest.mark.asyncio
    async def test_query_k8s_tool_mock(self):
        """Test query_k8s tool returns mock data."""
        tool = QueryK8sTool()
        result = await tool.execute(action="get_pods", namespace="payments")

        assert "pods" in result
        assert len(result["pods"]) > 0
        assert result["pods"][0]["name"] == "payments-api-7b5c8f9d-xz2m4"

    @pytest.mark.asyncio
    async def test_draft_postmortem_tool(self):
        """Test draft_postmortem tool generates markdown."""
        tool = DraftPostmortemTool()
        result = await tool.execute(
            incident_summary="Test incident",
            timeline="14:00 - Alert fired\n14:30 - Resolved",
            root_cause="Test root cause",
            impact="Service down",
            resolution="Restarted service",
            action_items=["Add monitoring", "Fix bug"],
        )

        assert "postmortem" in result
        assert "Test incident" in result["postmortem"]
        assert "Test root cause" in result["postmortem"]
        assert "Add monitoring" in result["postmortem"]


class TestAgentState:
    """Tests for AgentState."""

    def test_state_initialization(self):
        state = AgentState(user_query="test query")
        assert state.user_query == "test query"
        assert state.turn_count == 0
        assert not state.is_complete

    def test_add_messages(self):
        state = AgentState()
        state.add_user_message("Hello")
        state.add_assistant_message("Hi there")
        assert len(state.messages) == 2
        assert state.messages[0]["role"] == "user"
        assert state.messages[1]["role"] == "assistant"

    def test_add_tool_call(self):
        state = AgentState()
        tool_call = ToolCall(
            name="search_knowledge",
            arguments={"query": "test"},
            result={"results": []},
        )
        state.add_tool_message(tool_call)
        assert len(state.tool_calls) == 1
        assert len(state.messages) == 1
        assert state.messages[0]["role"] == "tool"

    def test_add_citation(self):
        state = AgentState()
        state.add_citation("chunk-1", "doc-1", 0.9, "Snippet here")
        assert len(state.citations) == 1
        assert state.citations[0]["chunk_id"] == "chunk-1"
        assert state.citations[0]["score"] == 0.9


class TestPrompts:
    """Tests for system prompts."""

    def test_system_prompt_contains_tools(self):
        """Test system prompt mentions all tools."""
        for tool_name in ["search_knowledge", "search_incidents", "get_incident_timeline", "query_k8s", "draft_postmortem"]:
            assert tool_name in SYSTEM_PROMPT

    def test_get_tool_schemas(self):
        """Test getting tool schemas."""
        schemas = get_tool_schemas()
        assert len(schemas) == 5
        schema_names = {s["function"]["name"] for s in schemas}
        assert schema_names == {
            "search_knowledge",
            "search_incidents",
            "get_incident_timeline",
            "query_k8s",
            "draft_postmortem",
        }