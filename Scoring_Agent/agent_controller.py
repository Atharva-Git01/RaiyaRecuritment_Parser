import logging
from typing import Optional, Dict, Any, List

# Local imports
try:
    from app.ai_guardrails import AgentGuardrails, ValidationFailure
    from app.jd_validator import validate_jd
    from agent_authority import AuthorityGovernance
    from agent_state import AgentState, AgentMemory
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from app.ai_guardrails import AgentGuardrails, ValidationFailure
    from app.jd_validator import validate_jd
    from agent_authority import AuthorityGovernance
    from agent_state import AgentState, AgentMemory

# Configure logger
logger = logging.getLogger("AgentController")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class AgentController:
    """
    State-based agent to manage the AI scoring process.
    Ensures explicit control flow, idempotency, and traceability.
    """
    
    def __init__(self, resume_data: dict, jd_data: dict, weights: Optional[dict] = None):
        # Normalize JD immediately to ensure weights are actionable
        try:
            clean_jd = validate_jd(jd_data)
        except Exception as e:
            logger.warning(f"JD Validaton/Normalization failed in init: {e}")
            clean_jd = jd_data
            
        # Initialize Memory (Single Source of Truth)
        self.memory = AgentMemory(
            resume_data=resume_data,
            jd_data=clean_jd,
            weights=weights
        )
        
        # Authority / Governance
        self.authority = AuthorityGovernance()

    @property
    def state(self) -> AgentState:
        return self.memory.current_state

    @property
    def result(self) -> Optional[Dict]:
        return self.memory.result
    
    @property
    def error(self) -> Optional[str]:
        return self.memory.error

    def transition_to(self, new_state: AgentState):
        """Transition to a new state and record history."""
        # --- AUTHORITY CHECK ---
        allowed = self.authority.authorize_transition(self.state.value, new_state.value)
        
        if not allowed:
            logger.critical(f"SECURITY VIOLATION: Unauthorized transition attempted from {self.state.value} to {new_state.value}")
            self.memory.error = f"Unauthorized state transition from {self.state.value} to {new_state.value}"
            if self.state != AgentState.FAILED:
                 self.memory.transition(AgentState.FAILED, reason="Security Violation")
            return

        logger.info(f"State Transition: {self.state.value} -> {new_state.value}")
        self.memory.transition(new_state)

    def is_terminal(self) -> bool:
        """Check if the agent is in a terminal state."""
        return self.state in [AgentState.COMPLETED, AgentState.FAILED]

    def run(self, max_steps: int = 20) -> Dict[str, Any]:
        """
        Execute the agent loop until terminal state or max_steps.
        Returns the final output.
        """
        logger.info("Starting Agent Controller execution...")
        steps = 0
        while not self.is_terminal():
            if steps >= max_steps:
                self.memory.error = "Max execution steps reached."
                self.transition_to(AgentState.FAILED)
                break
            
            self.step()
            steps += 1
            
        return self.get_output()

    def step(self):
        """
        Execute a single step based on the current state.
        This method is idempotent for a given state (it attempts to advance).
        """
        # Dispatch based on current state
        state = self.state
        
        if state == AgentState.INIT:
            self._do_init()
        elif state == AgentState.VALIDATING_INPUT:
            self._do_validate()
        elif state == AgentState.FETCHING_CONTEXT:
            self._do_fetch_context()
        elif state == AgentState.SCORING:
            self._do_score()
        elif state == AgentState.VERIFYING_OUTPUT:
            self._do_verify_output()
        elif self.is_terminal():
            logger.info("Agent is already in terminal state. No operation.")
        else:
            self.memory.error = f"Unknown state encountered: {state}"
            self.transition_to(AgentState.FAILED)

    # --- State Actions ---

    def _do_init(self):
        self.transition_to(AgentState.VALIDATING_INPUT)

    def _do_validate(self):
        logger.info("Validating inputs with Guardrails...")
        try:
            # FAIL-FAST: Guardrails raise exceptions if bad.
            AgentGuardrails.validate_resume_schema(self.memory.resume_data)
            AgentGuardrails.validate_jd_schema(self.memory.jd_data)
            AgentGuardrails.validate_weights(self.memory.weights)
            
            self.transition_to(AgentState.FETCHING_CONTEXT)
            
        except ValidationFailure as vf:
            logger.error(f"Guardrails Validation Failed: {vf}")
            self.memory.error = str(vf)
            self.transition_to(AgentState.FAILED)
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            self.memory.error = f"System Error: {e}"
            self.transition_to(AgentState.FAILED)

    def _do_fetch_context(self):
        logger.info("Fetching context...")
        self.transition_to(AgentState.SCORING)

    def _do_score(self):
        logger.info("Executing AI scoring...")
        
        # Guardrail check before major operation
        try:
            AgentGuardrails.pre_scoring_check(self.memory.resume_data, self.memory.jd_data)
        except ValidationFailure as vf:
            self.memory.error = f"Pre-scoring Check Failed: {vf}"
            self.transition_to(AgentState.FAILED)
            return

        try:
            from ai_scorer import ai_score_resume
            
            response = ai_score_resume(
                parsed_resume=self.memory.resume_data,
                job_description=self.memory.jd_data,
                scoring_weights=self.memory.weights
            )

            if response.get("ai_ok"):
                self.memory.result = response.get("ai_score")
                self.memory.token_usage = response.get("token_usage", {})  # carry tokens forward
                self.transition_to(AgentState.VERIFYING_OUTPUT)
            else:
                self.memory.error = str(response.get("error", "Unknown error from ai_scorer"))
                self.transition_to(AgentState.FAILED)

        except ImportError:
            self.memory.error = "Could not import 'ai_scorer'."
            self.transition_to(AgentState.FAILED)
        except Exception as e:
            self.memory.error = f"Exception during scoring: {str(e)}"
            self.transition_to(AgentState.FAILED)

    def _do_verify_output(self):
        logger.info("Verifying output...")
        
        if not self.authority.authorize_score(self.memory.result):
            self.memory.error = "Authority rejected the AI score (Malformed or out of bounds)."
            self.transition_to(AgentState.FAILED)
            return
        
        self.transition_to(AgentState.COMPLETED)

    # --- Output ---

    def get_output(self) -> Dict[str, Any]:
        """Return the final state and result from memory."""
        dump = self.memory.to_dict()
        dump["success"] = (self.state == AgentState.COMPLETED)
        # Include token usage at top level for easy access
        dump["token_usage"] = getattr(self.memory, "token_usage", {})
        return dump

# --- Example Usage ---
if __name__ == "__main__":
    # Mock data for testing
    mock_resume = {"name": "Test User", "skills": ["Python", "AI"]}
    mock_jd = {"title": "Engineer", "requirements": ["Python"]}
    
    print("Initializing Agent...")
    agent = AgentController(mock_resume, mock_jd)
    
    print("Running Agent...")
    final_output = agent.run()
    
    import json
    print(json.dumps(final_output, indent=2, default=str))
