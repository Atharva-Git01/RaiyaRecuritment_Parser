"""
RAIYA Pipeline 1 Node — Embed JD Weights.
After JD weight assignment is validated (HiTL or auto-verified),
chunk the JD weights/criteria and embed into pgvector (jd_embeddings table).

Uses BGE-large-en-v1.5 (768-dim) — same model as resume embeddings.
This enables hybrid_search to compare resume embeddings against JD embeddings
for per-section similarity scoring.
"""

from typing import Dict, Any

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.embed_tool import embed_chunks_with_cache
from app.chunking.jd_chunker import chunk_jd_json
from app.core.logging_config import get_logger
from app.db.database import AsyncSessionLocal
from app.db.pgvector_client import upsert_jd_embeddings

logger = get_logger("EmbedJDNode")


async def embed_jd_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Embed JD weights and criteria into pgvector for hybrid search.

    Runs after weight assignment is validated (HiTL approved or auto-verified).
    Uses criteria-aware chunking: each scoring section is split independently.

    Input: jd_normalized, jd_weights, jd_id
    Output: jd_embeddings stored in pgvector (jd_embeddings table)
    """
    jd_normalized = state.get("jd_normalized", {})
    jd_weights = state.get("jd_weights", {})
    jd_id = state.get("jd_id")

    if not jd_id:
        return {"errors": state.get("errors", []) + ["No jd_id for embedding"]}

    if not jd_weights.get("scoring"):
        return {
            "errors": state.get("errors", []) + ["No scoring sections in jd_weights"],
        }

    try:
        # ── Chunk JD using criteria-aware chunker ────────────
        chunks = chunk_jd_json(jd_normalized, jd_weights)
        logger.info(f"JD chunked into {len(chunks)} criteria-aware chunks")

        if not chunks:
            return {
                "errors": state.get("errors", []) + ["No chunks generated from JD"],
            }

        # ── Embed chunks (BGE-large-en-v1.5, 768-dim) ───────
        embeddings = await embed_chunks_with_cache(chunks)
        logger.info(f"Generated {len(embeddings)} JD embeddings")

        # ── Store in pgvector (jd_embeddings table) ──────────
        async with AsyncSessionLocal() as session:
            count = await upsert_jd_embeddings(
                session, jd_id, chunks, embeddings
            )
            logger.info(f"Stored {count} JD embeddings in pgvector")

        return {}

    except Exception as e:
        logger.error(f"JD embedding failed: {e}")
        return {
            "errors": state.get("errors", []) + [f"JD embedding failed: {str(e)}"],
        }
