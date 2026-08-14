#!/usr/bin/env python
"""CLI for document ingestion."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import init_db
from app.ingestion.loaders import MarkdownLoader, GitHubPostmortemLoader, PagerDutyLoader
from app.ingestion.pipeline import IngestionPipeline


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into On-Call Copilot")
    parser.add_argument(
        "--source",
        choices=["markdown", "github", "pagerduty"],
        required=True,
        help="Source type to ingest from",
    )
    parser.add_argument("--path", help="Directory path (for markdown source)")
    parser.add_argument("--repo", help="GitHub repo (for github source)")
    parser.add_argument("--since-days", type=int, default=30, help="Lookback days (for pagerduty)")
    args = parser.parse_args()

    # Initialize database
    await init_db()

    # Load documents
    print(f"Loading documents from {args.source}...")
    if args.source == "markdown":
        if not args.path:
            print("Error: --path required for markdown source")
            sys.exit(1)
        loader = MarkdownLoader(directory=args.path)
    elif args.source == "github":
        if not args.repo:
            print("Error: --repo required for github source")
            sys.exit(1)
        loader = GitHubPostmortemLoader(repo=args.repo)
    elif args.source == "pagerduty":
        loader = PagerDutyLoader(since_days=args.since_days)
    else:
        print(f"Unknown source: {args.source}")
        sys.exit(1)

    documents = await loader.load()
    print(f"Loaded {len(documents)} documents")

    if not documents:
        print("No documents to ingest")
        return

    # Run pipeline
    print("Running ingestion pipeline...")
    pipeline = IngestionPipeline()

    async def progress_callback(stats):
        print(f"  Progress: {stats}")

    stats = await pipeline.ingest_documents(documents, progress_callback=progress_callback)

    print(f"\nIngestion complete!")
    print(f"  Documents: {stats['documents']}")
    print(f"  Chunks: {stats['chunks']}")
    print(f"  Embeddings: {stats['embeddings']}")
    if stats["errors"]:
        print(f"  Errors: {len(stats['errors'])}")
        for e in stats["errors"]:
            print(f"    - {e}")


if __name__ == "__main__":
    asyncio.run(main())