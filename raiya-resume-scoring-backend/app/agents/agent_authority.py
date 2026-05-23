"""
RAIYA Authority Governance — FSM transition control and score validation.
"""

from typing import Dict, List, Any
from app.core.logging_config import get_logger

logger = get_logger("AgentAuthority")


class AuthorityGovernance:
    """
    Governance layer for the Agent.
    Enforces:
    1. Closed World Assumption (Whitelisted transitions).
    2. Monotonicity (Cannot regress to previous states).
    3. LLM Constraint (Score validation).
    """

    def __init__(self):
        # CLOSED WORLD: Explicitly allow only these transitions.
        self._allowed_transitions: Dict[str, List[str]] = {
            "INIT": ["VALIDATING_INPUT"],
            "VALIDATING_INPUT": ["FETCHING_CONTEXT", "FAILED"],
            "FETCHING_CONTEXT": ["SCORING", "FAILED"],
            "SCORING": ["VERIFYING_OUTPUT", "FAILED"],
            "VERIFYING_OUTPUT": ["COMPLETED", "FAILED"],
            "COMPLETED": [],    # Terminal
            "FAILED": []        # Terminal
        }

    def authorize_transition(self, current_state: str, next_state: str) -> bool:
        """Check if the transition is allowed."""
        if current_state == next_state:
            return True  # No-op transition (idempotency)

        allowed_next = self._allowed_transitions.get(current_state, [])
        if next_state in allowed_next:
            logger.info(f"Authority: Transition '{current_state}' -> '{next_state}' APPROVED.")
            return True
        else:
            logger.error(f"Authority: Transition '{current_state}' -> '{next_state}' DENIED.")
            return False

    def authorize_score(self, score_data: Dict[str, Any]) -> bool:
        """
        Validate AI score output.
        Rules:
        1. Must be a dict.
        2. Must contain 'final_score'.
        3. 'final_score' must be numeric 0-100.
        """
        if not isinstance(score_data, dict):
            logger.error("Authority: Score DENIED. Data is not a dictionary.")
            return False

        if "final_score" not in score_data:
            logger.error("Authority: Score DENIED. Missing 'final_score'.")
            return False

        score = score_data["final_score"]
        if not isinstance(score, (int, float)):
            logger.error("Authority: Score DENIED. 'final_score' is not numeric.")
            return False

        if not (0 <= score <= 100):
            logger.error(f"Authority: Score DENIED. 'final_score' {score} out of bounds.")
            return False

        logger.info("Authority: Score structure APPROVED.")
        return True
