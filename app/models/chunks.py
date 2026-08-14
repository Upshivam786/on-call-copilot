"""Chunk model."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.models.base import Base


class Chunk(Base, table=True):
    """A chunk of a document with its embedding vector."""

    __tablename__ = "chunks"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()),
    )
    document_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    chunk_index: int = Field(description="Order within the document")
    content: str = Field(description="Chunk text")
    embedding: str = Field(description="pgvector embedding as string '[...]'")
    token_count: Optional[int] = Field(default=None)
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
    )


class ChunkCreate(SQLModel):
    """Schema for creating a chunk (for ingestion)."""
    document_id: UUID
    chunk_index: int
    content: str
    embedding: str
    token_count: Optional[int] = None
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")