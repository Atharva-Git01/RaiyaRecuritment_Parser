"""
RAIYA Agent Guardrails — Input/output validation safety layer.
"""

from typing import Dict, Any, Optional
from app.core.logging_config import get_logger

logger = get_logger("AgentGuardrails")


class ValidationFailure(Exception):
    """Custom exception for validation failures to trigger fail-fast."""
    pass


class AgentGuardrails:
    """Safety and Validation Layer. Enforces data integrity before processing steps."""

    @staticmethod
    def validate_resume_schema(resume_data: Dict[str, Any]) -> bool:
        """Validate Resume has minimum viable fields. FAIL-FAST."""
        if not resume_data:
            raise ValidationFailure("Resume data is empty/None.")

        # Check for name in top-level or nested personal_info
        has_name = "name" in resume_data
        if not has_name and "personal_info" in resume_data:
            if isinstance(resume_data["personal_info"], dict):
                has_name = "name" in resume_data["personal_info"]

        if not has_name:
            raise ValidationFailure("Resume missing critical field: name")

        if "skills" in resume_data and not isinstance(resume_data["skills"], list):
            raise ValidationFailure("Resume 'skills' must be a list.")

        logger.info("Guardrails: Resume schema valid.")
        return True

    @staticmethod
    def validate_jd_schema(jd_data: Dict[str, Any]) -> bool:
        """Validate JD has minimum viable fields."""
        if not jd_data:
            raise ValidationFailure("JD data is empty/None.")

        has_title = "title" in jd_data or "job_title" in jd_data
        has_desc = any(k in jd_data for k in ("description", "job_description", "requirements"))
        has_job_info = "job_information" in jd_data

        if not has_title and not has_desc and not has_job_info:
            raise ValidationFailure("JD must have title/job_title or description/requirements.")

        logger.info("Guardrails: JD schema valid.")
        return True

    @staticmethod
    def validate_weights(weights: Optional[Dict[str, Any]]) -> bool:
        """Validate scoring weights if provided."""
        if weights is None:
            return True  # defaults used

        if not isinstance(weights, dict):
            raise ValidationFailure("Weights must be a dictionary.")

        scoring = weights.get("scoring", weights)
        if isinstance(scoring, dict):
            for k, v in scoring.items():
                if isinstance(v, dict) and "weight" in v:
                    w = v["weight"]
                    if not isinstance(w, (int, float)):
                        raise ValidationFailure(f"Weight '{k}' is not numeric: {w}")

        logger.info("Guardrails: Weights valid.")
        return True

    @staticmethod
    def validate_reasoning_inputs(
        section_similarities: Dict[str, Any],
        jd_weights: Dict[str, Any],
        resume_parsed: Dict[str, Any]
    ) -> bool:
        """Validate inputs before reasoning engine runs."""
        if not section_similarities:
            raise ValidationFailure("section_similarities is empty.")
        if not jd_weights:
            raise ValidationFailure("jd_weights is empty.")
        if not resume_parsed:
            raise ValidationFailure("resume_parsed is empty.")
        
        scoring = jd_weights.get("scoring", {})
        if not scoring:
            raise ValidationFailure("jd_weights.scoring is empty.")
        
        return True

    @staticmethod
    def pre_scoring_check(resume: Dict, jd: Dict) -> bool:
        """Final boundary check before invoking AI Scorer."""
        if not resume or not jd:
            raise ValidationFailure("Cannot score: Resume or JD is missing.")
        return True
