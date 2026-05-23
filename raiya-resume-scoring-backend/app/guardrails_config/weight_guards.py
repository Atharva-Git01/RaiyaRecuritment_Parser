"""
RAIYA Weight Guards — range + sum validation for JD weights.
Handles both legacy plain-number criteria and enterprise rich-dict criteria
produced by the 14-phase ontology_label_criteria_average_normalized pipeline.
"""

from typing import List, Tuple


def _extract_criteria_score(value: object) -> float | None:
    """
    Return the numeric score from a criterion value regardless of format.
      • Legacy flat:   80.0   → 80.0
      • Enterprise:    {"score": 80.0, "reasoning_label": ..., ...} → 80.0
    Returns None if the value is unrecognisable.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        score = value.get("score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def validate_jd_weights(weights_schema: dict) -> Tuple[bool, List[str]]:
    """
    Validate section weights are in [0, 100] and sum to 100 (±0.5).
    Criteria values are validated for sign only (negative → warning appended).
    """
    errors: List[str] = []
    scoring = weights_schema.get("scoring", {})
    total = 0.0

    for section, data in scoring.items():
        if not isinstance(data, dict):
            continue

        w = data.get("weight", 0)
        if not isinstance(w, (int, float)):
            errors.append(f"Weight not numeric: {section}={w}")
            continue
        if w < 0 or w > 100:
            errors.append(f"Weight out of range [0,100]: {section}={w}")
        total += w

        # Validate criteria scores (sign check only)
        criteria = data.get("criteria", {})
        if isinstance(criteria, dict):
            for key, val in criteria.items():
                score = _extract_criteria_score(val)
                if score is None:
                    errors.append(
                        f"Unrecognised criteria format: scoring.{section}.criteria['{key}']"
                    )
                elif score < 0:
                    errors.append(
                        f"Negative criteria score: scoring.{section}.criteria['{key}']={score}"
                    )

    if abs(total - 100.0) > 0.5:
        errors.append(
            f"Weights sum={total:.4f} deviates from 100 (tolerance=0.5)"
        )

    return len(errors) == 0, errors
