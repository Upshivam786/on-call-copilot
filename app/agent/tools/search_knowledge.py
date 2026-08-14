"""Tool: Search knowledge base (RAG hybrid search)."""

from typing import Any

from app.agent.tools.base import BaseTool
from app.retrieval.service import RetrievalService


class SearchKnowledgeTool(BaseTool):
    """Search operational knowledge base (runbooks, postmortems, alerts)."""

    name = "search_knowledge"
    description = (
        "Search the knowledge base for runbooks, postmortems, alert definitions, "
        "and operational documentation. Use this to find relevant procedures and past "
        "incidents when responding to an alert or incident."
    )
    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query describing the symptom, service, or alert",
            },
            "service": {
                "type": "string",
                "description": "Optional: filter by service name (e.g., 'payments-api')",
            },
            "source_type": {
                "type": "string",
                "enum": ["runbook", "postmortem", "alert_def", "config", "slack"],
                "description": "Optional: filter by document type",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, retrieval_service: RetrievalService = None):
        self.retrieval_service = retrieval_service or RetrievalService()

    async def execute(
        self,
        query: str,
        service: str | None = None,
        source_type: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Execute knowledge search."""
        filters = {}
        if service:
            filters["service"] = service
        if source_type:
            filters["source_type"] = source_type

        results = await self.retrieval_service.search(
            query=query,
            filters=filters if filters else None,
            use_query_expansion=True,
            use_reranking=True,
        )

        # Return top_k formatted results
        formatted = []
        for r in results[:top_k]:
            formatted.append(
                {
                    "title": r.title,
                    "source_type": r.source_type,
                    "content": r.content[:500],  # Truncate for tool output
                    "score": round(r.score, 4),
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                }
            )

        return {
            "results": formatted,
            "total_found": len(results),
            "note": "Citations must use chunk_id and document_id when referenced in the answer.",
        }