"""PagerDuty loader for incidents and runbooks."""

from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import settings
from app.ingestion.loaders.base import BaseLoader, LoadedDocument


class PagerDutyLoader(BaseLoader):
    """Loads incidents and runbooks from PagerDuty."""

    def __init__(
        self,
        subdomain: str | None = None,
        api_key: str | None = None,
        since_days: int = 30,
    ):
        self.subdomain = subdomain or settings.PAGERDUTY_SUBDOMAIN
        self.api_key = api_key or settings.PAGERDUTY_API_KEY
        self.since_days = since_days

    @property
    def source_type(self) -> str:
        return "pagerduty"

    async def load(self) -> list[LoadedDocument]:
        """Load incidents from PagerDuty."""
        if not self.api_key or not self.subdomain:
            raise ValueError("PAGERDUTY_API_KEY and PAGERDUTY_SUBDOMAIN not configured")

        since = (datetime.utcnow() - timedelta(days=self.since_days)).isoformat() + "Z"

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Token token={self.api_key}",
                "Accept": "application/vnd.pagerduty+json;version=2",
            }

            # Fetch incidents
            incidents = await self._fetch_incidents(client, headers, since)

            # Fetch runbooks (if available via API)
            runbooks = await self._fetch_runbooks(client, headers)

            documents = []

            # Convert incidents to documents
            for inc in incidents:
                documents.append(
                    LoadedDocument(
                        source_type="incident",
                        title=f"Incident: {inc.get('title', 'Unknown')}",
                        content=self._format_incident(inc),
                        source_id=inc.get("id"),
                        metadata={
                            "incident_number": inc.get("incident_number"),
                            "status": inc.get("status"),
                            "urgency": inc.get("urgency"),
                            "service": inc.get("service", {}).get("summary"),
                            "created_at": inc.get("created_at"),
                            "resolved_at": inc.get("resolved_at"),
                            "doc_type": "incident",
                        },
                    )
                )

            # Convert runbooks
            for rb in runbooks:
                documents.append(
                    LoadedDocument(
                        source_type="runbook",
                        title=rb.get("title", "Runbook"),
                        content=rb.get("content", ""),
                        source_id=rb.get("id"),
                        metadata={
                            "service": rb.get("service", {}).get("summary"),
                            "doc_type": "runbook",
                        },
                    )
                )

            return documents

    async def _fetch_incidents(self, client: httpx.AsyncClient, headers: dict, since: str) -> list[dict]:
        """Fetch incidents from PagerDuty."""
        url = f"https://{self.subdomain}.pagerduty.com/api/v2/incidents"
        params = {
            "since": since,
            "limit": 100,
            "include[]": "body",
        }

        all_incidents = []
        while True:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            all_incidents.extend(data.get("incidents", []))
            if not data.get("more", False):
                break
            params["offset"] = data.get("offset", 0) + len(data.get("incidents", []))
        return all_incidents

    async def _fetch_runbooks(self, client: httpx.AsyncClient, headers: dict) -> list[dict]:
        """Fetch runbooks from PagerDuty (if supported)."""
        # Note: PagerDuty runbooks API may vary; this is a placeholder
        url = f"https://{self.subdomain}.pagerduty.com/api/v2/runbooks"
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("runbooks", [])
        except Exception:
            return []

    def _format_incident(self, incident: dict) -> str:
        """Format incident as readable text."""
        parts = [
            f"Title: {incident.get('title', 'N/A')}",
            f"Status: {incident.get('status', 'N/A')}",
            f"Urgency: {incident.get('urgency', 'N/A')}",
            f"Service: {incident.get('service', {}).get('summary', 'N/A')}",
            f"Created: {incident.get('created_at', 'N/A')}",
            f"Resolved: {incident.get('resolved_at', 'N/A')}",
            "",
            "Description:",
            incident.get("body", {}).get("details", "No description"),
        ]
        return "\n".join(parts)