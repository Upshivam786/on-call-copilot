"""Agent conversation state."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class AgentState:
    """State maintained during an agent conversation turn."""

    session_id: UUID = field(default_factory=uuid4)
    user_query: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)  # OpenAI format
    tool_calls: list[ToolCall] = field(default_factory=list)
    turn_count: int = 0
    citations: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str | None = None
    is_complete: bool = False

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_message(self, tool_call: ToolCall):
        self.tool_calls.append(tool_call)
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.name,
                "content": str(tool_call.result) if tool_call.result else tool_call.error,
            }
        )

    def add_citation(self, chunk_id: str, document_id: str, score: float, snippet: str):
        self.citations.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "score": round(score, 4),
                "snippet": snippet[:200],
            }
        )