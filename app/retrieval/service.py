"""Retrieval service: hybrid search over documents/chunks with reranking and query expansion."""

from typing import Any, Optional

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.models import Chunk, Document
from app.ingestion.embedder import BatchEmbedder
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.strategies import HybridSearchStrategy, BM25Strategy, VectorStrategy
from app.retrieval.models import SearchResult


class RetrievalService:
    """Hybrid RAG retrieval with reranking and query expansion."""

    def __init__(
        self,
        embedder: BatchEmbedder = None,
        reranker: CrossEncoderReranker = None,
        top_k: int = None,
        rerank_top_k: int = None,
    ):
        self.embedder = embedder or BatchEmbedder()
        self.reranker = reranker or CrossEncoderReranker()
        self.top_k = top_k or settings.RETRIEVAL_TOP_K
        self.rerank_top_k = rerank_top_k or settings.RETRIEVAL_RERANK_TOP_K
        self.vector_strategy = VectorStrategy()
        self.bm25_strategy = BM25Strategy()
        self.hybrid_strategy = HybridSearchStrategy(
            vector_weight=0.7,
            bm25_weight=0.3,
        )

    async def search(
        self,
        query: str,
        filters: dict[str, Any] = None,
        use_query_expansion: bool = True,
        use_reranking: bool = True,
    ) -> list[SearchResult]:
        """Main search entrypoint."""
        # Query expansion (optional)
        queries = [query]
        if use_query_expansion:
            expanded = await self._expand_query(query)
            queries.extend(expanded)

        # Hybrid search per query, then merge results
        all_results: dict[str, SearchResult] = {}

        for q in queries:
            results = await self._hybrid_search_single(q, filters)
            for r in results:
                # Keep highest score per chunk
                if r.chunk_id not in all_results or r.score > all_results[r.chunk_id].score:
                    all_results[r.chunk_id] = r

        # Sort by score descending
        merged = sorted(all_results.values(), key=lambda x: x.score, reverse=True)
        merged = merged[: self.top_k * 2]  # Oversample before reranking

        # Rerank if enabled
        if use_reranking and self.reranker.is_available():
            merged = await self._rerank(query, merged)

        return merged[: self.top_k]

    async def _hybrid_search_single(
        self,
        query: str,
        filters: dict[str, Any] | None,
    ) -> list[SearchResult]:
        """Run hybrid search for a single query."""
        # Get query embedding
        embedding = await self.embedder.embed_texts([query])
        query_embedding = embedding[0]

        # Build filter clause
        filter_clause = self._build_filter_clause(filters) if filters else ""

        # Vector search
        vector_results = await self.vector_strategy.search(
            query_embedding=query_embedding,
            top_k=self.top_k,
            filter_clause=filter_clause,
        )

        # BM25 search
        bm25_results = await self.bm25_strategy.search(
            query=query,
            top_k=self.top_k,
            filter_clause=filter_clause,
        )

        # Combine via hybrid strategy
        return self.hybrid_strategy.combine(
            vector_results=vector_results,
            bm25_results=bm25_results,
            top_k=self.top_k,
        )

    async def _expand_query(self, query: str) -> list[str]:
        """Expand query using LLM into multiple semantically similar queries."""
        # This is a lightweight version; full implementation uses LLM
        # For now, we do simple expansion: extract key terms and reformulate
        try:
            import openai

            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a query expansion engine for incident response knowledge search. "
                        "Given a user query about an incident or alert, generate 2-3 alternative phrasings "
                        "that might match relevant runbooks, postmortems, or incident records. "
                        "Return only the expanded queries, one per line.",
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=200,
            )
            expanded = response.choices[0].message.content.strip().split("\n")
            return [q.strip() for q in expanded if q.strip()][:3]
        except Exception as e:
            # Silently fall back to no expansion
            return []

    async def _rerank(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """Rerank results using cross-encoder."""
        if not results:
            return results

        pairs = [(query, r.content) for r in results]
        scores = await self.reranker.predict(pairs)

        for r, score in zip(results, scores):
            r.rerank_score = score

        return sorted(results, key=lambda x: x.rerank_score or 0.0, reverse=True)

    def _build_filter_clause(self, filters: dict[str, Any]) -> str:
        """Build SQL filter clause from metadata filters."""
        clauses = []

        if "service" in filters:
            clauses.append(f"chunks.metadata->>'service' = '{filters['service']}'")

        if "team" in filters:
            clauses.append(f"documents.metadata->>'team' = '{filters['team']}'")

        if "source_type" in filters:
            clauses.append(f"documents.source_type = '{filters['source_type']}'")

        if "severity" in filters:
            clauses.append(f"incidents.severity = '{filters['severity']}'")

        if "date_from" in filters:
            clauses.append(f"chunks.created_at >= '{filters['date_from']}'")

        if "date_to" in filters:
            clauses.append(f"chunks.created_at <= '{filters['date_to']}'")

        if not clauses:
            return ""

        return " AND " + " AND ".join(clauses)
