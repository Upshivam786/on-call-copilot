"""Batch embedding with retry/backoff."""

import asyncio
import os
from typing import Any, Optional

import openai
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr

from app.config import settings


class BatchEmbedder:
    """Batch embedder with OpenAI and local fallback."""

    def __init__(
        self,
        model: str = None,
        dimensions: int = None,
        batch_size: int = None,
    ):
        self.model = model or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self.batch_size = batch_size or settings.INGESTION_BATCH_SIZE
        self._client: Optional[openai.AsyncOpenAI] = None
        self._local_available = False

    async def _get_client(self) -> openai.AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                max_retries=0,  # We handle retries ourselves
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts with batching and retry."""
        if not texts:
            return []

        client = await self._get_client()
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings = await self._embed_batch_with_retry(client, batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def _embed_batch_with_retry(
        self, client: openai.AsyncOpenAI, texts: list[str], max_retries: int = 3
    ) -> list[list[float]]:
        """Embed a batch with exponential backoff retry."""
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = await client.embeddings.create(
                    model=self.model,
                    input=texts,
                    dimensions=self.dimensions if "text-embedding-3" in self.model else None,
                )
                return [data.embedding for data in response.data]

            except openai.RateLimitError as e:
                last_exception = e
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

            except openai.APIError as e:
                last_exception = e
                wait_time = 2 ** attempt
                print(f"API error: {e}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

            except Exception as e:
                last_exception = e
                wait_time = 2 ** attempt
                print(f"Unexpected error: {e}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

        # If all retries fail, raise the last exception
        raise last_exception

    def embed_single(self, text: str) -> list[float]:
        """Synchronous single embedding (for CLI use)."""
        import openai as sync_openai

        client = sync_openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(
            model=self.model,
            input=[text],
            dimensions=self.dimensions if "text-embedding-3" in self.model else None,
        )
        return response.data[0].embedding


class LocalEmbedder:
    """Local embedding fallback using sentence-transformers (optional)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts locally."""
        self._load_model()
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> list[float]:
        """Embed single text locally."""
        return self.embed_texts([text])[0]


def get_embedder() -> BatchEmbedder | LocalEmbedder:
    """Get appropriate embedder based on configuration."""
    if settings.OPENAI_API_KEY:
        return BatchEmbedder()
    else:
        print("Warning: No OPENAI_API_KEY set, using local embedder")
        return LocalEmbedder()