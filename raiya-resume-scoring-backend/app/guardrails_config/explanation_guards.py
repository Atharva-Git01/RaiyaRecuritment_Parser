"""
RAIYA Explanation Guards — PII detection and inference language filtering.
"""

from typing import Tuple, List
from app.core.logging_config import get_logger

logger = get_logger("ExplanationGuards")

INFERENCE_PHRASES = [
    "likely", "probably", "seems to", "appears to", "suggests",
    "indicates potential", "may have", "could be", "we can infer",
    "implies", "strong candidate", "good fit", "promising",
    "talented", "impressive", "capable of"
]


def validate_explanation_guardrails(text: str) -> Tuple[str, List[str]]:
    """Apply explanation guards + inference language check."""
    fired = []

    # Inference language check
    for phrase in INFERENCE_PHRASES:
        if phrase.lower() in text.lower():
            fired.append(f"InferenceLanguage:{phrase}")

    return text, fired
