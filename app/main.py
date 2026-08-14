"""FastAPI application factory for On-Call Copilot."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat_router, health_router, ingest_router
from app.config import settings
from app.database import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logging.info("Starting On-Call Copilot API")

    yield

    # Shutdown
    logging.info("Shutting down On-Call Copilot API")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="On-Call Copilot API",
        description="RAG-powered incident response assistant for on-call engineers",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.ENVIRONMENT == "development" else ["http://localhost:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(health_router)
    api_router.include_router(chat_router)
    api_router.include_router(ingest_router)
    app.include_router(api_router)

    # Root redirect to docs
    @app.get("/")
    async def root():
        return {
            "name": "On-Call Copilot API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
