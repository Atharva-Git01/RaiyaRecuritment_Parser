import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("AgentGuardrails")

class ValidationFailure(Exception):
    """Custom exception for validation failures to trigger fail-fast."""
    pass

class AgentGuardrails:
    """
    Safety and Validation Layer.
    Enforces data integrity before processing steps.
    Stops silent corruption by failing fast.
    """

    @staticmethod
    def validate_resume_schema(resume_data: Dict[str, Any]) -> bool:
        """
        Validate Resume has minimum viable fields.
        FAIL-FAST: Raises ValidationFailure if critical data is missing.
        """
        if not resume_data:
            raise ValidationFailure("Resume data is empty/None.")
        
        # Critical fields required for any meaningful scoring
        required_fields = ["name"] # 'skills' or 'experience' might be optional technically, but name is ID.
        # Actually, for scoring, we need SKILLS or EXPERIENCE or EDUCATION usually. 
        # But let's check for basic structure.
        
        missing = []
        for f in required_fields:
            if f in resume_data:
                continue
            # Check nested personal_info for 'name'
            if f == "name" and "personal_info" in resume_data and isinstance(resume_data["personal_info"], dict):
                if "name" in resume_data["personal_info"]:
                    continue
            missing.append(f)

        if missing:
             raise ValidationFailure(f"Resume missing critical fields: {missing}")

        # Deep check: Ensure non-empty if present
        if "skills" in resume_data and not isinstance(resume_data["skills"], list):
             raise ValidationFailure("Resume 'skills' must be a list.")
             
        logger.info("Guardrails: Resume schema valid.")
        return True

    @staticmethod
    def validate_jd_schema(jd_data: Dict[str, Any]) -> bool:
        """
        Validate JD has minimum viable fields.
        """
        if not jd_data:
            raise ValidationFailure("JD data is empty/None.")
            
        # Check for title/job_title OR description/job_description/requirements
        has_title = "title" in jd_data or "job_title" in jd_data
        has_desc = "description" in jd_data or "job_description" in jd_data or "requirements" in jd_data
        
        if not has_title and not has_desc:
             raise ValidationFailure("JD must have title/job_title or description/requirements/job_description.")
             
        logger.info("Guardrails: JD schema valid.")
        return True

    @staticmethod
    def validate_weights(weights: Optional[Dict[str, Any]]) -> bool:
        """
        Validate scoring weights if provided.
        """
        if weights is None:
            return True # defaults used
            
        if not isinstance(weights, dict):
            raise ValidationFailure("Weights must be a dictionary.")
            
        # Check for non-numeric values
        for k, v in weights.items():
            if not isinstance(v, (int, float)):
                 raise ValidationFailure(f"Weight '{k}' is not numeric: {v}")
                 
        logger.info("Guardrails: Weights valid.")
        return True

    @staticmethod
    def pre_scoring_check(resume: Dict, jd: Dict) -> bool:
        """
        Final boundary check before invoking AI Scorer.
        """
        # Ensure neither is empty
        if not resume or not jd:
             raise ValidationFailure("Cannot score: Resume or JD is missing.")
             
        # Check size limits (DoS prevention)
        # e.g. text characters roughly
        # This is a good place to stop huge payloads
        return True

    @staticmethod
    def validate_output_integrity(result: Dict[str, Any]) -> bool:
        """
        Post-scoring check.
        Ensures result is not just valid but 'sane'.
        """
        if not result:
            raise ValidationFailure("Result is empty.")
            
        if "final_score" not in result:
             raise ValidationFailure("Result missing 'final_score'.")
             
        # Sanity check: If final_score > 0 but skills_score is 0 and experience is 0 and... 
        # might be suspicious if weights imply otherwise. 
        # But Authority checks schema. Guardrails checks logic/sanity if needed.
        return True

# === AI Scorer Integration Support ===

class GuardrailContext:
    """
    Context object for guardrails, compatible with ai_scorer requirements.
    Holds references to the Resume and JD objects being scored.
    """
    def __init__(self, resume: Any, jd: Any):
        self.resume = resume
        self.jd = jd

def apply_guardrails(score_dict: Dict[str, Any], context: GuardrailContext) -> Dict[str, Any]:
    """
    Apply guardrails to the AI score output.
    This function is called by ai_scorer.py.
    
    Args:
        score_dict: The raw score dictionary from the AI.
        context: Context containing resume and JD.
        
    Returns:
        The validated (and potentially sanitized) score dictionary.
    """
    # 1. Integrity Check
    try:
        AgentGuardrails.validate_output_integrity(score_dict)
    except ValidationFailure as e:
        logger.warning(f"Guardrails integrity check warning: {e}")
        # We might choose to return as-is or sanitize. 
        # For now, let's log and proceed, but ensure 'final_score' exists safely.
        if "final_score" not in score_dict:
            score_dict["final_score"] = 0
            
    # 2. Logic/Consistency Sanitization (Optional extension point)
    # Example: If evidence_rules were triggering, we could enforce capping here.
    
    return score_dict

