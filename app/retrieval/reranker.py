"""Cross-encoder reranker for search results."""

from typing import Any, Optional


class CrossEncoderReranker:
    """Cross-encoder reranker using sentence-transformers (optional)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        use_local: bool = True,
    ):
        self.model_name = model_name
        self.use_local = use_local
        self._model: Optional[Any] = None
        self._available = False

    def is_available(self) -> bool:
        """Check if reranker is available."""
        if self._available:
            return True

        try:
            if self.use_local:
                import sentence_transformers

                self._model = sentence_transformers.CrossEncoder(self.model_name)
                self._available = True
                return True
        except ImportError:
            pass

        return False

    async def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Predict relevance scores for query-document pairs."""
        if not self.is_available() or not pairs:
            return [0.5] * len(pairs)

        try:
            # Run in thread pool to avoid blocking
            import asyncio

            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                lambda: self._model.predict(pairs, show_progress_bar=False),
            )
            return [float(s) for s in scores]
        except Exception as e:
            print(f"Reranker error: {e}")
            return [0.5] * len(pairs)

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Rerank documents and return top-k."""
        if not self.is_available() or not documents:
            return documents[:top_k]

        pairs = [(query, doc.get("content", "")) for doc in documents]
        scores = await self.predict(pairs)

        for doc, score in zip(documents, scores):
            doc["rerank_score"] = score

        return sorted(documents, key=lambda x: x.get("rerank_score", 0), reverse=True)[:top_k]