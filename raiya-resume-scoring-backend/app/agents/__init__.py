"""
RAIYA Agent State — Pipeline state management for LangGraph.
Updated for LangGraph TypedDict-based state with all pipeline fields.
"""

from typing import TypedDict, Optional, Dict, List, Any
from enum import Enum


class AgentState(str, Enum):
    """Finite states for the Agent FSM."""
    INIT = "INIT"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    FETCHING_CONTEXT = "FETCHING_CONTEXT"
    SCORING = "SCORING"
    VERIFYING_OUTPUT = "VERIFYING_OUTPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineState(TypedDict, total=False):
    """
    LangGraph pipeline state — passed between all nodes.
    All fields are optional since they are populated progressively.
    """
    # ── Identifiers ──────────────────────────────────────────────
    batch_id: str
    resume_file_id: str
    jd_id: str
    session_id: str

    # ── Pipeline 1 outputs ───────────────────────────────────────
    resume_file_bytes: bytes
    resume_file_hash: str
    resume_parsed: Dict[str, Any]          # resume_pdf_extraction_schema
    resume_content_hash: str
    resume_chunks: List[Dict[str, Any]]

    # ── Pipeline 2 outputs ───────────────────────────────────────
    jd_file_bytes: bytes
    jd_file_hash: str
    jd_extracted: Dict[str, Any]           # jd_pdf_extraction_schema
    jd_normalized: Dict[str, Any]
    jd_weights: Dict[str, Any]             # jd_weights_schema_format
    jd_content_hash: str
    weights_hash: str
    hitl_verified: bool

    # ── Pipeline 3 outputs ───────────────────────────────────────
    section_similarities: Dict[str, Dict[str, float]]
    reasoning_labels: Dict[str, str]
    reasoning_context: str
    structural_facts: Dict[str, Any]
    evidence_map: Dict[str, str]
    verification_report: Dict[str, Any]

    # RAG validation outputs
    deterministic_report: Dict[str, Any]
    mathematical_report: Dict[str, Any]
    rule_based_evidence: Dict[str, Any]
    rag_final_verdict: Dict[str, Any]

    # Score adjustment
    match_output: Dict[str, Any]           # final_result_scoring_agent_schema
    final_score: float
    output_hash: str

    # Explanation
    llm_explanation: str
    explanation_hash: str

    # Report
    report_path: str
    report_hash: str

    # ── Agent metadata ───────────────────────────────────────────
    agent_state: str
    agent_memory_history: List[Dict[str, Any]]
    token_usage_summary: Dict[str, Any]
    errors: List[str]
    cache_hits: List[str]


class PipelineContext(TypedDict, total=False):
    """
    Runtime context injected into every node via Runtime[PipelineContext].

    Per BACKEND_WORKFLOW.md, runtime dependencies are not module globals —
    they are injected so they survive checkpoint resume and remain mockable.
    All fields are optional so tests can build minimal contexts.
    """
    db: Any            # AsyncSessionLocal factory (sqlalchemy.ext.asyncio.async_sessionmaker)
    redis: Any         # redis.asyncio.Redis client
    embedder: Any      # BGE-large-en-v1.5 wrapper
    ocr: Any           # Nanonets DocStrange client
    llm: Any           # Azure Phi-4 inference client
    smtp: Any          # aiosmtplib client (Pipeline 4 only — not used by the graph)
    memory: Any        # PipelineMemoryStore (optional audit log)
    settings: Any      # app.core.config.Settings instance
