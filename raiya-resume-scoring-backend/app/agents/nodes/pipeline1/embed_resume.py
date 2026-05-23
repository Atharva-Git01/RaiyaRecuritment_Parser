"""
RAIYA Pipeline 1 Node — Embed Resume.
RecursiveJsonSplitter → BGE-large-en-v1.5 embed → pgvector store
"""

from typing import Dict, Any

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.embed_tool import embed_chunks_with_cache
from app.chunking.resume_chunker import chunk_resume_json
from app.core.logging_config import get_logger
from app.db.database import AsyncSessionLocal
from app.db.pgvector_client import upsert_resume_embeddings

logger = get_logger("EmbedResumeNode")


async def embed_resume_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 1 Step 3: Chunk and embed the resume JSON.
    Uses RecursiveJsonSplitter for section-aware chunking.
    Input: resume_parsed, resume_file_id
    Output: resume_chunks (stored in pgvector)
    """
    resume_parsed = state.get("resume_parsed", {})
    resume_file_id = state.get("resume_file_id")

    if not resume_file_id:
        return {"errors": state.get("errors", []) + ["No resume_file_id"]}

    try:
        # ── Chunk using RecursiveJsonSplitter ─────────────────
        chunks = chunk_resume_json(resume_parsed)
        logger.info(f"Resume chunked into {len(chunks)} chunks")

        if not chunks:
            return {
                "resume_chunks": [],
                "errors": state.get("errors", []) + ["No chunks generated from resume"],
            }

        # ── Embed chunks ─────────────────────────────────────
        embeddings = await embed_chunks_with_cache(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # ── Store in pgvector ────────────────────────────────
        async with AsyncSessionLocal() as session:
            count = await upsert_resume_embeddings(
                session, resume_file_id, chunks, embeddings
            )
            logger.info(f"Stored {count} resume embeddings in pgvector")

        return {"resume_chunks": chunks}

    except Exception as e:
        logger.error(f"Resume embedding failed: {e}")
        return {
            "resume_chunks": [],
            "errors": state.get("errors", []) + [f"Embedding failed: {str(e)}"],
        }
