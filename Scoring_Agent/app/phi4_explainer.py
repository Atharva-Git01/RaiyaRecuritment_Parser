from typing import Any, Dict


def get_config() -> Dict[str, Any]:
    return {"mode": "deterministic_stub"}


def generate_explanation(*args, **kwargs) -> Dict[str, Any]:
    return {
        "summary": "Explanation generation is running in deterministic fallback mode.",
        "strengths": [],
        "improvements": [],
    }
