"""
RAIYA Pipeline 2 Node — Validate JD.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.agent_guardrails import AgentGuardrails, ValidationFailure
from app.core.logging_config import get_logger

logger = get_logger("ValidateJDNode")


async def validate_jd_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """Validate extracted JD JSON."""
    jd_extracted = state.get("jd_extracted")
    try:
        AgentGuardrails.validate_jd_schema(jd_extracted)
        logger.info("JD validation passed")
        return {"agent_state": "FETCHING_CONTEXT"}
    except ValidationFailure as e:
        logger.error(f"JD validation failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "agent_state": "FAILED",
        }
