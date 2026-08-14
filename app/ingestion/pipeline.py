"""Ingestion pipeline orchestrator."""

from typing import Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models import Document, Chunk
from app.ingestion.chunker import SemanticChunker
from app.ingestion.embedder import BatchEmbedder, get_embedder


class IngestionPipeline:
    """Orchestrates document loading, chunking, embedding, and storage."""

    def __init__(
        self,
        chunker: SemanticChunker = None,
        embedder=None,
    ):
        self.chunker = chunker or SemanticChunker()
        self.embedder = embedder or get_embedder()

    async def ingest_documents(
        self,
        loaded_docs: list[Any],  # List[LoadedDocument]
        progress_callback=None,
    ) -> dict[str, Any]:
        """Full ingestion: chunk -> embed -> store."""
        stats = {"documents": 0, "chunks": 0, "embeddings": 0, "errors": []}

        # Chunk all documents
        all_chunks = self.chunker.chunk_many(loaded_docs)
        stats["documents"] = len(loaded_docs)
        stats["chunks"] = len(all_chunks)

        if not all_chunks:
            return stats

        # Embed in batches
        texts = [c["content"] for c in all_chunks]
        try:
            if hasattr(self.embedder, 'embed_texts'):
                import asyncio
                if asyncio.iscoroutinefunction(self.embedder.embed_texts):
                    embeddings = await self.embedder.embed_texts(texts)
                else:
                    embeddings = self.embedder.embed_texts(texts)
                stats["embeddings"] = len(embeddings)
            else:
                raise AttributeError("Embedder has no embed_texts method")
        except Exception as e:
            stats["errors"].append(f"Embedding failed: {e}")
            return stats

        # Store in database
        async with get_session() as session:
            for i, chunk in enumerate(all_chunks):
                try:
                    # Get or create document
                    doc = await self._get_or_create_document(
                        session,
                        chunk["document_source_type"],
                        chunk["document_source_id"],
                        chunk["document_title"],
                        loaded_docs[i // (len(all_chunks) // len(loaded_docs) + 1)].content
                        if loaded_docs and len(all_chunks) > 0
                        else "",
                    )

                    # Store chunk with embedding
                    await self._store_chunk(
                        session,
                        doc.id,
                        chunk,
                        embeddings[i],
                    )

                except Exception as e:
                    stats["errors"].append(f"Chunk {i} storage failed: {e}")

        if progress_callback:
            await progress_callback(stats)

        return stats

    async def _get_or_create_document(
        self,
        session: AsyncSession,
        source_type: str,
        source_id: Optional[str],
        title: str,
        content: str,
    ) -> Document:
        """Get existing document or create new one (idempotent by source_id)."""
        if source_id:
            stmt = select(Document).where(
                Document.source_type == source_type,
                Document.source_id == source_id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                # Update content if changed
                if existing.content != content:
                    existing.content = content
                    existing.updated_at = __import__("datetime").datetime.utcnow()
                return existing

        doc = Document(
            source_type=source_type,
            source_id=source_id,
            title=title,
            content=content,
            metadata_={},
        )
        session.add(doc)
        await session.flush()  # Get ID
        return doc

    async def _store_chunk(
        self,
        session: AsyncSession,
        document_id: Any,
        chunk: dict[str, Any],
        embedding: list[float],
    ) -> None:
        """Store a chunk with its embedding."""
        # Delete existing chunks for this document (idempotent)
        stmt = delete(Chunk).where(Chunk.document_id == document_id)
        await session.execute(stmt)

        chunk_obj = Chunk(
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=f"[{','.join(str(x) for x in embedding)}]",
            token_count=chunk.get("token_count"),
            metadata_=chunk.get("metadata", {}),
        )
        session.add(chunk_obj)

    async def reindex_document(
        self,
        source_type: str,
        source_id: str,
    ) -> bool:
        """Re-ingest a single document by source ID (idempotent)."""
        # This would need the loader to be re-invoked
        # For now, just delete existing chunks
        async with get_session() as session:
            stmt = select(Document).where(
                Document.source_type == source_type,
                Document.source_id == source_id,
            )
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if not doc:
                return False

            delete_stmt = delete(Chunk).where(Chunk.document_id == doc.id)
            await session.execute(delete_stmt)
            return True
