"""Search strategies: Vector, BM25, Hybrid."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import Chunk, Document
from app.retrieval.models import SearchResult, RawSearchResult


class BaseStrategy:
    """Base class for search strategies."""

    async def search(
        self,
        query: str | list[float] = None,
        query_embedding: list[float] = None,
        top_k: int = 20,
        filter_clause: str = "",
    ) -> list[RawSearchResult]:
        raise NotImplementedError


class VectorStrategy(BaseStrategy):
    """Pure vector similarity search using pgvector."""

    async def search(
        self,
        query_embedding: list[float] = None,
        top_k: int = 20,
        filter_clause: str = "",
    ) -> list[RawSearchResult]:
        if query_embedding is None:
            raise ValueError("query_embedding required for vector search")

        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        query = f"""
            SELECT
                c.id as chunk_id,
                c.document_id,
                c.content,
                d.title,
                d.source_type,
                1 - (c.embedding <=> '{embedding_str}'::vector) as score,
                c.metadata
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE 1=1 {filter_clause}
            ORDER BY c.embedding <=> '{embedding_str}'::vector
            LIMIT {top_k}
        """

        async with get_db_session() as session:
            result = await session.execute(text(query))
            rows = result.fetchall()

        return [
            RawSearchResult(
                chunk_id=str(r.chunk_id),
                document_id=str(r.document_id),
                content=r.content,
                title=r.title,
                source_type=r.source_type,
                score=float(r.score),
                metadata=r.metadata or {},
            )
            for r in rows
        ]


class BM25Strategy(BaseStrategy):
    """Full-text search using PostgreSQL's built-in tsvector/tsquery."""

    async def search(
        self,
        query: str = None,
        top_k: int = 20,
        filter_clause: str = "",
    ) -> list[RawSearchResult]:
        if query is None:
            raise ValueError("query required for BM25 search")

        # Simple tsquery conversion
        # In production, use websearch_to_tsquery for better handling
        ts_query = " & ".join(query.split())

        query_sql = f"""
            SELECT
                c.id as chunk_id,
                c.document_id,
                c.content,
                d.title,
                d.source_type,
                ts_rank_cd(
                    to_tsvector('english', c.content),
                    websearch_to_tsquery('english', '{ts_query}')
                ) as score,
                c.metadata
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE to_tsvector('english', c.content) @@ websearch_to_tsquery('english', '{ts_query}')
              AND 1=1 {filter_clause}
            ORDER BY score DESC
            LIMIT {top_k}
        """

        async with get_db_session() as session:
            result = await session.execute(text(query_sql))
            rows = result.fetchall()

        return [
            RawSearchResult(
                chunk_id=str(r.chunk_id),
                document_id=str(r.document_id),
                content=r.content,
                title=r.title,
                source_type=r.source_type,
                score=float(r.score),
                metadata=r.metadata or {},
            )
            for r in rows
        ]


class HybridSearchStrategy:
    """Combines vector and BM25 results with weighted scores."""

    def __init__(
        self,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ):
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def combine(
        self,
        vector_results: list[RawSearchResult],
        bm25_results: list[RawSearchResult],
        top_k: int = 20,
    ) -> list[SearchResult]:
        """Combine and normalize scores."""
        # Normalize scores to 0-1 within each result set
        norm_vector = self._normalize_scores(vector_results)
        norm_bm25 = self._normalize_scores(bm25_results)

        # Merge by chunk_id, taking max weighted score
        merged: dict[str, SearchResult] = {}

        for r in norm_vector:
            merged[r.chunk_id] = SearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                title=r.title,
                source_type=r.source_type,
                score=r.score * self.vector_weight,
                metadata=r.metadata,
            )

        for r in norm_bm25:
            if r.chunk_id in merged:
                merged[r.chunk_id].score += r.score * self.bm25_weight
            else:
                merged[r.chunk_id] = SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.content,
                    title=r.title,
                    source_type=r.source_type,
                    score=r.score * self.bm25_weight,
                    metadata=r.metadata,
                )

        # Sort by combined score
        sorted_results = sorted(merged.values(), key=lambda x: x.score, reverse=True)
        return sorted_results[:top_k]

    def _normalize_scores(self, results: list[RawSearchResult]) -> list[RawSearchResult]:
        """Normalize scores to 0-1 range using min-max."""
        if not results:
            return []

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [RawSearchResult(**{**r.__dict__, "score": 1.0}) for r in results]

        return [
            RawSearchResult(**{**r.__dict__, "score": (r.score - min_score) / (max_score - min_score)})
            for r in results
        ]