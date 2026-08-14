"""Incident model."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.models.base import Base


class Incident(Base, table=True):
    """An incident record with timeline, root cause, and resolution."""

    __tablename__ = "incidents"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()),
    )
    alert_name: Optional[str] = Field(
        default=None, max_length=255, index=True,
    )
    severity: Optional[str] = Field(
        default=None, max_length=20, index=True,
        description="critical | high | medium | low",
    )
    status: Optional[str] = Field(
        default=None, max_length=20, index=True,
        description="firing | resolved | acknowledged",
    )
    started_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    resolved_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    root_cause: Optional[str] = Field(default=None)
    resolution_steps: Optional[str] = Field(default=None)
    postmortem_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=False), ForeignKey("documents.id"), nullable=True),
    )
    services: Optional[list[str]] = Field(
        default=None, sa_column=Column(ARRAY(Text), nullable=True),
    )
    tags: Optional[list[str]] = Field(
        default=None, sa_column=Column(ARRAY(Text), nullable=True),
    )
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )


class IncidentCreate(SQLModel):
    """Schema for creating an incident."""
    alert_name: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    resolution_steps: Optional[str] = None
    postmortem_id: Optional[UUID] = None
    services: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    raw_payload: Optional[dict[str, Any]] = None


class IncidentRead(SQLModel):
    """Incident details for API."""
    id: UUID
    alert_name: Optional[str]
    severity: Optional[str]
    status: Optional[str]
    started_at: Optional[datetime]
    resolved_at: Optional[datetime]
    root_cause: Optional[str]
    resolution_steps: Optional[str]
    postmortem_id: Optional[UUID]
    services: Optional[list[str]]
    tags: Optional[list[str]]
    raw_payload: Optional[dict[str, Any]]
    created_at: datetime