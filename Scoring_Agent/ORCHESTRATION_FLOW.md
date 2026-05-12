# Resume Scoring Pipeline - Orchestration Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          ENTRY POINT: process_resume.py                                              │
│                     Loads Resume JSON + JD JSON from uploads/                                        │
└────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT CONTROLLER (Orchestrator)                                               │
│                         State Machine: AgentState Enum                                               │
│                    Memory: AgentMemory (Single Source of Truth)                                      │
└────────────────────────────────┬─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │   STATE: INIT          │
                     │   Action: Initialize   │
                     └────────┬───────────────┘
                              │
                              ▼
         ┌─────────���──────────────────────────────────────────────┐
         │         STATE: VALIDATING_INPUT                        │
         │         ┌──────────────────────────────────┐           │
         │         │  AgentGuardrails.validate_*()    │           │
         │         │  • validate_resume_schema()      │           │
         │         │  • validate_jd_schema()          │           │
         │         │  • validate_weights()            │           │
         │         │  FAIL-FAST: Raises ValidationFailure        │
         │         └──────────────────────────────────┘           │
         └────────┬───────────────────────────────────────────────┘
                  │                                    │
                  │ PASS                               │ FAIL
                  ▼                                    ▼
     ┌────────────────────────┐              ┌─────────────────┐
     │ STATE: FETCHING_CONTEXT│              │  STATE: FAILED  │
     │ Action: Prepare Context│              │  Store Error    │
     └────────┬───────────────┘              └─────────────────┘
              │
              ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                           STATE: SCORING                                                             │
 │  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │  1. Pre-Scoring Check (AgentGuardrails.pre_scoring_check())                                │     │
 │  │  2. RAG Validation (Evidence Retrieval & Ground Truth)                                     │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │  RAG Validation Layer (RAG_Validation_layer/)                                       │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ • Semantic Matching: Check JD vs Resume embeddings                              │  │   │   │
 │  │     │  │ • Ground Truth Calculation: Independent score recalc                             │  │   │   │
 │  │     │  │ • Rule-Based Evidence: Detect biases (e.g., internship)                           │  │   │   │
 │  │     │  │ • Generate Constraints for AI Prompt                                              │  │   │   │
 │  │     │  └─────────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  3. Call ai_scorer.ai_score_resume()                                                       │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │  AI SCORER MODULE (ai_scorer.py)                                                     │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ A. Contract Enforcement (scoring_contracts.py)                                 │  │   │   │
 │  │     │  │    • Validate ScoringWeights                                                    │  │   │   │
 │  │     │  │    • Validate ResumeFacts                                                        │  │   │   │
 │  │     │  │    • Validate JDRequirements                                                     │  │   │   │
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ B. JD Validation & Normalization                                               │  │   │   │
 │  │     │  │    jd_validator.validate_jd()                                                  │  │   │   │
 │  │     │  │    ├─ jd_normalizer.normalize_jd()                                             │  │   │   │
 │  │     │  │    ├─ validate_scoring_structure()                                             │  │   │   │
 │  │     │  │    ├─ scale_all_criteria() (0-100)                                             │  │   │   │
 │  │     │  │    └─ validate_weights_sum() (normalize to 1.0)                                │  │   │   │
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ C. Evidence Rules Evaluation                                                   │  │   │   │
 │  │     │  │    • Load config/evidence_rules.json                                           │  │   │   │
 │  │     │  │    • Evaluate rules against resume                                             │  │   │   │
 │  │     │  │    • Generate constraint text for AI prompt                                    │  │   │   │
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ D. AI Request (Azure OpenAI)                                                   │  │   │   │
 │  │     │  │    • Load system_prompt.txt (versioned)                                        │  │   │   │
 │  │     │  │    • Build user prompt with JD + Resume + Rules                                │  │   │   │
 │  │     │  │    • POST to Azure OpenAI (3 retries, 180s timeout)                             │  │   │   │
 │  │     │  │    • Parse JSON response                                                        │  │   │   │
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ E. Output Validation & Guardrails                                              │  │   │   │
 │  │     │  │    validate_ai_score_output()                                                  │  │   │   │
 │  │     │  │    ├─ Clamp scores to 0-100                                                    │  │   │   │
 │  │     │  │    ├─ apply_guardrails() (ai_guardrails.py)                                    │  │   │   │
 │  │     │  │    │   └─ validate_output_integrity()                                          │  │   │   │
 │  │     │  │    └─ Recompute final_score (weighted sum)                                     │  │   │   │
 │  │     │  │  └──────────────────────────────────────────────���────────────────────────────────┘  │   │   │
 │  │     │  Return: {"ai_ok": True, "ai_score": {...}}                                       │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  4. Store result in AgentMemory                                                            │     │
 │  └───────────────────────────────────────────────────────────────────────────────────────────────┘   │
 └────────┬───────────────────────────────────────────────────────────────────────────────────────┘
          │                                    │
          │ SUCCESS                            │ FAILURE
          ▼                                    ▼
 ┌─────────────────────────┐          ┌─────────────────┐
 │ STATE: VERIFYING_OUTPUT │          │  STATE: FAILED  │
 │  ┌──────────────────┐   │          │  Store Error    │
 │  │ Authority Check  │   │          └─────────────────┘
 │  │ authorize_score()│   │
 │  │ • Is dict?       │   │
 │  │ • Has final_score│   │
 │  │ • Score 0-100?   │   │
 │  └──────────────────┘   │
 └────────┬────────────────┘
          │                 │
          │ APPROVED        │ REJECTED
          ▼                 ▼
 ┌─────────────────┐  ┌─────────────────┐
 │ STATE: COMPLETED│  │  STATE: FAILED  │
 │ Success = True  │  │  Store Error    │
 └────────┬────────┘  └─────────────────┘
          │
          ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                    OUTPUT: results/scoring_result_*.json                                            │
 │  {                                                                                                   │
 │    "current_state": "COMPLETED",                                                                     │
 │    "inputs": { resume, jd, weights },                                                                │
 │    "history": [ state transitions with timestamps ],                                                │
 │    "result": { final_score, component_scores, notes, scoring_trace },                               │
 │    "validation_report": {                                                                            │
 │      "mae": float,                                                                                   │
 │      "accuracy": float,                                                                              │
 │      "ground_truth": float,                                                                          │
 │      "evidence_metrics": {...}                                                                       │
 │    },                                                                                                │
 │    "error": null,                                                                                    │
 │    "success": true                                                                                   │
 │  }                                                                                                   │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. **State Machine (agent_state.py)**
