"""
RAIYA Pipeline 1 Node — Validate Resume.
Pydantic validation against resume_pdf_extraction_schema.
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.agent_guardrails import AgentGuardrails, ValidationFailure
from app.core.logging_config import get_logger

logger = get_logger("ValidateResumeNode")


async def validate_resume_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 1 Step 2: Validate extracted resume JSON.
    Input: resume_parsed
    Output: validated state with agent_state update
    """
    resume_parsed = state.get("resume_parsed")

    try:
        AgentGuardrails.validate_resume_schema(resume_parsed)

        # Optional: Pydantic validation
        try:
            from app.schemas.resume import ResumeExtractionSchema
            ResumeExtractionSchema(**resume_parsed)
        except Exception as ve:
            logger.warning(f"Pydantic validation warning (non-fatal): {ve}")

        logger.info("Resume validation passed")
        return {"agent_state": "FETCHING_CONTEXT"}
    except ValidationFailure as e:
        logger.error(f"Resume validation failed: {e}")
        return {
            "errors": state.get("errors", []) + [f"Resume validation failed: {str(e)}"],
            "agent_state": "FAILED",
        }
