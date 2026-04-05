from typing import Any, Dict


def validate_explanation(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Explanation payload must be a dictionary.")
    return payload
