from copy import deepcopy
from typing import Any, Dict

from app.jd_normalizer import normalize_jd


def _scale_criteria(criteria: Dict[str, Any]) -> Dict[str, int]:
    if not isinstance(criteria, dict) or not criteria:
        return {}

    numeric_values = []
    for value in criteria.values():
        try:
            numeric_values.append(float(value))
        except Exception:
            numeric_values.append(0.0)

    max_value = max(numeric_values) if numeric_values else 0.0
    if max_value <= 0:
        return {key: 0 for key in criteria}

    if max_value >= 100:
        return {
            key: max(0, min(100, int(round(float(value))))) if str(value).strip() else 0
            for key, value in criteria.items()
        }

    scale = 100.0 / max_value
    return {
        key: max(0, min(100, int(round(float(value) * scale)))) if str(value).strip() else 0
        for key, value in criteria.items()
    }


def _normalize_weights(scoring: Dict[str, Any]) -> Dict[str, Any]:
    total_weight = 0.0
    cleaned: Dict[str, Any] = {}

    for key, block in scoring.items():
        if not isinstance(block, dict):
            continue
        try:
            weight = float(block.get("weight", 0))
        except Exception:
            weight = 0.0
        total_weight += max(weight, 0.0)
        cleaned[key] = deepcopy(block)

    if total_weight <= 0:
        return cleaned

    for block in cleaned.values():
        block["weight"] = round(max(float(block.get("weight", 0)), 0.0) / total_weight, 4)
        block["criteria"] = _scale_criteria(block.get("criteria", {}))

    return cleaned


def validate_jd(jd: Dict[str, Any]) -> Dict[str, Any]:
    if jd is None:
        raise ValueError("JD data is empty/None.")
    normalized = normalize_jd(deepcopy(jd or {}))
    scoring = normalized.get("scoring", {})
    if isinstance(scoring, dict):
        normalized["scoring"] = _normalize_weights(scoring)
    return normalized
