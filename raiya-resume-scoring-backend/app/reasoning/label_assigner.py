"""
RAIYA Reasoning Phase 3 — Label Assigner.
Assigns categorical labels per dimension based on evidence classification
and similarity scores. Uses ReAct pattern with LLM (temp=0.1).
"""

from typing import Dict, Any
from app.reasoning.reasoning_schemas import LABEL_DIMENSIONS, SECTION_TO_LABEL_DIMENSION
from app.core.logging_config import get_logger

logger = get_logger("LabelAssigner")


def assign_labels(
    evidence_map: Dict[str, Any],
    section_similarities: Dict[str, Any],
    structural_facts: Dict[str, Any],
) -> Dict[str, str]:
    """
    Phase 3: Label Assignment (deterministic fallback — no LLM required).
    Maps each scoring section to its label dimension and assigns
    a categorical label based on hybrid similarity score and evidence classification.
    
    Returns:
        Dict mapping dimension → label string.
    """
    entries = evidence_map.get("entries", {})
    labels = {}
    
    # Track per-dimension scores (average across sections mapping to same dimension)
    dimension_scores: Dict[str, list] = {}

    for section_name, evidence in entries.items():
        dimension = SECTION_TO_LABEL_DIMENSION.get(section_name)
        if not dimension:
            continue

        sim_data = section_similarities.get(section_name, {})
        hybrid_score = sim_data.get("hybrid_score", 0.0)
        classification = evidence.get("classification", "ABSENT")

        # Adjust score based on evidence classification
        adjusted_score = hybrid_score
        if classification == "ABSENT":
            adjusted_score = min(adjusted_score, 0.25)
        elif classification == "PARTIAL":
            adjusted_score = min(adjusted_score, 0.79)

        if dimension not in dimension_scores:
            dimension_scores[dimension] = []
        dimension_scores[dimension].append(adjusted_score)

    # Assign labels per dimension
    for dimension, scores in dimension_scores.items():
        avg_score = sum(scores) / len(scores) if scores else 0.0
        label = _score_to_label(dimension, avg_score)
        labels[dimension] = label
        logger.info(f"Phase 3: {dimension} → {label} (avg_score={avg_score:.3f})")

    # Ensure all dimensions have a label (defaults)
    default_labels = {
        "technical_fit": "moderate",
        "experience_fit": "meets",
        "seniority_fit": "match",
        "education_fit": "meets",
        "domain_fit": "moderate",
        "certification_fit": "some_present",
        "tool_fit": "partial",
        "soft_skill_fit": "moderate",
    }
    for dim, default in default_labels.items():
        if dim not in labels:
            labels[dim] = default

    return labels


def _score_to_label(dimension: str, score: float) -> str:
    """Map a numeric score to the correct label for a dimension."""
    ranges = LABEL_DIMENSIONS.get(dimension, {})
    best_label = None
    for label, (lo, hi) in ranges.items():
        if lo <= score <= hi:
            return label
        # Track closest match
        if best_label is None:
            best_label = label

    # Fallback: find the range whose midpoint is closest
    if ranges:
        closest = min(
            ranges.items(),
            key=lambda x: abs(score - (x[1][0] + x[1][1]) / 2)
        )
        return closest[0]

    return best_label or "moderate"
