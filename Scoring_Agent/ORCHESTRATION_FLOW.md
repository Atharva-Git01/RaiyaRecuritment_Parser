### 1. **State Machine (agent_state.py)**
- `AgentState` enum: INIT → VALIDATING_INPUT → FETCHING_CONTEXT → SCORING → VERIFYING_OUTPUT → COMPLETED/FAILED
- `AgentMemory`: Immutable audit trail with state history