- `AgentState` enum: INIT → VALIDATING_INPUT → FETCHING_CONTEXT → SCORING → VERIFYING_OUTPUT → COMPLETED/FAILED
- `AgentMemory`: Immutable audit trail with state history

### 2. **Governance Layer (agent_authority.py)**
- **Closed World Assumption**: Whitelisted state transitions only
- **Monotonicity**: No backward state transitions
- **Score Validation**: Enforces 0-100 range, required fields

### 3. **Safety Layer (ai_guardrails.py)**
- **Fail-Fast Validation**: Raises exceptions on bad input
- **Schema Checks**: Resume, JD, Weights validation
- **Output Integrity**: Post-scoring sanity checks

### 4. **AI Scorer (ai_scorer.py)**
- **Contract Enforcement**: Pydantic models for type safety
- **JD Normalization**: Scales criteria, normalizes weights
- **Evidence Rules**: Applies constraints from config
- **Retry Logic**: 3 attempts with backoff
- **Guardrails Integration**: Sanitizes AI output

### 5. **RAG Validation Layer (Integrated in SCORING)**
- **Semantic Matching**: Embedding-based validation to detect hallucinations
- **Ground Truth Calculation**: Independent score recalculation with MAE/RMSE
- **Rule-Based Evidence**: Dynamic rules for bias detection (e.g., internship overestimation)
- **Historical Indexing**: Pinecone storage for retrieval and RAG queries

### 6. **Orchestrator (agent_controller.py)**
- **State Dispatch**: Routes execution based on current state
- **Authority Checks**: Validates every transition
- **Error Handling**: Captures failures with context
- **Idempotency**: Safe to retry any state

## Data Flow

```
Resume JSON + JD JSON
     ↓
Validation (Guardrails)
     ↓
JD Normalization (Weights → 1.0, Criteria → 0-100)
     ↓
RAG Validation (Semantic Matching, Ground Truth, Evidence Generation)
     ↓
Evidence Rules Evaluation
     ↓
AI Prompt Construction (System + User + Constraints)
     ↓
Azure OpenAI API Call
     ↓
JSON Response Parsing
     ↓
Output Validation (Guardrails + Authority)
     ↓
Final Score Calculation (Weighted Sum)
     ↓
Memory Serialization (Audit Trail)
     ↓
JSON Output File
```

## Security & Reliability Features

- ✅ **Fail-Fast**: Invalid input stops execution immediately
- ✅ **Closed World**: Only whitelisted transitions allowed
- ✅ **Immutable History**: Full audit trail of state changes
- ✅ **Contract Enforcement**: Pydantic validation at boundaries
- ✅ **Retry Logic**: 3 attempts for AI calls
- ✅ **Score Recomputation**: AI cannot hallucinate final_score
- ✅ **Evidence-Based Constraints**: Rules applied from config
- ✅ **Timeout Protection**: 180s max per AI request
- ✅ **RAG Validation**: Semantic ground truth with MAE/RMSE metrics
- ✅ **Historical Indexing**: Evidence stored in Pinecone for retrieval
