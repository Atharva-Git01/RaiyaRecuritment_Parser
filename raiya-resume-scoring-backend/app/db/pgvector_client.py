"""
RAIYA pgvector Client — Vector storage and hybrid search using PostgreSQL 16 + pgvector.
Replaces Pinecone with local pgvector for all vector operations.
"""

from typing import List, Optional, Dict, Any
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger("pgvector_client")

# ── Embedding dimension (unified: BGE-large-en-v1.5) ────────────
PRIMARY_DIM = settings.EMBEDDING_DIMS_PRIMARY  # 768


async def ensure_pgvector_extension(session: AsyncSession) -> None:
    """Ensure pgvector extension is installed."""
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await session.commit()
    logger.info("pgvector extension ensured")


# ── Resume Embeddings ────────────────────────────────────────────

async def upsert_resume_embeddings(
    session: AsyncSession,
    resume_file_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """
    Upsert resume chunk embeddings into resume_embeddings table.
    
    Args:
        session: Async DB session
        resume_file_id: UUID of the resume
        chunks: List of chunk dicts with text, dimension, chunk_hash, chunk_index
        embeddings: List of embedding vectors (768-dim)
    
    Returns:
        Number of embeddings upserted
    """
    # Delete existing embeddings for this resume
    await session.execute(
        text("DELETE FROM resume_embeddings WHERE resume_file_id = :rid"),
        {"rid": resume_file_id}
    )

    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        await session.execute(
            text("""
                INSERT INTO resume_embeddings 
                (resume_file_id, chunk_index, dimension, chunk_text, embedding, chunk_hash, metadata)
                VALUES (:rid, :idx, :dim, :txt, :emb, :hash, :meta)
            """),
            {
                "rid": resume_file_id,
                "idx": chunk.get("chunk_index", count),
                "dim": chunk.get("dimension", "general"),
                "txt": chunk.get("text", ""),
                "emb": str(embedding),
                "hash": chunk.get("chunk_hash", ""),
                "meta": None,
            }
        )
        count += 1

    await session.commit()
    logger.info(f"Upserted {count} resume embeddings for file_id={resume_file_id}")
    return count


# ── JD Embeddings ────────────────────────────────────────────────

async def upsert_jd_embeddings(
    session: AsyncSession,
    jd_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """Upsert JD chunk embeddings into jd_embeddings table."""
    await session.execute(
        text("DELETE FROM jd_embeddings WHERE jd_id = :jid"),
        {"jid": jd_id}
    )

    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        await session.execute(
            text("""
                INSERT INTO jd_embeddings
                (jd_id, chunk_index, dimension, chunk_text, embedding, chunk_hash, metadata)
                VALUES (:jid, :idx, :dim, :txt, :emb, :hash, :meta)
            """),
            {
                "jid": jd_id,
                "idx": chunk.get("chunk_index", count),
                "dim": chunk.get("dimension", "general"),
                "txt": chunk.get("text", ""),
                "emb": str(embedding),
                "hash": chunk.get("chunk_hash", ""),
                "meta": None,
            }
        )
        count += 1

    await session.commit()
    logger.info(f"Upserted {count} JD embeddings for jd_id={jd_id}")
    return count


# ── RAG Evidence Embeddings ──────────────────────────────────────

async def upsert_evidence_embeddings(
    session: AsyncSession,
    evidence_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> int:
    """Upsert RAG evidence embeddings."""
    await session.execute(
        text("DELETE FROM rag_evidence_embeddings WHERE evidence_id = :eid"),
        {"eid": evidence_id}
    )

    count = 0
    for chunk, embedding in zip(chunks, embeddings):
        await session.execute(
            text("""
                INSERT INTO rag_evidence_embeddings
                (evidence_id, source_type, section_name, chunk_text, embedding, chunk_hash, metadata)
                VALUES (:eid, :stype, :sname, :txt, :emb, :hash, :meta)
            """),
            {
                "eid": evidence_id,
                "stype": chunk.get("source_type", "rule_based"),
                "sname": chunk.get("section_name", "general"),
                "txt": chunk.get("text", ""),
                "emb": str(embedding),
                "hash": chunk.get("chunk_hash", ""),
                "meta": None,
            }
        )
        count += 1

    await session.commit()
    logger.info(f"Upserted {count} evidence embeddings for evidence_id={evidence_id}")
    return count


# ── Vector Search ────────────────────────────────────────────────

async def search_resume_embeddings(
    session: AsyncSession,
    query_embedding: List[float],
    resume_file_id: Optional[str] = None,
    dimension: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search resume embeddings using cosine similarity.
    
    Returns list of dicts with: chunk_text, dimension, similarity, chunk_index
    """
    filters = []
    params: Dict[str, Any] = {"emb": str(query_embedding), "k": top_k}

    if resume_file_id:
        filters.append("resume_file_id = :rid")
        params["rid"] = resume_file_id
    if dimension:
        filters.append("dimension = :dim")
        params["dim"] = dimension

    where_clause = " AND ".join(filters) if filters else "1=1"

    result = await session.execute(
        text(f"""
            SELECT chunk_text, dimension, chunk_index, chunk_hash,
                   1 - (embedding <=> :emb::vector) as similarity
            FROM resume_embeddings
            WHERE {where_clause}
            ORDER BY embedding <=> :emb::vector
            LIMIT :k
        """),
        params
    )

    rows = result.fetchall()
    return [
        {
            "chunk_text": row[0],
            "dimension": row[1],
            "chunk_index": row[2],
            "chunk_hash": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]


async def search_jd_embeddings(
    session: AsyncSession,
    query_embedding: List[float],
    jd_id: Optional[str] = None,
    dimension: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Search JD embeddings using cosine similarity."""
    filters = []
    params: Dict[str, Any] = {"emb": str(query_embedding), "k": top_k}

    if jd_id:
        filters.append("jd_id = :jid")
        params["jid"] = jd_id
    if dimension:
        filters.append("dimension = :dim")
        params["dim"] = dimension

    where_clause = " AND ".join(filters) if filters else "1=1"

    result = await session.execute(
        text(f"""
            SELECT chunk_text, dimension, chunk_index, chunk_hash,
                   1 - (embedding <=> :emb::vector) as similarity
            FROM jd_embeddings
            WHERE {where_clause}
            ORDER BY embedding <=> :emb::vector
            LIMIT :k
        """),
        params
    )

    rows = result.fetchall()
    return [
        {
            "chunk_text": row[0],
            "dimension": row[1],
            "chunk_index": row[2],
            "chunk_hash": row[3],
            "similarity": float(row[4]),
        }
        for row in rows
    ]
