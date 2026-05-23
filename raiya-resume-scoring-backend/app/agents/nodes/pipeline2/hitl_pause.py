"""
RAIYA Pipeline 2 Node — HITL Pause.
LangGraph interrupt_before point for human-in-the-loop weight verification.

In the 14-phase enterprise pipeline, the full weight JSON (with reasoning_label +
confidence + evidence per criterion) is available for human inspection.
On approval, weighting_metadata.hitl_review.reviewed_by_human is set to True.
"""

from datetime import datetime, timezone

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.core.hashing import hash_json
from app.core.logging_config import get_logger

logger = get_logger("HITLPauseNode")


async def hitl_pause_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    HITL pause — LangGraph interrupts BEFORE this node via the compile-time
    `interrupt_before=["hitl_pause"]` on the graph.

    The orchestrator pauses with the JD weights checkpointed; the human
    reviews them (full enterprise schema with reasoning labels) and resumes
    with `Command(resume={"hitl_verified": True, "jd_weights": approved})`.
    The resume payload is merged into state before this node runs.

    On entry the state should have:
      hitl_verified: True
      jd_weights:   (potentially updated by human)
      weights_hash: (will be recomputed below if weights were edited)
    """
    hitl_verified = state.get("hitl_verified", False)

    if not hitl_verified:
        logger.info("HITL: Waiting for human verification…")
        return {
            "agent_state": "VERIFYING_OUTPUT",
            "hitl_verified": False,
        }

    # Human has approved — mark reviewed_by_human in weighting_metadata and
    # recompute the weights hash if the dict was modified.
    delta: dict = {"agent_state": "SCORING"}
    weights: dict = state.get("jd_weights", {})
    wm = weights.get("weighting_metadata")
    if isinstance(wm, dict):
        hitl_review = wm.get("hitl_review")
        if isinstance(hitl_review, dict) and not hitl_review.get("reviewed_by_human"):
            hitl_review["reviewed_by_human"] = True
            hitl_review["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            delta["jd_weights"] = weights
            delta["weights_hash"] = hash_json(weights)

    logger.info(
        "HITL: Weights verified by human — labels_modified=%s",
        weights.get("weighting_metadata", {})
        .get("hitl_review", {})
        .get("labels_modified", 0),
    )
    return delta
