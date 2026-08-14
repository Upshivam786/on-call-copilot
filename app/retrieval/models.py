"""Shared retrieval models to avoid circular imports."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """A search result with metadata and score."""
    chunk_id: str
    document_id: str
    content: str
    title: str
    source_type: str
    score: float = 0.0
    rerank_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "title": self.title,
            "source_type": self.source_type,
            "score": self.score,
            "rerank_score": self.rerank_score,
            "metadata": self.metadata,
        }


@dataclass
class RawSearchResult:
    """Raw result from a search strategy."""
    chunk_id: str
    document_id: str
    content: str
    title: str
    source_type: str
    score: float
    metadata: dict[str, Any]