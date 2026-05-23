"""
RAIYA Pipeline 3 Node — Reasoning Engine.
5-phase reasoning: structural → evidence → labels → verify → context.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.core.logging_config import get_logger
from app.reasoning.reasoning_engine_core import run_reasoning_engine

logger = get_logger("ReasoningEngineNode")


async def reasoning_engine_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 3 Step 2: Run 5-phase reasoning engine.
    Output: reasoning_labels, reasoning_context, structural_facts, evidence_map, verification_report.
    """
    resume_parsed = state.get("resume_parsed", {})
    jd_weights = state.get("jd_weights", {})
    section_sims = state.get("section_similarities", {})
    resume_hash = state.get("resume_content_hash", "")
    jd_hash = state.get("jd_content_hash", "")
    weights_hash = state.get("weights_hash", "")

    try:
        output = await run_reasoning_engine(
            resume_parsed=resume_parsed,
            jd_weights=jd_weights,
            section_similarities=section_sims,
            resume_hash=resume_hash,
            jd_hash=jd_hash,
            weights_hash=weights_hash,
        )

        logger.info(f"Reasoning engine complete: {output.get('phases_completed', 0)} phases")

        return {
            "structural_facts": output.get("structural_facts", {}),
            "evidence_map": output.get("evidence_map", {}),
            "reasoning_labels": output.get("reasoning_labels", {}),
            "verification_report": output.get("verification_report", {}),
            "reasoning_context": output.get("reasoning_context", ""),
        }
    except Exception as e:
        logger.error(f"Reasoning engine failed: {e}")
        return {
            "reasoning_labels": {},
            "reasoning_context": "",
            "errors": state.get("errors", []) + [f"Reasoning failed: {str(e)}"],
        }
