 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                           STATE: SCORING                                                             │
 │  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐   │
 │  │  1. Pre-Scoring Check (AgentGuardrails.pre_scoring_check())                                │     │
 │  │  2. JD Validation & Normalization                                                            │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │    jd_validator.validate_jd()                                                        │   │   │
 │  │     │    ├─ jd_normalizer.normalize_jd()                                                   │   │   │
 │  │     │    ├─ validate_scoring_structure()                                                   │   │   │
 │  │     │    ├─ scale_all_criteria() (0-100)                                                   │   │   │
 │  │     │    └─ validate_weights_sum() (normalize to 1.0)                                      │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  3. RAG Validation (Evidence Retrieval & Ground Truth)                                     │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │  RAG Validation Layer (RAG_Validation_layer/)                                       │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ • Semantic Matching: Check JD vs Resume embeddings                              │  │   │   │
 │  │     │  │ • Ground Truth Calculation: Independent score recalc                             │  │   │   │
 │  │     │  │ • Rule-Based Evidence: Detect biases (e.g., internship)                           │  │   │   │
 │  │     │  │ • Generate Constraints for AI Prompt                                              │  │   │   │
 │  │     │  └─────────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  4. Evidence Rules Evaluation                                                               │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │    • Load config/evidence_rules.json                                                 │   │   │
 │  │     │    • Evaluate rules against resume                                                   │   │   │
 │  │     │    • Generate constraint text for AI prompt                                          │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  5. Call ai_scorer.ai_score_resume()                                                       │     │
 │  │     ┌─────────────────────────────────────────────────────────────────────────────────────┐   │   │
 │  │     │  AI SCORER MODULE (ai_scorer.py)                                                     │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ A. Contract Enforcement (scoring_contracts.py)                                 │  │   │   │
 │  │     │  │    • Validate ScoringWeights                                                    │  │   │   │
 │  │     │  │    • Validate ResumeFacts                                                        │  │   │   │
 │  │     │  │    • Validate JDRequirements                                                     │  │   │   │
 │  │     │  │  └───────────────────���───────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ B. JD Validation & Normalization (Already Done)                                │  │   │   │
 │  │     │  │    (Integrated above)                                                            │  │   │   │
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  ┌─────────────────────────────────────────────────────────────────────────────────┐  │   │   │
 │  │     │  │ C. Evidence Rules Evaluation (Already Done)                                    │  │   │   │
 │  │     │  │    (Integrated above)                                                            │  │   │   │
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
 │  │     │  │  └───────────────────────────────────────────────────────────────────────────────┘  │   │   │
 │  │     │  Return: {"ai_ok": True, "ai_score": {...}}                                       │   │   │
 │  │     └─────────────────────────────────────────────────────────────────────────────────────┘   │   │
 │  │  6. Store result in AgentMemory                                                            │     │
 │  └───────────────────────────────────────────────────────────────────────────────────────────────┘   │