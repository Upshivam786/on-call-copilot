"""Base loader for ingesting documents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LoadedDocument:
    """A document loaded from a source."""
    source_type: str
    title: str
    content: str
    source_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    async def load(self) -> list[LoadedDocument]:
        """Load documents from the source."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier."""
        ...
