"""Markdown document loader for runbooks and postmortems."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from app.ingestion.loaders.base import BaseLoader, LoadedDocument


def _serialize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Convert date/datetime objects to ISO strings for JSON serialization."""
    result = {}
    for k, v in metadata.items():
        if isinstance(v, (date, datetime)):
            result[k] = v.isoformat()
        elif isinstance(v, list):
            result[k] = [_serialize_metadata_item(item) for item in v]
        elif isinstance(v, dict):
            result[k] = _serialize_metadata(v)
        else:
            result[k] = v
    return result


def _serialize_metadata_item(item: Any) -> Any:
    if isinstance(item, (date, datetime)):
        return item.isoformat()
    elif isinstance(item, list):
        return [_serialize_metadata_item(i) for i in item]
    elif isinstance(item, dict):
        return _serialize_metadata(item)
    return item


class MarkdownLoader(BaseLoader):
    """Loads Markdown files (.md, .mdx) with optional frontmatter."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    @property
    def source_type(self) -> str:
        return "markdown"

    async def load(self) -> list[LoadedDocument]:
        """Load all Markdown files recursively."""
        documents = []
        for path in self.directory.rglob("*.md"):
            try:
                doc = self._load_file(path)
                if doc:
                    documents.append(doc)
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
        return documents

    def _load_file(self, path: Path) -> LoadedDocument | None:
        """Load a single Markdown file."""
        content = path.read_text(encoding="utf-8")

        # Parse frontmatter if present
        metadata: dict[str, Any] = {}
        title = path.stem
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                metadata.update(_serialize_metadata(frontmatter))
                title = frontmatter.get("title", path.stem)
                content = parts[2].strip()

        return LoadedDocument(
            source_type="markdown",
            title=title,
            content=content,
            source_id=str(path.relative_to(self.directory)),
            metadata={
                "path": str(path),
                "file_name": path.name,
                "doc_type": metadata.get("type", "runbook"),
                **metadata,
            },
        )
