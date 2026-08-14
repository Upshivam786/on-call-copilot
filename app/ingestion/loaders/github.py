"""GitHub loader for postmortems and runbooks."""

from typing import Any

import httpx

from app.config import settings
from app.ingestion.loaders.base import BaseLoader, LoadedDocument


class GitHubPostmortemLoader(BaseLoader):
    """Loads Markdown postmortems from a GitHub repo."""

    def __init__(
        self,
        repo: str = "your-org/your-postmortems-repo",
        path: str = "postmortems",
        token: str | None = None,
    ):
        self.repo = repo
        self.path = path
        self.token = token or settings.GITHUB_TOKEN

    @property
    def source_type(self) -> str:
        return "postmortem"

    async def load(self) -> list[LoadedDocument]:
        """Load postmortems from GitHub."""
        if not self.token:
            raise ValueError("GITHUB_TOKEN not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            url = f"https://api.github.com/repos/{self.repo}/contents/{self.path}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            documents = []
            for item in response.json():
                if item["type"] == "file" and item["name"].endswith(".md"):
                    content = await self._fetch_content(client, headers, item["download_url"])
                    if content:
                        documents.append(
                            LoadedDocument(
                                source_type="postmortem",
                                title=item["name"].replace(".md", ""),
                                content=content,
                                source_id=item["html_url"],
                                metadata={
                                    "github_path": item["path"],
                                    "doc_type": "postmortem",
                                    "repo": self.repo,
                                },
                            )
                        )
            return documents

    async def _fetch_content(
        self, client: httpx.AsyncClient, headers: dict, url: str
    ) -> str | None:
        """Fetch raw content from GitHub."""
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Warning: Failed to fetch {url}: {e}")
            return None
