"""
RAIYA Backend — FastAPI Application Entry Point.
AI-Powered Resume Screening Backend by SpeedTech.ai.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.agent_controller import build_graph
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db.database import AsyncSessionLocal, init_db, close_db
from app.db import redis_client as _redis_module
from app.db.memory_persistence import get_memory_store, open_async_checkpointer
from app.db.redis_client import init_redis, close_redis

# Initialize logging
setup_logging(level="INFO" if settings.APP_ENV == "development" else "WARNING")
logger = get_logger("main")


def _build_pipeline_context() -> dict:
    """
    Assemble the runtime context that gets handed to every LangGraph node
    as `Runtime[PipelineContext]`. The dict layout mirrors PipelineContext.

    Built once at startup so nodes can pull stable handles instead of
    re-resolving them per invocation. Tool wrappers (ocr, embedder, llm,
    smtp) remain lazily imported by the individual nodes — adding them
    here is a no-op until a node opts in to reading from runtime.context.
    """
    return {
        "db": AsyncSessionLocal,
        "redis": _redis_module.redis_client,  # singleton initialised by init_redis()
        "memory": get_memory_store(),
        "settings": settings,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — startup and shutdown.

    Holds the `AsyncPostgresSaver` context open for the lifetime of the
    application, compiles the LangGraph pipeline once, and binds both
    to `app.state` so routes can reuse them.
    """
    logger.info("Starting RAIYA Backend...")
    await init_db()
    await init_redis()

    async with open_async_checkpointer() as checkpointer:
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer=checkpointer)
        app.state.pipeline_context = _build_pipeline_context()
        logger.info(
            "LangGraph pipeline ready (checkpointer=%s)",
            "AsyncPostgresSaver" if checkpointer is not None else "None",
        )
        logger.info("RAIYA Backend started successfully")
        yield
        logger.info("Shutting down RAIYA Backend...")

    await close_redis()
    await close_db()
    logger.info("RAIYA Backend shut down")


app = FastAPI(
    title="RAIYA — AI-Powered Resume Screening",
    description="Resume scoring backend with LangGraph agentic pipeline, "
                "BGE embeddings, pgvector, and Guardrails AI validation.",
    version="8.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — health check."""
    return {
        "service": "RAIYA Resume Scoring Backend",
        "version": "8.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check.

    Surfaces whether the LangGraph pipeline compiled and which checkpointer
    backs it. The workflow doc's verification step 3 ("Graph compile") is a
    one-line `curl /health` against this endpoint.
    """
    graph = getattr(app.state, "graph", None)
    checkpointer = getattr(app.state, "checkpointer", None)
    return {
        "status": "healthy",
        "service": "raiya-backend",
        "version": "8.0.0",
        "environment": settings.APP_ENV,
        "graph_ready": graph is not None,
        "checkpointer": (
            "AsyncPostgresSaver" if checkpointer is not None else "none"
        ),
    }
