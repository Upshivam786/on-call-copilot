"""Semantic chunking for documents."""

from typing import Any

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document as LlamaDocument

from app.config import settings
from app.ingestion.loaders.base import LoadedDocument


class SemanticChunker:
    """Chunks documents using LlamaIndex's SentenceSplitter with semantic awareness."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.INGESTION_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.INGESTION_CHUNK_OVERLAP
        self._splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            paragraph_separator="\n\n\n",
            secondary_chunking_regex="[^.!?]*[.!?]",
        )

    def chunk(self, doc: LoadedDocument) -> list[dict[str, Any]]:
        """Chunk a loaded document into pieces."""
        llama_doc = LlamaDocument(
            text=doc.content,
            metadata={
                "source_type": doc.source_type,
                "title": doc.title,
                "source_id": doc.source_id,
                **doc.metadata,
            },
        )
        nodes = self._splitter.get_nodes_from_documents([llama_doc])

        chunks = []
        for i, node in enumerate(nodes):
            chunks.append(
                {
                    "chunk_index": i,
                    "content": node.get_content(),
                    "token_count": len(node.get_content()) // 4,  # rough estimate
                    "metadata": {**node.metadata, "chunk_index": i},
                }
            )
        return chunks

    def chunk_many(self, docs: list[LoadedDocument]) -> list[dict[str, Any]]:
        """Chunk multiple documents."""
        all_chunks = []
        for doc in docs:
            doc_chunks = self.chunk(doc)
            for chunk in doc_chunks:
                chunk["document_source_type"] = doc.source_type
                chunk["document_title"] = doc.title
                chunk["document_source_id"] = doc.source_id
            all_chunks.extend(doc_chunks)
        return all_chunks