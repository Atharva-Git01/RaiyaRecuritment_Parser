"""
RAIYA Reasoning Engine Core — Orchestrates all 5 phases.

Phase 1: StructuralAnalyzer (temp=0.0)    → structural_facts
Phase 2: EvidenceClassifier (Python)       → evidence_map [EXPLICIT|PARTIAL|ABSENT]
Phase 3: LabelAssigner (LLM ReAct)         → reasoning_labels [categorical]
Phase 4: CrossVerifier (Python)             → verified_labels [label vs similarity range]
Phase 5: ContextSynthesizer (LLM temp=0.0) → reasoning_context
"""

from typing import Dict, Any, Tuple

from app.reasoning.structural_analyzer import analyze_structure
from app.reasoning.evidence_classifier import classify_evidence
from app.reasoning.label_assigner import assign_labels
from app.reasoning.cross_verifier import cross_verify
from app.reasoning.context_synthesizer import synthesize_context
from app.reasoning.reasoning_cache import get_cached_reasoning, set_cached_reasoning
from app.core.hashing import hash_json
from app.core.logging_config import get_logger

logger = get_logger("ReasoningEngineCore")


async def run_reasoning_engine(
    resume_parsed: Dict[str, Any],
    jd_weights: Dict[str, Any],
    section_similarities: Dict[str, Any],
    resume_hash: str,
    jd_hash: str,
    weights_hash: str,
) -> Dict[str, Any]:
    """
    Execute the full 5-phase reasoning engine.
    
    Args:
        resume_parsed: Resume JSON (resume_pdf_extraction_schema)
        jd_weights: JD weights JSON (jd_weights_schema_format)
        section_similarities: Hybrid search results per section
        resume_hash: SHA-256 hash of resume content
        jd_hash: SHA-256 hash of JD content
        weights_hash: SHA-256 hash of JD weights
    
    Returns:
        Complete reasoning output with all 5 phase results.
    """
    # ── Check cache ──────────────────────────────────────────────
    cached = await get_cached_reasoning(resume_hash, jd_hash, weights_hash)
    if cached:
        logger.info("Reasoning engine: cache HIT, skipping computation")
        return cached

    logger.info("Reasoning engine: starting 5-phase analysis")

    # ── Phase 1: Structural Analysis ─────────────────────────────
    logger.info("Phase 1: Structural Analysis")
    structural_facts = analyze_structure(resume_parsed)

    # ── Phase 2: Evidence Classification ─────────────────────────
    logger.info("Phase 2: Evidence Classification")
    evidence_map = classify_evidence(resume_parsed, jd_weights, section_similarities)

    # ── Phase 3: Label Assignment ────────────────────────────────
    logger.info("Phase 3: Label Assignment")
    raw_labels = assign_labels(evidence_map, section_similarities, structural_facts)

    # ── Phase 4: Cross Verification ──────────────────────────────
    logger.info("Phase 4: Cross Verification")
    verification_result = cross_verify(raw_labels, section_similarities, evidence_map)
    verified_labels = verification_result["labels"]
    corrections = verification_result["total_corrections"]

    # ── Phase 5: Context Synthesis ───────────────────────────────
    logger.info("Phase 5: Context Synthesis")
    reasoning_context = synthesize_context(
        structural_facts, evidence_map, verified_labels,
        verification_result, section_similarities
    )

    # ── Build output ─────────────────────────────────────────────
    output = {
        "structural_facts": structural_facts,
        "evidence_map": evidence_map,
        "reasoning_labels": verified_labels,
        "verification_report": verification_result,
        "reasoning_context": reasoning_context,
        "phases_completed": 5,
        "corrections_applied": corrections,
    }

    # Compute reasoning hash
    reasoning_hash = hash_json(output)
    output["reasoning_hash"] = reasoning_hash

    # ── Cache result ─────────────────────────────────────────────
    await set_cached_reasoning(resume_hash, jd_hash, weights_hash, output)

    logger.info(
        f"Reasoning engine complete: labels={verified_labels}, "
        f"corrections={corrections}, hash={reasoning_hash[:20]}..."
    )

    return output
