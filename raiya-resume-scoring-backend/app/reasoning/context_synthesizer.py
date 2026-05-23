"""
RAIYA Reasoning Phase 5 — Context Synthesizer.
Produces a narrative reasoning context for the RAG validation layer.
LLM-based (temp=0.0) for consistency.
"""

from typing import Dict, Any
from app.core.logging_config import get_logger

logger = get_logger("ContextSynthesizer")


def synthesize_context(
    structural_facts: Dict[str, Any],
    evidence_map: Dict[str, Any],
    verified_labels: Dict[str, str],
    verification_report: Dict[str, Any],
    section_similarities: Dict[str, Any],
) -> str:
    """
    Phase 5: Context Synthesis (deterministic template-based).
    Produces a narrative reasoning context from all previous phases.
    This narrative is the primary grounding input for the RAG validation layer.
    
    Returns:
        Narrative string summarizing the reasoning process.
    """
    parts = []

    # Resume completeness
    completeness = structural_facts.get("resume_completeness", 0.0)
    parts.append(f"Resume Completeness: {completeness:.0%}")

    # Structural observations
    facts = structural_facts.get("facts", [])
    present_fields = [f["field"] for f in facts if f.get("present")]
    missing_fields = [f["field"] for f in facts if not f.get("present")]
    if present_fields:
        parts.append(f"Present fields: {', '.join(present_fields)}")
    if missing_fields:
        parts.append(f"Missing fields: {', '.join(missing_fields)}")

    parts.append("")

    # Evidence classification summary
    evidence_entries = evidence_map.get("entries", {})
    parts.append("Evidence Classification:")
    for section, entry in evidence_entries.items():
        classification = entry.get("classification", "ABSENT")
        matched = entry.get("matched_items", [])
        missing = entry.get("missing_items", [])
        conf = entry.get("confidence", 0.0)
        parts.append(
            f"  {section}: {classification} "
            f"(matched={len(matched)}, missing={len(missing)}, conf={conf:.2f})"
        )

    parts.append("")

    # Verified labels
    parts.append("Verified Labels:")
    for dim, label in verified_labels.items():
        sim_scores = []
        for section, sim_data in section_similarities.items():
            from app.reasoning.reasoning_schemas import SECTION_TO_LABEL_DIMENSION
            if SECTION_TO_LABEL_DIMENSION.get(section) == dim:
                score = sim_data.get("hybrid_score", 0.0) if isinstance(sim_data, dict) else 0.0
                sim_scores.append(score)
        avg_sim = sum(sim_scores) / len(sim_scores) if sim_scores else 0.0
        parts.append(f"  {dim}: {label} (avg_similarity={avg_sim:.3f})")

    # Corrections
    corrections = verification_report.get("total_corrections", 0)
    if corrections > 0:
        parts.append(f"\nLabel Corrections Applied: {corrections}")
        for entry in verification_report.get("entries", []):
            if entry.get("corrected"):
                parts.append(
                    f"  {entry['dimension']}: {entry['original_label']} → "
                    f"{entry['verified_label']} ({entry['reason']})"
                )

    narrative = "\n".join(parts)
    logger.info(f"Phase 5 complete: context synthesized ({len(narrative)} chars)")

    return narrative
