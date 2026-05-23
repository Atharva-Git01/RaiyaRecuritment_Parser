"""
RAIYA Agent Controller — LangGraph pipeline build_graph() with all nodes + edges.

Target: LangGraph 0.6.x async runtime, AsyncPostgresSaver checkpointer.

Topology (per BACKEND_WORKFLOW.md):
  Pipeline 1 (JD):      extract_jd → validate_jd → jd_normalize → assign_weights
                                  → [hitl_pause if needs_review] → embed_jd
  Pipeline 2 (Resume):  extract_resume → validate_resume → embed_resume
  Pipeline 3 (Scoring): hybrid_search → reasoning_engine → rag_validation →
                        score_adjustment → final_validation → explanation_gen
                        → report_generator → END

Pipeline 4 (interview email) is NOT a graph node — it is a batch-level
service invoked by `batch_service.run_batch` after all per-resume graphs
in a batch complete.
"""

from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.agents import PipelineContext, PipelineState
from app.core.logging_config import get_logger

# Pipeline 1 nodes — JD Processing (runs first; lives in pipeline2/ directory).
from app.agents.nodes.pipeline2.extract_jd import extract_jd_node
from app.agents.nodes.pipeline2.validate_jd import validate_jd_node
from app.agents.nodes.pipeline2.jd_normalize import jd_normalize_node
from app.agents.nodes.pipeline2.assign_weights import assign_weights_node
from app.agents.nodes.pipeline2.hitl_pause import hitl_pause_node
from app.agents.nodes.pipeline2.embed_jd import embed_jd_node

# Pipeline 2 nodes — Resume Processing (lives in pipeline1/ directory).
from app.agents.nodes.pipeline1.extract_resume import extract_resume_node
from app.agents.nodes.pipeline1.validate_resume import validate_resume_node
from app.agents.nodes.pipeline1.embed_resume import embed_resume_node

# Pipeline 3 nodes — Scoring + Validation + Report.
from app.agents.nodes.pipeline3.hybrid_search import hybrid_search_node
from app.agents.nodes.pipeline3.reasoning_engine import reasoning_engine_node
from app.agents.nodes.pipeline3.rag_validation import rag_validation_node
from app.agents.nodes.pipeline3.score_adjustment import score_adjustment_node
from app.agents.nodes.pipeline3.final_validation import final_validation_node
from app.agents.nodes.pipeline3.explanation_gen import explanation_gen_node
from app.agents.nodes.pipeline3.report_generator import report_generator_node

logger = get_logger("AgentController")


# ── Error Handler ────────────────────────────────────────────────────

async def error_handler_node(state: dict) -> dict:
    """Terminal error handler — logs and marks the run failed."""
    errors = state.get("errors", []) or []
    logger.error("Pipeline failed with %d errors: %s", len(errors), errors)
    return {"agent_state": "FAILED"}


# ── Routing Functions ────────────────────────────────────────────────
#
# Each router returns one of the labels in its conditional-edge mapping.
# Labels match the table in BACKEND_WORKFLOW.md § "Branching".

def route_jd_validation(state: dict) -> str:
    """`validate_jd` → PASS / FAIL."""
    if state.get("agent_state") == "FAILED":
        return "FAIL"
    return "PASS"


def route_weights_outcome(state: dict) -> str:
    """
    `assign_weights` → auto_verified / needs_review / FAIL.

    If the upstream batch orchestrator pre-approved the JD (hitl_verified
    injected into state), skip the HITL gate. Otherwise pause for review.
    """
    if state.get("agent_state") == "FAILED":
        return "FAIL"
    jd_weights = state.get("jd_weights") or {}
    if not jd_weights:
        return "FAIL"
    if state.get("hitl_verified"):
        return "auto_verified"
    return "needs_review"


def route_resume_validation(state: dict) -> str:
    """`validate_resume` → PASS / FAIL."""
    if state.get("agent_state") == "FAILED":
        return "FAIL"
    return "PASS"


def route_hybrid_search(state: dict) -> str:
    if state.get("agent_state") == "FAILED" or not state.get("section_similarities"):
        return "FAIL"
    return "PASS"


def route_rag(state: dict) -> str:
    if state.get("agent_state") == "FAILED":
        return "FAIL"
    return "PASS"


def route_final_validation(state: dict) -> str:
    if state.get("agent_state") == "FAILED":
        return "FAIL"
    return "PASS"


