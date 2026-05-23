"""
RAIYA Final Validation Report Schema — Maps final_validation_report_schema.json.
Output of rag_validation _generate_final_report(). Combines deterministic validity,
mathematical validity, and JD weight pipeline Phase 13 validity into a single verdict.
"""

from pydantic import BaseModel, Field
from typing import Literal


class FinalValidationReport(BaseModel):
    """PASS only when det_valid AND math_valid AND jd_weights_math_valid."""
    verdict: Literal["PASS", "FAIL"]
    deterministic_valid: bool           # True when no hallucination/mandatory-gap/anomaly errors
    mathematical_valid: bool            # True when overall_accuracy >= 80 (Step 4)
    # Cross-reference of JD Phase 13 mathematical_validation.is_valid
    jd_weights_math_valid: bool = True
    overall_accuracy: float             # Step 4 overall accuracy percentage (0–100)
    importance_weighted_mae: float = 0.0
    rules_fired: int = 0                # Total rules fired across all sections (R001–R005)
    # high (accuracy >= 90) | medium (accuracy >= 70) | low (accuracy < 70)
    confidence: Literal["high", "medium", "low"]
