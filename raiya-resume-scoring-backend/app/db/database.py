"""
RAIYA Database — SQLAlchemy async + sync engines for PostgreSQL 16.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("database")


# ── Async Engine (for FastAPI routes) ────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
logger.info(f"Async database engine initialized (host: {async_engine.url.host}, port: {async_engine.url.port})")

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync Engine (for LangGraph PostgresSaver, Alembic) ───────────

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)
logger.info(f"Sync database engine initialized (host: {sync_engine.url.host}, port: {sync_engine.url.port})")

SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)


# ── Base class for ORM models ────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Dependency for FastAPI ───────────────────────────────────────

async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Get a synchronous database session."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Startup / Shutdown ───────────────────────────────────────────

async def init_db():
    """Create all tables (for development only — use Alembic in production)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db():
    """Dispose of the async engine on shutdown."""
    await async_engine.dispose()
    logger.info("Database connections closed")
