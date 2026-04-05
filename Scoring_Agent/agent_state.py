import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any

class AgentState(Enum):
    """Finite states for the Agent."""
    INIT = "INIT"
    VALIDATING_INPUT = "VALIDATING_INPUT"
    FETCHING_CONTEXT = "FETCHING_CONTEXT"
    SCORING = "SCORING"
    VERIFYING_OUTPUT = "VERIFYING_OUTPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class StateSnapshot:
    """Immutable record of a state transition."""
    from_state: str
    to_state: str
    timestamp: str
    reason: Optional[str] = None

@dataclass
class AgentMemory:
    """
    Structured memory for the Agent.
    Holds all input data, current state, execution history, and results.
    """
    # Inputs (Immutable-ish)
    resume_data: Dict[str, Any]
    jd_data: Dict[str, Any]
    weights: Optional[Dict[str, Any]] = None

    # execution State
    current_state: AgentState = AgentState.INIT
    history: List[StateSnapshot] = field(default_factory=list)
    
    # Outputs
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def transition(self, new_state: AgentState, reason: Optional[str] = None):
        """Record a transition and update state."""
        snapshot = StateSnapshot(
            from_state=self.current_state.value,
            to_state=new_state.value,
            timestamp=datetime.datetime.now().isoformat(),
            reason=reason
        )
        self.history.append(snapshot)
        self.current_state = new_state

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize memory to a dictionary. 
        Useful for traceability and auditing.
        """
        return {
            "current_state": self.current_state.value,
            "inputs": {
                "resume_summary": "Present" if self.resume_data else "Missing", # Don't dump PII/full text by default? Or maybe we should for full audit. 
                # For now, let's keep inputs minimal in the top level dump or full if needed.
                # Let's dump full inputs for the 'Auditable decision artifact' as requested.
                "resume": self.resume_data,
                "jd": self.jd_data,
                "weights": self.weights
            },
            "history": [asdict(h) for h in self.history],
            "result": self.result,
            "error": self.error
        }
