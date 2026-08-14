"""Ingestion API endpoints."""

import uuid
from enum import Enum
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db_session
from app.ingestion.loaders import MarkdownLoader, GitHubPostmortemLoader, PagerDutyLoader
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/ingest", tags=["ingest"])

# In-memory job tracking (replace with Redis in production)
ingestion_jobs: dict[str, dict] = {}


class SourceType(str, Enum):
    MARKDOWN = "markdown"
    GITHUB = "github"
    PAGERDUTY = "pagerduty"


class IngestionRequest(BaseModel):
    """Request to trigger ingestion."""
    source: SourceType
    path: Optional[str] = None  # For markdown: directory path
    repo: Optional[str] = None  # For github: org/repo
    since_days: Optional[int] = 30  # For pagerduty: lookback window


@router.post("")
async def trigger_ingestion(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger document ingestion."""
    job_id = str(uuid.uuid4())

    ingestion_jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "source": request.source,
        "progress": 0,
        "created_at": "2026-08-13T12:00:00Z",
    }

    background_tasks.add_task(
        run_ingestion_job,
        job_id=job_id,
        source=request.source,
        path=request.path,
        repo=request.repo,
        since_days=request.since_days,
    )

    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}")
async def get_ingestion_status(job_id: str):
    """Get ingestion job status."""
    job = ingestion_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def run_ingestion_job(
    job_id: str,
    source: str,
    path: Optional[str] = None,
    repo: Optional[str] = None,
    since_days: int = 30,
):
    """Background task to run ingestion."""
    try:
        ingestion_jobs[job_id]["status"] = "running"

        # Load documents
        if source == SourceType.MARKDOWN:
            loader = MarkdownLoader(directory=path or "./demo_docs")
            documents = await loader.load()
        elif source == SourceType.GITHUB:
            loader = GitHubPostmortemLoader(repo=repo or "your-org/your-postmortems-repo")
            documents = await loader.load()
        elif source == SourceType.PAGERDUTY:
            loader = PagerDutyLoader(since_days=since_days)
            documents = await loader.load()
        else:
            raise ValueError(f"Unknown source: {source}")

        ingestion_jobs[job_id]["documents_loaded"] = len(documents)

        # Run pipeline
        pipeline = IngestionPipeline()
        stats = await pipeline.ingest_documents(documents)

        ingestion_jobs[job_id].update(
            {
                "status": "completed",
                "stats": stats,
            }
        )

    except Exception as e:
        ingestion_jobs[job_id].update(
            {
                "status": "failed",
                "error": str(e),
            }
        )
