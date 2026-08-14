"""Tool: Get incident timeline."""

from typing import Any
from uuid import UUID

from app.agent.tools.base import BaseTool
from app.database import get_session
from app.models import Incident, Document
from sqlalchemy import select


class GetIncidentTimelineTool(BaseTool):
    """Get full timeline and details for a specific incident."""

    name = "get_incident_timeline"
    description = (
        "Retrieve the complete timeline, root cause, resolution steps, "
        "and linked postmortem for a specific incident ID. "
        "Use this after finding an incident via search_incidents to get full details."
    )
    schema = {
        "type": "object",
        "properties": {
            "incident_id": {
                "type": "string",
                "description": "UUID of the incident to retrieve",
            },
        },
        "required": ["incident_id"],
    }

    async def execute(self, incident_id: str) -> dict[str, Any]:
        """Execute timeline retrieval."""
        async with get_session() as session:
            # Get incident
            stmt = select(Incident).where(Incident.id == UUID(incident_id))
            result = await session.execute(stmt)
            incident = result.scalar_one_or_none()

            if not incident:
                return {"error": f"Incident {incident_id} not found"}

            # Get linked postmortem if any
            postmortem = None
            if incident.postmortem_id:
                stmt = select(Document).where(Document.id == incident.postmortem_id)
                result = await session.execute(stmt)
                postmortem = result.scalar_one_or_none()

        return {
            "incident": {
                "id": str(incident.id),
                "alert_name": incident.alert_name,
                "severity": incident.severity,
                "status": incident.status,
                "services": incident.services,
                "started_at": incident.started_at.isoformat() if incident.started_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "root_cause": incident.root_cause,
                "resolution_steps": incident.resolution_steps,
                "tags": incident.tags,
                "raw_payload": incident.raw_payload,
            },
            "postmortem": (
                {
                    "id": str(postmortem.id),
                    "title": postmortem.title,
                    "content": postmortem.content,
                }
                if postmortem
                else None
            ),
        }