# ── Build Graph ──────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Build the per-resume LangGraph pipeline.

    Args:
        checkpointer: An `AsyncPostgresSaver` (or None for in-memory).
                      When provided, `interrupt_before=["hitl_pause"]` is
                      wired so the HITL gate can pause/resume across HTTP
                      requests via `Command(resume=...)`.

    Returns:
        A `CompiledStateGraph` ready to call `.ainvoke(...)` against.
    """
    g = StateGraph(state_schema=PipelineState, context_schema=PipelineContext)

    # ── Pipeline 1 — JD (runs first) ─────────────────────────────
    g.add_node("extract_jd", extract_jd_node)
    g.add_node("validate_jd", validate_jd_node)
    g.add_node("jd_normalize", jd_normalize_node)
    g.add_node("assign_weights", assign_weights_node)
    g.add_node("hitl_pause", hitl_pause_node)
    g.add_node("embed_jd", embed_jd_node)

    # ── Pipeline 2 — Resume (after JD weights embedded) ──────────
    g.add_node("extract_resume", extract_resume_node)
    g.add_node("validate_resume", validate_resume_node)
    g.add_node("embed_resume", embed_resume_node)

    # ── Pipeline 3 — Scoring + Report ────────────────────────────
    g.add_node("hybrid_search", hybrid_search_node)
    g.add_node("reasoning_engine", reasoning_engine_node)
    g.add_node("rag_validation", rag_validation_node)
    g.add_node("score_adjustment", score_adjustment_node)
    g.add_node("final_validation", final_validation_node)
    g.add_node("explanation_gen", explanation_gen_node)
    g.add_node("report_generator", report_generator_node)
    g.add_node("error_handler", error_handler_node)

    # ── Entry point: JD first ────────────────────────────────────
    g.add_edge(START, "extract_jd")

    # ── Pipeline 1 linear edges ──────────────────────────────────
    g.add_edge("extract_jd", "validate_jd")
    g.add_edge("jd_normalize", "assign_weights")
    # hitl_pause has no outgoing router — it always continues to embed_jd
    # once the human approves via Command(resume=...).
    g.add_edge("hitl_pause", "embed_jd")
    g.add_edge("embed_jd", "extract_resume")

    # ── Pipeline 2 linear edges ──────────────────────────────────
    g.add_edge("extract_resume", "validate_resume")
    g.add_edge("embed_resume", "hybrid_search")

    # ── Pipeline 3 linear edges ──────────────────────────────────
    g.add_edge("hybrid_search", "reasoning_engine")
    g.add_edge("reasoning_engine", "rag_validation")
    g.add_edge("score_adjustment", "final_validation")
    g.add_edge("explanation_gen", "report_generator")
    # Pipeline 4 is batch-level (services/email_service.py), not a graph
    # node — `report_generator` is the terminal node.
    g.add_edge("report_generator", END)
    g.add_edge("error_handler", END)

    # ── Conditional edges ────────────────────────────────────────
    g.add_conditional_edges(
        "validate_jd", route_jd_validation,
        {"PASS": "jd_normalize", "FAIL": "error_handler"},
    )
    g.add_conditional_edges(
        "assign_weights", route_weights_outcome,
        {
            "auto_verified": "embed_jd",
            "needs_review": "hitl_pause",
            "FAIL": "error_handler",
        },
    )
    g.add_conditional_edges(
        "validate_resume", route_resume_validation,
        {"PASS": "embed_resume", "FAIL": "error_handler"},
    )
    g.add_conditional_edges(
        "hybrid_search", route_hybrid_search,
        {"PASS": "reasoning_engine", "FAIL": "error_handler"},
    )
    g.add_conditional_edges(
        "rag_validation", route_rag,
        {"PASS": "score_adjustment", "FAIL": "error_handler"},
    )
    g.add_conditional_edges(
        "final_validation", route_final_validation,
        {"PASS": "explanation_gen", "FAIL": "error_handler"},
    )

    # ── Compile ──────────────────────────────────────────────────
    compile_kwargs: Dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
        compile_kwargs["interrupt_before"] = ["hitl_pause"]

    compiled = g.compile(**compile_kwargs)
    logger.info(
        "LangGraph pipeline compiled (checkpointer=%s)",
        "AsyncPostgresSaver" if checkpointer is not None else "None",
    )
    return compiled
