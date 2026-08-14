"""Agent tools package."""

from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.agent.tools.search_incidents import SearchIncidentsTool
from app.agent.tools.get_timeline import GetIncidentTimelineTool
from app.agent.tools.query_k8s import QueryK8sTool
from app.agent.tools.draft_postmortem import DraftPostmortemTool

__all__ = [
    "SearchKnowledgeTool",
    "SearchIncidentsTool",
    "GetIncidentTimelineTool",
    "QueryK8sTool",
    "DraftPostmortemTool",
]

# Registry of all available tools
TOOL_REGISTRY = {
    "search_knowledge": SearchKnowledgeTool,
    "search_incidents": SearchIncidentsTool,
    "get_incident_timeline": GetIncidentTimelineTool,
    "query_k8s": QueryK8sTool,
    "draft_postmortem": DraftPostmortemTool,
}
