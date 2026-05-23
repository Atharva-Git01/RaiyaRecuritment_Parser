"""
RAIYA Pipeline 3 Node — Hybrid Search.
Dense (BGE) + BM25 + Exact match → RRF fusion per JD section.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.search_tool import hybrid_search_per_section
from app.core.logging_config import get_logger
from app.db.database import AsyncSessionLocal

logger = get_logger("HybridSearchNode")


async def hybrid_search_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 3 Step 1: Hybrid search per section.
    Output: section_similarities dict.
    """
    resume_file_id = state.get("resume_file_id")
    jd_weights = state.get("jd_weights", {})
    resume_parsed = state.get("resume_parsed", {})
    resume_hash = state.get("resume_content_hash", "")
    jd_hash = state.get("jd_content_hash", "")
    weights_hash = state.get("weights_hash", "")

    try:
        async with AsyncSessionLocal() as session:
            section_sims = await hybrid_search_per_section(
                resume_file_id=resume_file_id,
                jd_weights=jd_weights,
                resume_parsed=resume_parsed,
                session=session,
                resume_hash=resume_hash,
                jd_hash=jd_hash,
                weights_hash=weights_hash,
            )

        logger.info(f"Hybrid search complete: {len(section_sims)} sections")
        return {"section_similarities": section_sims}

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        return {
            "section_similarities": {},
            "errors": state.get("errors", []) + [f"Hybrid search failed: {str(e)}"],
        }
