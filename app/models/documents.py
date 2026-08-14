"""Document model."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.models.base import Base


class Document(Base, table=True):
    """A source document (runbook, postmortem, alert definition, config, etc.)."""

    __tablename__ = "documents"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()),
    )
    source_type: str = Field(
        max_length=50, index=True,
        description="runbook | postmortem | alert_def | config | slack",
    )
    source_id: Optional[str] = Field(
        default=None, max_length=255, index=True,
        description="External ID (e.g., Jira key)",
    )
    title: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    __table_args__ = (
        Index("idx_documents_source", "source_type", "source_id"),
    )
