import logging
from typing import Dict, List, Any, Optional
# Local imports
try:
    from agent_state import AgentState
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from agent_state import AgentState

logger = logging.getLogger("AgentAuthority")
# Ensure logging setup if used standalone
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

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
        # Format: {Current_State_Value: [Allowed_Next_State_Values]}
        self._allowed_transitions: Dict[str, List[str]] = {
            AgentState.INIT.value: [AgentState.VALIDATING_INPUT.value],
            AgentState.VALIDATING_INPUT.value: [AgentState.FETCHING_CONTEXT.value, AgentState.FAILED.value],
            AgentState.FETCHING_CONTEXT.value: [AgentState.SCORING.value, AgentState.FAILED.value],
            AgentState.SCORING.value: [AgentState.VERIFYING_OUTPUT.value, AgentState.FAILED.value],
            AgentState.VERIFYING_OUTPUT.value: [AgentState.COMPLETED.value, AgentState.FAILED.value],
            AgentState.COMPLETED.value: [], # Terminal
            AgentState.FAILED.value: []     # Terminal
        }

    def authorize_transition(self, current_state: str, next_state: str) -> bool:
        """
        Check if the transition is allowed.
        Accepts strings (values of Enums).
        """
        if current_state == next_state:
            # No-op transition is allowed (idempotency)
            return True
            
        allowed_next = self._allowed_transitions.get(current_state, [])
        if next_state in allowed_next:
            logger.info(f"Authority: Transition '{current_state}' -> '{next_state}' APPROVED.")
            return True
        else:
            logger.error(f"Authority: Transition '{current_state}' -> '{next_state}' DENIED. (Not in whitelist)")
            return False

    def authorize_score(self, score_data: Dict[str, Any]) -> bool:
        """
        Validate appropriate scoring usage.
        The LLM is a tool; it cannot render a score that violates schema or logic basics.
        
        Rules:
        1. Must be a dict.
        2. Must contain 'final_score'.
        3. 'final_score' must be int 0-100.
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
