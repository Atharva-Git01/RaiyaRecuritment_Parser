"""
RAIYA Reasoning Phase 4 — Cross Verifier.
Python-based label verification: checks each assigned label against
the similarity score range to detect mismatches and apply corrections.
"""

from typing import Dict, Any, List
from app.reasoning.reasoning_schemas import LABEL_DIMENSIONS
from app.core.logging_config import get_logger

logger = get_logger("CrossVerifier")


def cross_verify(
    labels: Dict[str, str],
    section_similarities: Dict[str, Any],
    evidence_map: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phase 4: Cross-Verification (Python, no LLM).
    Validates each label against the corresponding hybrid similarity score.
    If the score falls outside the label's range, the label is corrected.
    
    Returns:
        Dict with entries (list of verification results), total_corrections,
        and corrected labels dict.
    """
    from app.reasoning.reasoning_schemas import SECTION_TO_LABEL_DIMENSION

    entries = []
    corrections = 0
    corrected_labels = dict(labels)

    # Build a dimension → avg similarity map
    dimension_sims: Dict[str, List[float]] = {}
    for section_name, sim_data in section_similarities.items():
        dimension = SECTION_TO_LABEL_DIMENSION.get(section_name)
        if dimension:
            score = sim_data.get("hybrid_score", 0.0) if isinstance(sim_data, dict) else 0.0
            if dimension not in dimension_sims:
                dimension_sims[dimension] = []
            dimension_sims[dimension].append(score)

    for dimension, label in labels.items():
        ranges = LABEL_DIMENSIONS.get(dimension, {})
        expected_range = ranges.get(label, (0.0, 1.0))

        # Get average similarity for this dimension
        sims = dimension_sims.get(dimension, [0.5])
        avg_sim = sum(sims) / len(sims) if sims else 0.5

        # Check if score falls within label range
        lo, hi = expected_range
        in_range = lo <= avg_sim <= hi
        corrected = False
        verified_label = label
        reason = ""

        if not in_range:
            # Find the correct label for this score
            new_label = _find_label_for_score(dimension, avg_sim)
            if new_label != label:
                corrected = True
                verified_label = new_label
                corrections += 1
                reason = (
                    f"Score {avg_sim:.3f} outside range {expected_range} for label '{label}'. "
                    f"Corrected to '{new_label}'."
                )
                corrected_labels[dimension] = new_label
                logger.warning(f"Phase 4: {dimension} corrected: {label} → {new_label} "
                              f"(score={avg_sim:.3f})")
            else:
                reason = f"Score {avg_sim:.3f} marginally outside range but label unchanged."

        entries.append({
            "dimension": dimension,
            "original_label": label,
            "verified_label": verified_label,
            "similarity_score": round(avg_sim, 4),
            "expected_range": list(expected_range),
            "corrected": corrected,
            "reason": reason,
        })

    logger.info(f"Phase 4 complete: {corrections} corrections applied")

    return {
        "entries": entries,
        "total_corrections": corrections,
        "labels": corrected_labels,
    }


def _find_label_for_score(dimension: str, score: float) -> str:
    """Find the correct label for a given score in a dimension."""
    ranges = LABEL_DIMENSIONS.get(dimension, {})
    for label, (lo, hi) in ranges.items():
        if lo <= score <= hi:
            return label
    # Closest match
    if ranges:
        closest = min(
            ranges.items(),
            key=lambda x: abs(score - (x[1][0] + x[1][1]) / 2)
        )
        return closest[0]
    return "moderate"
