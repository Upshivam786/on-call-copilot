"""Chat models."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.models.base import Base


class ChatSession(Base, table=True):
    """A chat session with context."""

    __tablename__ = "chat_sessions"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()),
    )
    user_id: Optional[str] = Field(
        default=None, max_length=255, index=True,
    )
    title: Optional[str] = Field(default=None, max_length=500)
    context: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class ChatMessage(Base, table=True):
    """A message in a chat session."""

    __tablename__ = "chat_messages"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()),
    )
    session_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=False), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    role: str = Field(max_length=20, description="user | assistant | tool")
    content: Optional[str] = Field(default=None)
    citations: Optional[list[dict[str, Any]]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True),
    )
    tool_calls: Optional[list[dict[str, Any]]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id", "created_at"),
    )


class ChatSessionCreate(SQLModel):
    """Request to create a session."""
    user_id: Optional[str] = None
    title: Optional[str] = None


class ChatSessionRead(SQLModel):
    """Session details."""
    id: UUID
    user_id: Optional[str]
    title: Optional[str]
    context: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(SQLModel):
    """Request to add a message."""
    session_id: UUID
    role: str = "user"
    content: str


class ChatMessageRead(SQLModel):
    """Response with message details."""
    id: UUID
    session_id: UUID
    role: str
    content: Optional[str]
    citations: Optional[list[dict[str, Any]]] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    created_at: datetime