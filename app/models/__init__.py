"""SQLModel models for On-Call Copilot."""

from app.models.documents import Document
from app.models.chunks import Chunk, ChunkCreate
from app.models.incidents import Incident, IncidentCreate, IncidentRead
from app.models.chat import (
    ChatSession,
    ChatMessage,
    ChatSessionCreate,
    ChatSessionRead,
    ChatMessageCreate,
    ChatMessageRead,
)

__all__ = [
    "Document",
    "Chunk",
    "ChunkCreate",
    "Incident",
    "IncidentCreate",
    "IncidentRead",
    "ChatSession",
    "ChatMessage",
    "ChatSessionCreate",
    "ChatSessionRead",
    "ChatMessageCreate",
    "ChatMessageRead",
]

# Base for metadata reference
from app.models.base import Base  # noqa: E402

__all__.append("Base")
