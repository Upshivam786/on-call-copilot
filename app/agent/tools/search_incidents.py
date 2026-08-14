"""Tool: Search incidents."""

from typing import Any, Optional
from datetime import datetime

from app.agent.tools.base import BaseTool
from app.database import get_session
from app.models import Incident
from sqlalchemy import select


class SearchIncidentsTool(BaseTool):
    """Search past incidents by alert name, service, severity, or date."""

    name = "search_incidents"
    description = (
        "Search historical incidents to find similar past issues, their root causes, "
        "and how they were resolved. Useful for understanding if an alert has fired "
        "before and what the standard mitigation was."
    )
    schema = {
        "type": "object",
        "properties": {
            "alert_name": {
                "type": "string",
                "description": "Optional: filter by alert name (partial match)",
            },
            "service": {
                "type": "string",
                "description": "Optional: filter by affected service",
            },
            "severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low"],
                "description": "Optional: filter by severity",
            },
            "status": {
                "type": "string",
                "enum": ["firing", "resolved", "acknowledged"],
                "description": "Optional: filter by status",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of incidents to return (default 10)",
                "default": 10,
            },
        },
        "required": [],
    }

    async def execute(
        self,
        alert_name: str | None = None,
        service: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Execute incident search."""
        stmt = select(Incident).order_by(Incident.started_at.desc())

        if alert_name:
            stmt = stmt.where(Incident.alert_name.ilike(f"%{alert_name}%"))
        if service:
            # services is an array column
            stmt = stmt.where(Incident.services.any(service))
        if severity:
            stmt = stmt.where(Incident.severity == severity)
        if status:
            stmt = stmt.where(Incident.status == status)

        stmt = stmt.limit(limit)

        async with get_session() as session:
            result = await session.execute(stmt)
            incidents = result.scalars().all()

        formatted = []
        for inc in incidents:
            formatted.append(
                {
                    "id": str(inc.id),
                    "alert_name": inc.alert_name,
                    "severity": inc.severity,
                    "status": inc.status,
                    "services": inc.services,
                    "started_at": inc.started_at.isoformat() if inc.started_at else None,
                    "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
                    "root_cause": inc.root_cause,
                    "resolution_steps": inc.resolution_steps,
                }
            )

        return {
            "incidents": formatted,
            "total_found": len(formatted),
        }