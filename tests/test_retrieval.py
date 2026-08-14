"""Tests for retrieval service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.retrieval.service import RetrievalService, SearchResult
from app.retrieval.strategies import VectorStrategy, BM25Strategy, HybridSearchStrategy
from app.retrieval.reranker import CrossEncoderReranker


class TestRetrievalService:
    """Tests for RetrievalService."""

    @pytest.fixture
    def mock_retrieval(self):
        with patch("app.retrieval.service.BatchEmbedder") as mock_embedder:
            mock_embedder.return_value.embed_texts = AsyncMock(
                return_value=[[0.1] * 1536]
            )
            with patch("app.retrieval.service.CrossEncoderReranker") as mock_reranker:
                mock_reranker.return_value.is_available.return_value = False
                service = RetrievalService()
                yield service

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_retrieval):
        """Test that search returns SearchResult objects."""
        with patch.object(mock_retrieval, "_hybrid_search_single") as mock_search:
            mock_search.return_value = [
                SearchResult(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    content="Test content",
                    title="Test Doc",
                    source_type="runbook",
                    score=0.9,
                )
            ]
            results = await mock_retrieval.search("test query")
            assert len(results) == 1
            assert results[0].title == "Test Doc"

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_retrieval):
        """Test search with metadata filters."""
        with patch.object(mock_retrieval, "_hybrid_search_single") as mock_search:
            mock_search.return_value = []
            await mock_retrieval.search("test", filters={"service": "payments-api"})
            # Verify filter clause was passed
            call_args = mock_search.call_args
            assert call_args.args[1] == {"service": "payments-api"}


class TestHybridSearchStrategy:
    """Tests for HybridSearchStrategy."""

    def test_combine_results(self):
        """Test combining vector and BM25 results."""
        from app.retrieval.strategies import RawSearchResult

        vector_results = [
            RawSearchResult(
                chunk_id="c1", document_id="d1", content="c1", title="t1",
                source_type="runbook", score=0.9, metadata={}
            ),
            RawSearchResult(
                chunk_id="c2", document_id="d2", content="c2", title="t2",
                source_type="runbook", score=0.7, metadata={}
            ),
        ]

        bm25_results = [
            RawSearchResult(
                chunk_id="c2", document_id="d2", content="c2", title="t2",
                source_type="runbook", score=0.8, metadata={}
            ),
            RawSearchResult(
                chunk_id="c3", document_id="d3", content="c3", title="t3",
                source_type="runbook", score=0.6, metadata={}
            ),
        ]

        hybrid = HybridSearchStrategy(vector_weight=0.7, bm25_weight=0.3)
        combined = hybrid.combine(vector_results, bm25_results, top_k=3)

        assert len(combined) == 3
        # c2 should have higher combined score
        assert combined[0].chunk_id == "c1"  # Only in vector, high score
        # c2 in both

    def test_normalize_scores(self):
        """Test score normalization."""
        from app.retrieval.strategies import RawSearchResult

        hybrid = HybridSearchStrategy()
        results = [
            RawSearchResult(chunk_id="c1", document_id="d1", content="c1", title="t1",
                           source_type="runbook", score=100, metadata={}),
            RawSearchResult(chunk_id="c2", document_id="d2", content="c2", title="t2",
                           source_type="runbook", score=10, metadata={}),
        ]
        normalized = hybrid._normalize_scores(results)
        assert normalized[0].score == 1.0
        assert normalized[1].score == 0.0


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker."""

    def test_is_available_with_model(self):
        """Test is_available returns True when sentence-transformers is installed."""
        reranker = CrossEncoderReranker(use_local=True)
        # With sentence-transformers installed, should be True
        assert reranker.is_available() is True