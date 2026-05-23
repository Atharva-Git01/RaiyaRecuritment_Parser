"""
RAIYA Memory Persistence — LangGraph checkpoint + pipeline memory.

Provides:
1. `open_async_checkpointer()` — async context manager that yields an
   `AsyncPostgresSaver` for LangGraph state persistence. Must be opened
   inside the FastAPI lifespan so the underlying connection pool lives
   for the lifetime of the application.
2. `PipelineMemoryStore` — Pipeline execution audit log per session.
   Separate from LangGraph's checkpoint tables (state-of-truth); this
   table is human-readable audit only.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

from sqlalchemy import Column, String, DateTime, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.database import Base, sync_engine

logger = get_logger("MemoryPersistence")


# ── LangGraph Async Checkpoint Persistence ──────────────────────────

@asynccontextmanager
async def open_async_checkpointer() -> AsyncIterator[Any]:
    """
    Yield an `AsyncPostgresSaver` configured against `settings.DATABASE_URL`.

    This must be used inside an `async with` (typically in the FastAPI
    lifespan) — the underlying psycopg connection pool is opened on
    `__aenter__` and closed on `__aexit__`. `setup()` is idempotent and
    creates `checkpoints`, `checkpoint_writes`, `checkpoint_blobs` if
    they don't already exist.

    If `langgraph-checkpoint-postgres` is not installed, this yields
    `None` so the rest of the app can still boot (state simply will not
    persist across restarts).
    """
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError:
        logger.warning(
            "langgraph-checkpoint-postgres not installed — checkpointer disabled. "
            "Pipeline state will not persist across restarts."
        )
        yield None
        return

    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        try:
            await checkpointer.setup()
            logger.info("AsyncPostgresSaver initialised and tables ensured")
        except Exception as exc:
            # Setup is the only place a misconfigured DSN tends to surface.
            logger.error("AsyncPostgresSaver setup failed: %s", exc)
            raise
        yield checkpointer


# ── Pipeline Memory Store ───────────────────────────────────────────

class PipelineMemoryLog(Base):
    """Pipeline execution memory — tracks node completions per session."""
    __tablename__ = "pipeline_memory"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(80), nullable=False, index=True)
    batch_id = Column(String(80), nullable=True, index=True)
    node_name = Column(String(100), nullable=False)
    status = Column(String(30), default="started")  # started|completed|failed
    state_snapshot = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)


class PipelineMemoryStore:
    """
    Manages pipeline execution memory.

    Tracks which nodes completed, which failed, enabling:
    - Pipeline resume from last checkpoint after crash/restart
    - Execution audit trail
    - Performance analytics (node timing)
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def log_node_start(
        self, session_id: str, node_name: str, batch_id: Optional[str] = None
    ) -> int:
        """Log the start of a node execution."""
        async with self._session_factory() as session:
            log = PipelineMemoryLog(
                session_id=session_id,
                batch_id=batch_id,
                node_name=node_name,
                status="started",
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log.id

    async def log_node_complete(
        self,
        log_id: int,
        state_snapshot: Optional[Dict[str, Any]] = None,
    ):
        """Log the completion of a node execution."""
        from sqlalchemy import update

        async with self._session_factory() as session:
            await session.execute(
                update(PipelineMemoryLog)
                .where(PipelineMemoryLog.id == log_id)
                .values(
                    status="completed",
                    state_snapshot=state_snapshot,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def log_node_failure(
        self, log_id: int, error_message: str
    ):
        """Log a node execution failure."""
        from sqlalchemy import update

        async with self._session_factory() as session:
            await session.execute(
                update(PipelineMemoryLog)
                .where(PipelineMemoryLog.id == log_id)
                .values(
                    status="failed",
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def get_session_history(
        self, session_id: str
    ) -> list:
        """Get all memory logs for a session."""
        from sqlalchemy import select

        async with self._session_factory() as session:
            result = await session.execute(
                select(PipelineMemoryLog)
                .where(PipelineMemoryLog.session_id == session_id)
                .order_by(PipelineMemoryLog.started_at)
            )
            return result.scalars().all()

    async def get_last_completed_node(
        self, session_id: str
    ) -> Optional[str]:
        """Get the last successfully completed node for a session (for resume)."""
        from sqlalchemy import select

        async with self._session_factory() as session:
            result = await session.execute(
                select(PipelineMemoryLog.node_name)
                .where(PipelineMemoryLog.session_id == session_id)
                .where(PipelineMemoryLog.status == "completed")
                .order_by(PipelineMemoryLog.completed_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row


# ── Singleton ────────────────────────────────────────────────────────

_memory_store = None


def get_memory_store() -> PipelineMemoryStore:
    """Get the singleton PipelineMemoryStore instance."""
    global _memory_store
    if _memory_store is None:
        from app.db.database import AsyncSessionLocal
        _memory_store = PipelineMemoryStore(AsyncSessionLocal)
    return _memory_store
