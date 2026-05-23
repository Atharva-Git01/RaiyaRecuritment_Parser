# RAIYA — Master Copilot Planning Document v7.0
# AI-Powered Resume Screening Backend — Complete Agentic Pipeline
# Need to store all these in the directory : raiya-resume-scoring-backend
# EXISTING Sub directories within the backend directory: 


**System:** RAIYA by SpeedTech.ai
**Stack:** FastAPI · LangGraph · PostgreSQL 16 + pgvector · Redis 7 · Azure Phi-4 · Nanonets DocStrange OCR
**For:** AI Coding Agent / GitHub Copilot Workspace
**Updated:** All 9 canonical schemas integrated · LangChain RecursiveJsonSplitter chunking ·
            Hybrid search inside DeterministicValidator · Guardrails AI SimilarToPreviousValues ·
            Correct ReAct pattern (RAG evidence → reasoning validation)

---

## CRITICAL RULES FOR CODING AGENT

```
1.  NEVER store raw_text from OCR — Nanonets returns structured JSON directly
2.  NEVER store candidate_name or candidate_email as columns — read from parsed_json at query time
3.  Resume table PK is file_id (NOT id)
4.  org_id NOT in resumes table — access via batch → jd → org join
5.  Reasoning engine assigns LABELS ONLY — never numeric scores
6.  Reasoning engine is a 5-phase PURE ANALYSIS layer — runs between hybrid_search and rag_validation
7.  All hashes use SHA-256 prefixed "sha256:"
8.  Every LLM call logs to token_usage_monitor (JSONL + PostgreSQL)
9.  LangGraph interrupt_before=["hitl_pause"] — weights MUST be human-verified
10. Redis cache keys follow exact patterns in Section 10
11. Evidence rules JSON loaded at startup — admin updates via API
12. Reasoning output cached: "reason:{r_hash}:{j_hash}:{w_hash}" TTL=2h
13. Chunking uses LangChain RecursiveJsonSplitter — NOT naive text splitting
14. DeterministicValidator runs hybrid search (BGE dense + BM25) internally per section
15. Guardrails AI SimilarToPreviousValues applied on every section score to catch drift
16. ReAct pattern: THOUGHT→ACTION→OBSERVATION→SCORE — RAG evidence IS the context
17. JD weights schema now includes weight_generation_metadata per section
18. Final scoring agent schema (final_result_scoring_agent_schema.json) is the canonical output
19.Do not Use Pine cone api key for vector db instead use pg vector db (PostgreSQL 16 + pgvector) defined in the docker compose code ,refer to the RAG Validation approach from the directory: raiya-resume-scoring-backend\RAG_Validation_layer 
20.Make use of all the necessary directories to use it as agents: 
a. raiya-resume-scoring-backend\jd_extraction_normalization_scoring_weight_assignment
b.raiya-resume-scoring-backend\resume_extraction_normalization
c. update the prompts directory accordingly in :raiya-resume-scoring-backend\prompts  by adding necessary prompt based on the instructions given in the master plan
20 update the env file accordingly in the directory : raiya-resume-scoring-backend\.env
21.API connection establishment with the frontend directory using next js : raiya-resume-scoring-frontend (refer to the workflow defined in the readme file within the frontend directory : raiya-resume-scoring-frontend\README.md and then establish necessary api connection within database,if required make changes in the code in the frontend directory as well )
```

---

## 1. Canonical JSON Schemas Reference

All 9 uploaded schemas are canonical. Every module must conform to these exactly.

### Schema Map

| File | Used By | Pipeline Stage |
|---|---|---|
| `resume_pdf_extraction_schema.json` | Pipeline 1 extract_resume | OCR output |
| `jd_pdf_extraction_schema.json` | Pipeline 2 extract_jd | OCR output |
| `jd_weights_schema_format.json` | Pipeline 2 assign_weights + HiTL | Weight assignment |
| `extracted_rules_schema.json` | RAG step 2 — rule_extractor | Pre-scoring rules |
| `deterministic_validator_output_schema.json` | RAG step 3 — deterministic_validator | Hybrid semantic match |
| `mathematical_validator_report_schema.json` | RAG step 4 — mathematical_validator | Ground truth + MAE |
| `rule_based_evidence_schema.json` | RAG step 5 — rule_based_evidence | 14-detector output |
| `final_validation_report_schema.json` | RAG step 6 — final_report | PASS/FAIL verdict |
| `final_result_scoring_agent_schema.json` | Pipeline 3 score_adjustment output | Final canonical result |

---

## 2. System Overview

```
Pipeline 1 — Resume Extraction
  Raw PDF → file_hash → Redis cache check → Nanonets OCR →
  resume_pdf_extraction_schema JSON → Pydantic validate →
  RecursiveJsonSplitter chunks → BGE-large-en-v1.5 embed → pgvector store

Pipeline 2 — JD Extraction + Weight Assignment
  Raw PDF → file_hash → Redis cache check → Nanonets OCR →
  jd_pdf_extraction_schema JSON → alias normalization →
  Azure Phi-4 LLM → jd_weights_schema_format JSON →
  HiTL pause (verify weights_sum=100) → weights_hash

Pipeline 3 — Scoring + Reasoning + RAG Validation

  hybrid_search_node
  (per section: Dense BGE + BM25 + Exact → RRF → section_similarities)

  reasoning_engine_node  [5-phase LABELS ONLY]
  Phase 1: StructuralAnalyzer (LLM temp=0.0) → structural_facts
  Phase 2: EvidenceClassifier (Python) → evidence_map [EXPLICIT|PARTIAL|ABSENT]
  Phase 3: LabelAssigner (LLM ReAct) → reasoning_labels [categorical]
  Phase 4: CrossVerifier (Python) → verified_labels [label vs similarity range]
  Phase 5: ContextSynthesizer (LLM temp=0.0) → reasoning_context

  rag_validation_layer_node  [8 steps]
  Step 1: load_inputs (validate via AgentGuardrails)
  Step 2: jd_normalize (alias maps + weight scaling)
  Step 3: deterministic_validator
          → NOW uses hybrid search internally (BGE dense + BM25 per section)
          → output: deterministic_validator_output_schema
  Step 4: mathematical_validator
          → output: mathematical_validator_report_schema
  Step 5: rule_based_evidence (14 detectors)
          → output: rule_based_evidence_schema
  Step 6: final_report (PASS/FAIL)
          → output: final_validation_report_schema
  Step 7: historical_evidence (EVD_{ts}_{uuid}.json)
  Step 8: pgvector_update (chunk EVD via RecursiveJsonSplitter → embed → upsert)

  score_adjustment_node
  → reads reasoning_labels + rule_based_evidence + deterministic_report
  → applies Guardrails AI SimilarToPreviousValues on section scores
  → produces final_result_scoring_agent_schema output

  final_validation_node
  → Guardrails AI (score bounds + PII + toxic language)
  → AuthorityGovernance FSM check

  explanation_gen_node
  → reads reasoning_context + all RAG reports
  → 6-section audit-safe explanation

  report_generator_node
  → ReportLab PDF + SHA-256 + batch ranking
```

---

## 3. Complete Directory Structure

```
raiya_backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── hashing.py
│   │   └── logging_config.py
│   │
│   ├── db/
│   │   ├── database.py
│   │   ├── redis_client.py
│   │   └── pgvector_client.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── document.py               # Resume (file_id PK), JobDescription
│   │   ├── batch.py                  # Batch, MatchResult
│   │   └── audit.py                  # HashChainLog, TokenUsageLog, ReasoningLog
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── resume.py                 # Maps resume_pdf_extraction_schema.json
│   │   ├── jd.py                     # Maps jd_pdf_extraction_schema.json
│   │   ├── jd_weights.py             # Maps jd_weights_schema_format.json
│   │   ├── extracted_rules.py        # Maps extracted_rules_schema.json
│   │   ├── deterministic_output.py   # Maps deterministic_validator_output_schema.json
│   │   ├── mathematical_report.py    # Maps mathematical_validator_report_schema.json
│   │   ├── rule_based_evidence.py    # Maps rule_based_evidence_schema.json
│   │   ├── final_result.py           # Maps final_result_scoring_agent_schema.json
│   │   ├── reasoning.py              # ReasoningOutput, LabelSet, VerificationReport
│   │   ├── batch.py
│   │   └── admin.py
│   │
│   ├── agents/
│   │   ├── agent_state.py         
│   │   ├── agent_authority.py
│   │   ├── agent_guardrails.py      
│   │   ├── agent_controller.py       # LangGraph build_graph() all nodes + edges
│   │   │
│   │   ├── nodes/
│   │   │   ├── pipeline1/
│   │   │   │   ├── extract_resume.py # hash → Nanonets → resume_pdf_extraction_schema
│   │   │   │   ├── validate_resume.py
│   │   │   │   └── embed_resume.py   # RecursiveJsonSplitter → BGE → pgvector
│   │   │   │
│   │   │   ├── pipeline2/
│   │   │   │   ├── extract_jd.py     # hash → Nanonets → jd_pdf_extraction_schema
│   │   │   │   ├── validate_jd.py
│   │   │   │   ├── jd_normalize.py
│   │   │   │   ├── assign_weights.py # → jd_weights_schema_format
│   │   │   │   └── hitl_pause.py
│   │   │   │
│   │   │   └── pipeline3/
│   │   │       ├── hybrid_search.py    # Dense+BM25+Exact+RRF per section
│   │   │       ├── reasoning_engine.py # 5-phase + reasoning_context for RAG
│   │   │       ├── rag_validation.py   # 8-step orchestrator
│   │   │       ├── score_adjustment.py # → final_result_scoring_agent_schema
│   │   │       ├── final_validation.py # Guardrails + Authority
│   │   │       ├── explanation_gen.py  # 6-section audit explanation
│   │   │       └── report_generator.py # PDF + hash
│   │   │
│   │   └── tools/
│   │       ├── ocr_tool.py
│   │       ├── embed_tool.py
│   │       ├── search_tool.py          # hybrid per section + RecursiveJsonSplitter
│   │       └── llm_tool.py
│   │
│   ├── reasoning/
│   │   ├── reasoning_engine_core.py
│   │   ├── structural_analyzer.py
│   │   ├── evidence_classifier.py
│   │   ├── label_assigner.py
│   │   ├── cross_verifier.py
│   │   ├── context_synthesizer.py
│   │   ├── reasoning_cache.py
│   │   └── reasoning_schemas.py
│   │
│   ├── RAG_Validation_layer/  (replace pinecone with pg vector and other embeddings model defined in this maser plan,rest the code logic,let it be the same)
│   │   ├── pipeline.py
│   │   ├── normalizer_pre_score.py
│   │   ├── jd_normalizer.py
│   │   ├── rule_extractor.py          # → extracted_rules_schema
│   │   ├── deterministic_validator.py # → deterministic_validator_output_schema
│   │   │                              #   NOW includes hybrid search per section
│   │   ├── mathematical_validator.py  # → mathematical_validator_report_schema
│   │   ├── evidence_rule_engine.py
│   │   ├── rule_based_evidence.py     # → rule_based_evidence_schema
│   │   ├── evidence_generation.py
│   │   ├── final_report.py            # → final_validation_report_schema
│   │   └── evidence_rules.json
│   │
│   ├── chunking/                      # NEW: LangChain JSON splitter module
│   │   ├── __init__.py
│   │   ├── json_splitter.py           # RecursiveJsonSplitter wrappers
│   │   ├── resume_chunker.py          # chunk_resume_json() — section-aware
│   │   ├── jd_chunker.py              # chunk_jd_json() — criteria-aware
│   │   └── evidence_chunker.py        # chunk_evd_json() — for pgvector upsert
│   │
│   ├── guardrails_config/             # NEW: Guardrails AI configurations
│   │   ├── __init__.py
│   │   ├── score_guards.py            # SimilarToPreviousValues + ValidRange
│   │   ├── explanation_guards.py      # DetectPII + ToxicLanguage + NoInference
│   │   └── weight_guards.py           # ValidRange + ValidSum for JD weights
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── jd_service.py
│   │   ├── batch_service.py
│   │   ├── admin_service.py
│   │   └── token_usage_monitor.py
│   │
│   └── api/v1/
│       ├── router.py
│       └── routes/
│           ├── auth.py
│           ├── jd.py
│           ├── batch.py
│           └── admin.py
│
├── prompts/v2/
│   ├── jd_weight_assignment/system_prompt.txt
│   ├── react_based_scoring/system_prompt.txt    # Updated ReAct with RAG evidence
│   ├── final_output_explainer/system_prompt.txt
│   └── reasoning_engine/
│       ├── phase1_structural.txt
│       ├── phase3_labels.txt
│       └── phase5_context.txt
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_hashing.py
│   │   ├── test_json_splitter.py         # NEW
│   │   ├── test_deterministic_hybrid.py  # NEW: hybrid inside deterministic
│   │   ├── test_guardrails_similar.py    # NEW: SimilarToPreviousValues
│   │   ├── test_rule_extractor.py
│   │   ├── test_mathematical_validator.py
│   │   ├── test_reasoning_engine.py
│   │   ├── test_reasoning_cross_verify.py
│   │   ├── test_agent_authority.py
│   │   └── test_evidence_rule_engine.py
│   ├── integration/
│   │   ├── test_pipeline1_resume.py
│   │   ├── test_pipeline2_jd.py
│   │   ├── test_pipeline3_scoring.py
│   │   ├── test_reasoning_pipeline.py
│   │   ├── test_rag_validation_layer.py
│   │   ├── test_hitl_flow.py
│   │   └── test_full_batch.py
│   └── eval/
│       └── test_deepeval_suite.py
│
├── migrations/env.py
├── migrations/versions/001_initial_schema.py
├── docker/Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## 4. Pydantic Schema Models (Matching All 9 Uploaded Schemas)

### 4.1 Resume Extraction Schema

```python
# app/schemas/resume.py
# Source: resume_pdf_extraction_schema.json

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class PipelineMetadata(BaseModel):
    resume_content_hash: str            # sha256: of extracted JSON
    created_at: Optional[str] = None
    source: Optional[str] = None

class ExperienceEntry(BaseModel):
    title: str
    company: str
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []

class ProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = []

class EducationEntry(BaseModel):
    degree: str
    institution: str
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    field_of_study: Optional[str] = None
    cgpa: Optional[str] = None
    institute_location: Optional[str] = None

class SalaryExpectation(BaseModel):
    value: Optional[str] = None
    currency: Optional[str] = None

class ResumeExtractionSchema(BaseModel):
    pipeline_metadata: PipelineMetadata
    name: str = Field(..., min_length=1)
    email: Optional[EmailStr] = None
    skills: List[str] = []
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    education: List[EducationEntry] = []
    candidate_achievements: List[str] = []
    certifications: List[str] = []
    tools: List[str] = []
    technologies: List[str] = []
    salary_expectation: Optional[SalaryExpectation] = None
```

### 4.2 JD Extraction Schema

```python
# app/schemas/jd.py
# Source: jd_pdf_extraction_schema.json

class PipelineMetadataJD(BaseModel):
    jd_content_hash: str               # sha256: of extracted JSON
    created_at: Optional[str] = None
    source: Optional[str] = None

class PositionLevel(BaseModel):
    senior_level: bool = False
    mid_level: bool = False
    entry_level: bool = False

class WorkMode(BaseModel):
    remote_option: bool = False
    work_from_office: bool = False
    hybrid: bool = False

class JobInformation(BaseModel):
    job_title: str
    position: Optional[PositionLevel] = None
    employment_type: Optional[str] = None   # full-time|part-time|contract|internship|temporary|other
    location: Optional[str] = None
    work_mode: Optional[WorkMode] = None

class ExperienceRange(BaseModel):
    less_than_3_years: Optional[bool] = Field(None, alias="<3_years")
    three_4_years: Optional[bool] = Field(None, alias="3_4_years")
    five_7_years: Optional[bool] = Field(None, alias="5_7_years")
    eight_plus_years: Optional[bool] = Field(None, alias="8_plus_years")

class ExperienceRequirements(BaseModel):
    experience_range: Optional[ExperienceRange] = None
    minimum_years: Optional[float] = None
    preferred_years: Optional[float] = None

class QualificationLevel(BaseModel):
    phd: bool = False
    masters: bool = False
    bachelors: bool = False
    associate: bool = False
    diploma: bool = False
    certification: bool = False

class EducationRequirements(BaseModel):
    qualification: Optional[QualificationLevel] = None
    preferred_field_of_study: List[str] = []

class SkillsAndTechnologies(BaseModel):
    technologies: List[str] = []
    skills: List[str] = []
    tools: List[str] = []
    certifications: List[str] = []

class JobDetails(BaseModel):
    job_description: Optional[str] = None
    responsibilities: List[str] = []
    requirements: List[str] = []
    preferred_qualifications: List[str] = []

class JDExtractionSchema(BaseModel):
    pipeline_metadata: PipelineMetadataJD
    job_information: JobInformation
    experience_requirements: Optional[ExperienceRequirements] = None
    education_requirements: Optional[EducationRequirements] = None
    skills_and_technologies: Optional[SkillsAndTechnologies] = None
    job_details: Optional[JobDetails] = None
```

### 4.3 JD Weights Schema

```python
# app/schemas/jd_weights.py
# Source: jd_weights_schema_format.json

class WeightGenerationMetadata(BaseModel):
    raw_weight: float = 0
    criteria_count: int = 0
    normalization_method: str = "criteria_average_normalized"
    normalization_factor: float = 0

class WeightingMetadata(BaseModel):
    weight_generation_strategy: str = "criteria_average_normalized"
    normalization_applied: bool = True
    total_raw_weight: float = 0
    normalized_total_weight: float = 100

class ScoringSection(BaseModel):
    weight: float = 0
    weight_generation_metadata: WeightGenerationMetadata
    criteria: dict = {}                 # label → score mapping

class SalarySection(BaseModel):
    weight: float = 0
    weight_generation_metadata: WeightGenerationMetadata
    fallback_score: float = 50
    criteria_based_on_salary_expectation: dict = {"3-6": 0, "6-10": 0, ">10": 0}

class JDScoringBlock(BaseModel):
    relevant_experience: ScoringSection
    experience: ScoringSection
    qualification: ScoringSection
    technologies: ScoringSection
    skills: ScoringSection
    position: ScoringSection
    tools: ScoringSection
    certifications: ScoringSection
    responsibilities: ScoringSection
    salary: SalarySection

class JDWeightsSchema(BaseModel):
    jd_content_hash: str
    weighting_metadata: WeightingMetadata
    job_title: str = ""
    experience: str = ""
    qualification: str = ""
    technologies: List[str] = []
    skills: List[str] = []
    tools: List[str] = []
    certifications: List[str] = []
    location: str = ""
    position: str = ""
    job_description: str = ""
    responsibilities: List[str] = []
    employment_type: str = ""
    work_mode: WorkMode
    scoring: JDScoringBlock

    def validate_weight_sum(self) -> tuple[bool, float]:
        total = sum([
            self.scoring.relevant_experience.weight,
            self.scoring.experience.weight,
            self.scoring.qualification.weight,
            self.scoring.technologies.weight,
            self.scoring.skills.weight,
            self.scoring.position.weight,
            self.scoring.tools.weight,
            self.scoring.certifications.weight,
            self.scoring.responsibilities.weight,
            self.scoring.salary.weight,
        ])
        return abs(total - 100.0) <= 0.5, round(total, 4)
```

### 4.4 Deterministic Validator Output Schema

```python
# app/schemas/deterministic_output.py
# Source: deterministic_validator_output_schema.json

class MatchItem(BaseModel):
    jd_item: str
    resume_match: str
    similarity: float = Field(..., ge=0, le=1)  # 0.0–1.0 cosine similarity
    weight: float

class SemanticMetrics(BaseModel):
    matched_skills: List[MatchItem]
    weighted_coverage: float            # aggregate weighted coverage %
    token_overlap: float                # token-level overlap ratio

class SectionResult(BaseModel):
    valid: bool
    errors: List[str]
    resume_semantic_metrics: Optional[SemanticMetrics] = None

class OverallAnalytics(BaseModel):
    matched_skills: List[MatchItem]
    weighted_coverage: float
    token_overlap: float

class DeterministicValidatorOutput(BaseModel):
    is_valid: bool
    overall_analytics: OverallAnalytics
    errors: List[str]
    section_results: dict[str, SectionResult]   # dynamic section keys
```

### 4.5 Mathematical Validator Report Schema

```python
# app/schemas/mathematical_report.py
# Source: mathematical_validator_report_schema.json

class GlobalMetrics(BaseModel):
    ground_truth_final_score: float
    ai_final_score: float
    overall_accuracy: float
    is_valid: bool                      # accuracy >= 80%
    mae: float
    rmse: float
    total_weight_checked: float

class MathematicalValidatorReport(BaseModel):
    section_accuracy: dict[str, float]      # section → accuracy %
    ground_truth_scores: dict[str, float]   # section → deterministic score
    ai_scores: dict[str, float]             # section → AI score
    global_metrics: GlobalMetrics
```

### 4.6 Rule-Based Evidence Schema

```python
# app/schemas/rule_based_evidence.py
# Source: rule_based_evidence_schema.json

from typing import Literal

class CriterionEvidence(BaseModel):
    criterion: str
    criterion_weight: Optional[float] = None
    matched: bool
    evidence: Optional[str] = None

class ActionApplied(BaseModel):
    explanation: str
    score_after: float

class RuleEntry(BaseModel):
    rule_id: str
    description: str
    fired: bool
    condition_evaluation: str
    action_applied: ActionApplied

class SectionEvidence(BaseModel):
    section_name: str
    section_weight: float
    rule_type: str
    criteria_evaluated: List[CriterionEvidence]
    total_criteria: Optional[float] = None
    matched_count: Optional[float] = None
    coverage_pct: float
    base_coverage_pct: Optional[float] = None
    ai_score: float
    ground_truth_score: float
    score_delta: float
    verdict: Literal["ACCURATE", "OVERESTIMATED", "UNDERESTIMATED"]
    applied_rules: List[RuleEntry]

class OverallSummary(BaseModel):
    total_sections: float
    sections_with_overestimation: float
    sections_with_underestimation: float
    sections_accurate: float
    ai_final_score: float
    rule_based_final_score: float
    delta: float

class RuleApplications(BaseModel):
    total_rules_generated: float
    rule_log: List[RuleEntry]

class RuleBasedEvidenceSchema(BaseModel):
    evidence_id: str
    timestamp: str
    job_id: str
    job_title: str
    section_evidences: List[SectionEvidence]
    overall_summary: OverallSummary
    rule_applications: RuleApplications
```

### 4.7 Final Result Scoring Agent Schema

```python
# app/schemas/final_result.py
# Source: final_result_scoring_agent_schema.json
# This is the CANONICAL output of score_adjustment_node

class ScoringTraceEntry(BaseModel):
    score_awarded: float
    weight: float
    notes: str

class AgentResult(BaseModel):
    final_score: float
    skills_score: float
    experience_score: float
    relevant_experience_score: float
    projects_score: float
    certificates_score: float
    tools_score: float
    technologies_score: float
    qualification_score: float
    responsibilities_score: float
    salary_score: float
    position_score: float
    notes: str
    scoring_trace: dict[str, ScoringTraceEntry]
    guardrails_applied: List[str]           # list of fired guardrail names

class StateHistory(BaseModel):
    from_state: str
    to_state: str
    timestamp: str
    reason: Optional[str] = None

class FinalResultScoringAgent(BaseModel):
    current_state: Literal["INIT","VALIDATING_INPUT","FETCHING_CONTEXT",
                            "SCORING","VERIFYING_OUTPUT","COMPLETED","FAILED"]
    inputs: dict                            # resume + jd + weights
    history: List[StateHistory]
    result: AgentResult
    error: Optional[Any] = None
    success: bool
    token_usage: Optional[dict] = None
```

### 4.8 Extracted Rules Schema

```python
# app/schemas/extracted_rules.py
# Source: extracted_rules_schema.json

class ExtractedSectionRule(BaseModel):
    weight: float
    min_score: float
    max_score: float
    allowed_scores: List[float]
    criteria: dict[str, float]          # criterion label → score
    jd_items: List[str]
    required: bool
    description: str

# ExtractedRules is dynamic: dict[section_name, ExtractedSectionRule]
ExtractedRules = dict[str, ExtractedSectionRule]
```

---

## 5. LangChain RecursiveJsonSplitter — Chunking Implementation

### 5.1 Why RecursiveJsonSplitter

The `RecursiveJsonSplitter` from LangChain recursively splits nested JSON by traversing keys
at each level, preserving semantic context. This is critical for our structured schemas because:
- Resume JSON has deep nesting (experience[].responsibilities[], projects[].technologies[])
- JD weights JSON has scoring.{section}.criteria that must stay together
- Evidence documents (EVD_*.json) have raw_sources with deeply nested validator outputs

### 5.2 Chunker Implementation

```python
# app/chunking/json_splitter.py

from langchain_text_splitters import RecursiveJsonSplitter
from app.core.hashing import hash_content
import json

# Global splitter instances for different max chunk sizes
RESUME_SPLITTER  = RecursiveJsonSplitter(max_chunk_size=300)   # tokens
JD_SPLITTER      = RecursiveJsonSplitter(max_chunk_size=400)
EVIDENCE_SPLITTER = RecursiveJsonSplitter(max_chunk_size=500)

def split_json_to_chunks(data: dict, splitter: RecursiveJsonSplitter,
                          dimension_tag: str, source: str) -> list[dict]:
    """
    Split a JSON dict into chunks using RecursiveJsonSplitter.
    Each chunk is tagged with dimension and source for pgvector metadata.
    """
    # RecursiveJsonSplitter.split_json returns list of dicts (sub-JSON objects)
    json_chunks = splitter.split_json(json_data=data)

    chunks = []
    for i, chunk_dict in enumerate(json_chunks):
        chunk_text = json.dumps(chunk_dict, separators=(",", ":"), sort_keys=True)
        chunks.append({
            "text":       chunk_text,
            "dimension":  dimension_tag,
            "source":     source,
            "chunk_index": i,
            "chunk_hash": hash_content(chunk_text)
        })
    return chunks
```

### 5.3 Resume Chunker

```python
# app/chunking/resume_chunker.py

from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks

SECTION_DIMENSION_MAP = {
    "skills":               "technical_skills",
    "technologies":         "technical_skills",
    "tools":                "tool_fit",
    "experience":           "experience_fit",
    "education":            "education_fit",
    "certifications":       "certification_fit",
    "projects":             "domain_fit",
    "candidate_achievements": "domain_fit",
    "salary_expectation":   "salary",
}

def chunk_resume_json(resume_parsed: dict) -> list[dict]:
    """
    Section-aware chunking using RecursiveJsonSplitter.
    Each top-level section is split independently to preserve semantic boundaries.
    """
    from langchain_text_splitters import RecursiveJsonSplitter
    splitter = RecursiveJsonSplitter(max_chunk_size=300)
    all_chunks = []

    # Split each section independently
    for section_key, dimension in SECTION_DIMENSION_MAP.items():
        section_data = resume_parsed.get(section_key)
        if not section_data:
            continue

        # Wrap list fields in a dict for the splitter
        if isinstance(section_data, list):
            data_to_split = {section_key: section_data}
        elif isinstance(section_data, dict):
            data_to_split = {section_key: section_data}
        else:
            data_to_split = {section_key: str(section_data)}

        chunks = split_json_to_chunks(
            data=data_to_split,
            splitter=splitter,
            dimension_tag=dimension,
            source="resume"
        )
        all_chunks.extend(chunks)

    # Always add pipeline_metadata as a small identity chunk
    meta = resume_parsed.get("pipeline_metadata", {})
    if meta:
        identity = {
            "name":  resume_parsed.get("name", ""),
            "email": resume_parsed.get("email", ""),
            "pipeline_metadata": meta
        }
        all_chunks.extend(split_json_to_chunks(
            data=identity, splitter=splitter,
            dimension_tag="identity", source="resume"
        ))

    return all_chunks
```

### 5.4 JD Chunker

```python
# app/chunking/jd_chunker.py

from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks

def chunk_jd_json(jd_normalized: dict, jd_weights: dict) -> list[dict]:
    """
    Criteria-aware JD chunking.
    Each scoring section (with its criteria) is split as an independent sub-JSON.
    """
    splitter = RecursiveJsonSplitter(max_chunk_size=400)
    all_chunks = []

    scoring = jd_weights.get("scoring", {})
    for section_name, section_data in scoring.items():
        # Combine section data with JD items for richer context
        jd_items = _get_jd_items_for_section(section_name, jd_normalized)
        chunk_data = {
            "section": section_name,
            "weight":  section_data.get("weight", 0),
            "criteria": section_data.get("criteria", {}),
            "jd_items": jd_items
        }
        chunks = split_json_to_chunks(
            data=chunk_data, splitter=splitter,
            dimension_tag=section_name, source="jd"
        )
        all_chunks.extend(chunks)

    # Add job information as a domain_fit chunk
    job_info = {
        "job_title":    jd_normalized.get("job_title", ""),
        "position":     jd_normalized.get("position", ""),
        "job_description": jd_normalized.get("job_description", "")[:500],
        "responsibilities": jd_normalized.get("responsibilities", [])[:5]
    }
    all_chunks.extend(split_json_to_chunks(
        data=job_info, splitter=splitter,
        dimension_tag="domain_fit", source="jd"
    ))
    return all_chunks


def _get_jd_items_for_section(section: str, jd: dict) -> list[str]:
    mapping = {
        "technologies": jd.get("technologies", []),
        "skills":       jd.get("skills", []),
        "tools":        jd.get("tools", []),
        "certifications": jd.get("certifications", []),
        "responsibilities": jd.get("responsibilities", [])[:8],
    }
    return mapping.get(section, [])
```

### 5.5 Evidence Chunker (for pgvector upsert of EVD documents)

```python
# app/chunking/evidence_chunker.py

from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks
import json

def chunk_evd_json(evd_doc: dict) -> list[dict]:
    """
    Chunk EVD_{ts}_{uuid}.json for pgvector upsert.
    Strategy: one chunk per section_evidence entry + 1 summary chunk.
    Uses RecursiveJsonSplitter for nested raw_sources.
    Chunk IDs: "{evidence_id}#{section_name}"
    """
    splitter = RecursiveJsonSplitter(max_chunk_size=500)
    evidence_id = evd_doc.get("evidence_id", "EVD_unknown")
    all_chunks = []

    # Per-section chunks from rule_based evidence
    for section_ev in evd_doc.get("raw_sources", {}).get("rule_based_evidence", {}).get("section_evidences", []):
        section_name = section_ev.get("section_name", "unknown")
        chunk_data = {
            "evidence_id":    evidence_id,
            "section_name":   section_name,
            "verdict":        section_ev.get("verdict"),
            "ai_score":       section_ev.get("ai_score"),
            "ground_truth":   section_ev.get("ground_truth_score"),
            "score_delta":    section_ev.get("score_delta"),
            "coverage_pct":   section_ev.get("coverage_pct"),
            "applied_rules":  [r["rule_id"] for r in section_ev.get("applied_rules", []) if r.get("fired")],
            "criteria_evaluated": section_ev.get("criteria_evaluated", [])[:5]
        }
        chunks = split_json_to_chunks(
            data=chunk_data, splitter=splitter,
            dimension_tag=section_name, source="rag_evidence"
        )
        # Tag each chunk with evidence_id and section for pgvector metadata
        for c in chunks:
            c["evidence_id"]  = evidence_id
            c["source_type"]  = "rule_based"
            c["section_name"] = section_name
        all_chunks.extend(chunks)

    # Summary chunk
    summary_data = {
        "evidence_id":   evidence_id,
        "job_title":     evd_doc.get("job_title"),
        "summary":       evd_doc.get("summary", {}),
        "keywords":      evd_doc.get("keywords", []),
        "text_blob":     evd_doc.get("text_blob", "")[:400]
    }
    summary_chunks = split_json_to_chunks(
        data=summary_data, splitter=splitter,
        dimension_tag="summary", source="rag_evidence"
    )
    for c in summary_chunks:
        c["evidence_id"]  = evidence_id
        c["source_type"]  = "historical"
        c["section_name"] = "summary"
    all_chunks.extend(summary_chunks)

    return all_chunks
```

---

## 6. Hybrid Search INSIDE DeterministicValidator

### 6.1 Why Hybrid Search in Deterministic Validation

The existing deterministic_validator used only BGE cosine similarity for semantic matching.
By adding BM25 sparse search alongside BGE dense search and fusing with RRF, we achieve:
- Better exact-term matching for technical keywords (Python, FastAPI, Docker)
- Semantic fallback for paraphrased requirements ("REST API" ↔ "API development")
- Higher precision hallucination detection (BM25 penalises unsupported claims)

### 6.2 DeterministicValidator with Hybrid Search

```python
# app/RAG_Validation_layer/deterministic_validator.py
# Source: deterministic_validator_output_schema.json

from langsmith import traceable
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from app.schemas.deterministic_output import (
    DeterministicValidatorOutput, OverallAnalytics, SectionResult,
    SemanticMetrics, MatchItem
)
import numpy as np, logging

logger = logging.getLogger("DeterministicValidator")

BGE_MODEL  = SentenceTransformer("BAAI/bge-large-en-v1.5")
DENSE_THRESH  = 0.65
PARTIAL_THRESH = 0.50
BM25_WEIGHT   = 0.35     # RRF weight for BM25 in hybrid
DENSE_WEIGHT  = 0.65     # RRF weight for BGE dense in hybrid
RRF_K         = 60

SECTION_FIELD_MAP = {
    "skills":              ["skills"],
    "technologies":        ["technologies"],
    "tools":               ["tools"],
    "certifications":      ["certifications"],
    "relevant_experience": ["experience"],
    "experience":          ["experience"],
    "qualification":       ["education"],
    "responsibilities":    ["experience", "projects"],
    "position":            ["experience"],
}

class DeterministicValidator:

    def __init__(self, jd_data: dict):
        from app.RAG_Validation_layer.rule_extractor import RuleExtractor
        from app.RAG_Validation_layer.normalizer_pre_score import normalize_for_scoring
        self.jd_data = jd_data
        self._normalize = normalize_for_scoring
        jd_text = jd_data.get("job_description", "")
        extractor = RuleExtractor(jd_text)
        self.hard_rules = extractor.extract_hard_rules()
        self.soft_rules = extractor.extract_soft_rules()
        self.required_tools = extractor.extract_required_tools()

    @traceable(name="deterministic_validator", run_type="chain")
    def validate(self, resume_payload: dict) -> DeterministicValidatorOutput:
        ai_score    = resume_payload.get("ai_score", {})
        parsed_json = resume_payload.get("parsed_json", {})
        norm_resume = self._normalize(parsed_json)

        section_results: dict[str, SectionResult] = {}
        all_matched: list[MatchItem] = []
        overall_valid = True

        scoring = self.jd_data.get("scoring", {})
        for section_name, section_data in scoring.items():
            jd_criteria = section_data.get("criteria", {})
            if not jd_criteria:
                section_results[section_name] = SectionResult(
                    valid=True, errors=[], resume_semantic_metrics=None)
                continue

            resume_fields = SECTION_FIELD_MAP.get(section_name, ["skills"])
            resume_items  = self._collect_resume_items(norm_resume, resume_fields)
            jd_items      = list(jd_criteria.keys())

            # ── Hybrid search: Dense + BM25 per JD item ──────────────
            matched, unmatched = self._hybrid_match_section(
                jd_items=jd_items,
                resume_items=resume_items,
                section_weight=section_data.get("weight", 0)
            )
            all_matched.extend(matched)

            # ── Hallucination check ───────────────────────────────────
            hallucinated = self._detect_hallucinations(ai_score, section_name, jd_items)

            section_valid = len(hallucinated) == 0
            if not section_valid:
                overall_valid = False

            # ── Build section metrics ─────────────────────────────────
            weighted_cov = (len(matched) / len(jd_items) * 100) if jd_items else 0
            token_overlap = self._compute_token_overlap(jd_items, resume_items)

            section_results[section_name] = SectionResult(
                valid=section_valid,
                errors=hallucinated,
                resume_semantic_metrics=SemanticMetrics(
                    matched_skills=matched,
                    weighted_coverage=round(weighted_cov, 2),
                    token_overlap=round(token_overlap, 4)
                )
            )

        # ── Overall analytics ─────────────────────────────────────────
        overall_cov = (len(all_matched) / max(sum(
            len(list(sd.get("criteria",{}).keys()))
            for sd in scoring.values()
        ), 1)) * 100

        return DeterministicValidatorOutput(
            is_valid=overall_valid,
            overall_analytics=OverallAnalytics(
                matched_skills=all_matched,
                weighted_coverage=round(overall_cov, 2),
                token_overlap=0.0     # computed globally if needed
            ),
            errors=[],
            section_results=section_results
        )

    def _hybrid_match_section(self, jd_items: list[str], resume_items: list[str],
                               section_weight: float) -> tuple[list[MatchItem], list[str]]:
        """
        For each JD item: compute (a) BGE dense cosine, (b) BM25 score.
        Fuse with RRF, apply threshold, return matched MatchItems.
        """
        if not resume_items or not jd_items:
            return [], jd_items

        # ── Dense embeddings (BGE) ────────────────────────────────────
        jd_embs     = BGE_MODEL.encode(jd_items, normalize_embeddings=True)
        resume_embs = BGE_MODEL.encode(resume_items, normalize_embeddings=True)
        dense_sims  = jd_embs @ resume_embs.T   # shape: [len(jd), len(resume)]

        # ── BM25 sparse ───────────────────────────────────────────────
        tokenized_corpus = [r.lower().split() for r in resume_items]
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores_matrix = np.array([
            bm25.get_scores(jd_item.lower().split())
            for jd_item in jd_items
        ])   # shape: [len(jd), len(resume)]

        # Normalize BM25 to [0,1]
        bm25_max = bm25_scores_matrix.max() + 1e-10
        bm25_norm = bm25_scores_matrix / bm25_max

        # ── RRF fusion ────────────────────────────────────────────────
        def rrf_score(rank):
            return 1.0 / (RRF_K + rank + 1)

        matched, unmatched = [], []
        for i, jd_item in enumerate(jd_items):
            dense_row = dense_sims[i]
            bm25_row  = bm25_norm[i]

            # Rank resume items by each method
            dense_ranks = np.argsort(-dense_row)
            bm25_ranks  = np.argsort(-bm25_row)
            dense_rank_map = {idx: r for r, idx in enumerate(dense_ranks)}
            bm25_rank_map  = {idx: r for r, idx in enumerate(bm25_ranks)}

            # Compute RRF hybrid score per resume item
            rrf_scores = [
                DENSE_WEIGHT * rrf_score(dense_rank_map[j]) +
                BM25_WEIGHT  * rrf_score(bm25_rank_map[j])
                for j in range(len(resume_items))
            ]
            best_idx   = int(np.argmax(rrf_scores))
            best_dense = float(dense_row[best_idx])
            best_rrf   = max(rrf_scores)

            # Use dense similarity as the canonical similarity score
            if best_dense >= DENSE_THRESH:
                matched.append(MatchItem(
                    jd_item=jd_item,
                    resume_match=resume_items[best_idx],
                    similarity=round(best_dense, 4),
                    weight=section_weight
                ))
            else:
                unmatched.append(jd_item)

        return matched, unmatched

    def _detect_hallucinations(self, ai_score: dict, section: str,
                                jd_items: list[str]) -> list[str]:
        """Check that AI-claimed items for this section actually exist in JD."""
        if not isinstance(ai_score, dict):
            return []
        claimed = ai_score.get(f"{section}_score", None)
        if claimed is None or claimed == 0:
            return []
        # If AI gave a positive score but JD has no criteria → hallucination
        if not jd_items and claimed > 0:
            return [f"Hallucination: section '{section}' scored {claimed} but JD has no criteria"]
        return []

    def _collect_resume_items(self, norm_resume: dict, fields: list[str]) -> list[str]:
        items = []
        for field in fields:
            val = norm_resume.get(field, [])
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, str):
                        items.append(entry)
                    elif isinstance(entry, dict):
                        items.append(entry.get("title","") + " " + entry.get("company",""))
        return [i.strip() for i in items if i.strip()]

    def _compute_token_overlap(self, jd_items: list[str], resume_items: list[str]) -> float:
        jd_tokens  = set(" ".join(jd_items).lower().split())
        res_tokens = set(" ".join(resume_items).lower().split())
        if not jd_tokens:
            return 0.0
        return len(jd_tokens & res_tokens) / len(jd_tokens)
```

---

## 7. Guardrails AI — SimilarToPreviousValues

### 7.1 What SimilarToPreviousValues Does

`SimilarToPreviousValues` (from the Guardrails Hub : https://github.com/guardrails-ai/guardrails) validates that a new value is semantically
or numerically similar to a set of previously seen valid values. In RAIYA, we use it to:
1. Detect sudden score drift between consecutive candidates for the same JD
2. Flag when the reasoning engine's score adjustment deviates anomalously
3. Prevent AI over-estimation creep across batch processing

**Reference:** https://guardrailsai.com/hub/validator/guardrails/similar_to_previous_values

### 7.2 Score Guards Implementation

```python
# app/guardrails_config/score_guards.py

from guardrails import Guard
from guardrails.hub import SimilarToPreviousValues, ValidRange
from app.db.redis_client import redis_client
import json, logging

logger = logging.getLogger("ScoreGuards")

# ── SimilarToPreviousValues config ────────────────────────────────
# Stores previous valid section scores per JD in Redis
# If new score deviates by > threshold → flag as anomaly

SECTION_SCORE_GUARD = Guard().use(
    SimilarToPreviousValues(
        standard_deviations=2.0,    # flag if > 2 std devs from rolling mean
        on_fail="fix"               # clamp to closest valid prior value
    )
)

FINAL_SCORE_RANGE_GUARD = Guard().use_many(
    ValidRange(min=0, max=100, on_fail="exception"),
    SimilarToPreviousValues(
        standard_deviations=2.5,
        on_fail="fix"
    )
)

async def validate_section_score(section: str, score: float,
                                  jd_id: str) -> tuple[float, bool]:
    """
    Validate a section score using SimilarToPreviousValues.
    Returns (validated_score, was_corrected).
    """
    redis_key = f"score_history:{jd_id}:{section}"
    raw = await redis_client.get(redis_key)
    previous_scores: list[float] = json.loads(raw) if raw else []

    if len(previous_scores) < 3:
        # Not enough history — just range check
        validated = max(0.0, min(100.0, score))
        previous_scores.append(score)
        await redis_client.setex(redis_key, 86400, json.dumps(previous_scores[-20:]))
        return validated, False

    try:
        result = SECTION_SCORE_GUARD.validate(
            value=score,
            metadata={"prev_values": previous_scores}
        )
        validated_score = float(result.validated_output or score)
        was_corrected = validated_score != score
        if was_corrected:
            logger.warning(
                f"[Guardrails] {section} score corrected: {score:.2f} → {validated_score:.2f} "
                f"(prev_mean={sum(previous_scores)/len(previous_scores):.2f})"
            )
        previous_scores.append(validated_score)
        await redis_client.setex(redis_key, 86400, json.dumps(previous_scores[-20:]))
        return validated_score, was_corrected
    except Exception as e:
        logger.error(f"[Guardrails] SimilarToPreviousValues error: {e}")
        return max(0.0, min(100.0, score)), False


async def apply_batch_score_guards(
    section_scores: dict[str, float],
    jd_id: str
) -> tuple[dict[str, float], list[str]]:
    """
    Apply SimilarToPreviousValues to all section scores.
    Returns (validated_scores, list of guardrail names that fired).
    """
    validated = {}
    fired = []
    for section, score in section_scores.items():
        v_score, corrected = await validate_section_score(section, score, jd_id)
        validated[section] = v_score
        if corrected:
            fired.append(f"SimilarToPreviousValues:{section}")
    return validated, fired
```

### 7.3 Explanation Guards

```python
# app/guardrails_config/explanation_guards.py

from guardrails import Guard
from guardrails.hub import DetectPII, ToxicLanguage

EXPLANATION_GUARD = Guard().use_many(
    DetectPII(on_fail="anonymize"),
    ToxicLanguage(on_fail="filter")
)

INFERENCE_PHRASES = [
    "likely", "probably", "seems to", "appears to", "suggests",
    "indicates potential", "may have", "could be", "we can infer",
    "implies", "strong candidate", "good fit", "promising",
    "talented", "impressive", "capable of"
]

def validate_explanation_guardrails(text: str) -> tuple[str, list[str]]:
    """Apply explanation guards + inference language check."""
    fired = []
    try:
        result = EXPLANATION_GUARD.validate(value=text)
        text = result.validated_output or text
    except Exception:
        pass

    # Inference language check
    for phrase in INFERENCE_PHRASES:
        if phrase.lower() in text.lower():
            fired.append(f"InferenceLanguage:{phrase}")

    return text, fired
```

### 7.4 Weight Guards

```python
# app/guardrails_config/weight_guards.py

from guardrails import Guard
from guardrails.hub import ValidRange

WEIGHT_GUARD = Guard().use(
    ValidRange(min=0, max=100, on_fail="exception")
)

def validate_jd_weights(weights_schema: dict) -> tuple[bool, list[str]]:
    """Validate all section weights are in range and sum to 100."""
    errors = []
    scoring = weights_schema.get("scoring", {})
    total = 0.0
    for section, data in scoring.items():
        w = data.get("weight", 0)
        try:
            WEIGHT_GUARD.validate(value=w)
        except Exception:
            errors.append(f"Weight out of range [0,100]: {section}={w}")
        total += w
    if abs(total - 100.0) > 0.5:
        errors.append(f"Weights sum={total:.4f} deviates from 100 (tolerance=0.5)")
    return len(errors) == 0, errors
```

---

## 8. ReAct Pattern — Corrected with RAG Evidence as Context

### 8.1 How ReAct Validates the Reasoning Engine Score

The key insight is that the **ReAct scoring agent receives RAG validation evidence as context**.
This is not just grounding — it is the mechanism by which the reasoning engine's labels
are validated against deterministic ground truth:

```
THOUGHT:   The reasoning engine assigned label "strong" for technical_fit.
ACTION:    Retrieve deterministic_validator section_results["technologies"]
           and mathematical_validator ground_truth_scores["technologies"].
OBSERVATION: deterministic: weighted_coverage=82%, matched=["Python","FastAPI","Docker"]
             mathematical:  ground_truth=18.4, ai_score=19.0, delta=+0.6 (ACCURATE)
             reasoning label range for "strong": (0.80, 1.00)
             hybrid_score=0.84 → within "strong" range ✓
SCORE:     Apply section weight 20. Adjusted score = 0.84 × 20 = 16.8
```

The ReAct agent's job is to confirm or correct the reasoning engine's labels using
deterministic evidence. If the deterministic report contradicts the label, the label
is corrected before scoring.

### 8.2 Updated ReAct Prompt (with RAG Evidence as Mandatory Context)

```
File: prompts/v2/react_based_scoring/system_prompt.txt

SYSTEM ROLE
You are a deterministic Resume-to-JD Scoring Agent in an audit-safe AI pipeline.

PIPELINE POSITION:
You run AFTER:
  (a) Hybrid search produced section_similarities
  (b) 5-phase reasoning engine assigned categorical labels
  (c) RAG validation layer produced deterministic + mathematical + rule-based reports

Your output is validated by AuthorityGovernance FSM and Guardrails AI
(SimilarToPreviousValues + ValidRange).

YOUR PRIMARY INPUTS (in order of priority):
1. reasoning_context   — Phase 5 narrative from reasoning engine (your grounding)
2. deterministic_report — section_results per section (hybrid search matched items)
3. mathematical_report  — ground_truth_scores vs ai_scores per section
4. rule_based_evidence  — section_evidences with verdicts (ACCURATE/OVER/UNDER)
5. reasoning_labels     — categorical labels from Phase 3+4 (verified)
6. section_similarities — dense+BM25+exact hybrid scores per section
7. jd_weights           — section weights (jd_weights_schema_format)
8. resume_parsed        — RESUME_EXTRACTION_SCHEMA (evidence naming only)

REACT PATTERN — EXECUTE for EVERY SECTION in jd_weights.scoring:

THOUGHT:
  State the section being evaluated.
  State the reasoning label and its allowed score range.
  State the deterministic weighted_coverage for this section.
  State the mathematical ground_truth_score and verdict.

ACTION:
  Compare reasoning label range to hybrid_score.
  Compare ai_score in mathematical_report to ground_truth_score.
  Check rule_based_evidence verdict for this section.
  If verdict = OVERESTIMATED → apply downward correction.
  If verdict = UNDERESTIMATED → apply upward correction.
  Clamp corrected score to label range.

OBSERVATION:
  Explicit match confirmation (from deterministic matched_skills list).
  State delta between ai_score and ground_truth_score.
  State which rules fired in applied_rules list (if any).
  State final adjusted score before weight multiplication.

SCORE:
  final_section_score = adjusted_score × (jd_section_weight / 100) × 100
  Add to scoring_trace: score_awarded, weight, notes.

FINALIZE:
  final_score = Σ(final_section_score for all sections)
  Apply Guardrails SimilarToPreviousValues check.
  Populate guardrails_applied with list of fired guardrail names.
  Produce final_result_scoring_agent_schema JSON.

STRICT RULES:
- NEVER produce a section score outside the reasoning label's allowed range
- NEVER modify jd_weights.scoring.*.weight values
- NEVER infer skills not in resume_parsed or deterministic matched_skills
- NEVER score a section > 0 if deterministic coverage = 0 and no matched items
- mathematical_report is the authoritative ground truth — defer to it on large deltas
- If rule verdict = OVERESTIMATED → cap adjusted score at ground_truth_score
- If rule verdict = UNDERESTIMATED → floor adjusted score at ground_truth_score × 0.9
- guardrails_applied must list every SimilarToPreviousValues correction that fired

RETURN final_result_scoring_agent_schema JSON (no markdown):
{
  "current_state": "COMPLETED",
  "inputs": { "resume": {...}, "jd": {...}, "weights": {...} },
  "history": [...],
  "result": {
    "final_score": <float 0-100>,
    "skills_score": <float>,
    "experience_score": <float>,
    "relevant_experience_score": <float>,
    "projects_score": <float>,
    "certificates_score": <float>,
    "tools_score": <float>,
    "technologies_score": <float>,
    "qualification_score": <float>,
    "responsibilities_score": <float>,
    "salary_score": <float>,
    "position_score": <float>,
    "notes": "<brief scoring notes>",
    "scoring_trace": {
      "<section>": {
        "score_awarded": <float>,
        "weight": <float>,
        "notes": "<react trace summary for this section>"
      }
    },
    "guardrails_applied": ["SimilarToPreviousValues:technologies", ...]
  },
  "success": true,
  "token_usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
}
```

---

## 9. Score Adjustment Node — Full Implementation

```python
# app/agents/nodes/pipeline3/score_adjustment.py

from app.schemas.final_result import FinalResultScoringAgent, AgentResult, ScoringTraceEntry
from app.guardrails_config.score_guards import apply_batch_score_guards
from app.agents.agent_state import AgentState
from app.core.hashing import hash_json
from langsmith import traceable

SECTION_TO_LABEL_DIMENSION = {
    "technologies":        "technical_fit",
    "skills":              "technical_fit",
    "tools":               "tool_fit",
    "relevant_experience": "experience_fit",
    "experience":          "experience_fit",
    "qualification":       "education_fit",
    "certifications":      "certification_fit",
    "position":            "seniority_fit",
    "responsibilities":    "domain_fit",
    "salary":              "soft_skill_fit"
}

LABEL_SCORE_RANGES = {
    "technical_fit":  {"strong":(0.80,1.00),"moderate":(0.55,0.79),"weak":(0.30,0.54),"none":(0.00,0.29)},
    "experience_fit": {"exceeds":(0.90,1.00),"meets":(0.70,0.89),"below":(0.40,0.69),"significantly_below":(0.00,0.39)},
    "seniority_fit":  {"overqualified":(0.50,0.70),"match":(0.80,1.00),"junior":(0.30,0.59),"intern":(0.00,0.29)},
    "education_fit":  {"exceeds":(0.85,1.00),"meets":(0.60,0.84),"below":(0.00,0.59)},
    "domain_fit":     {"deep":(0.80,1.00),"moderate":(0.55,0.79),"surface":(0.25,0.54),"none":(0.00,0.24)},
    "certification_fit":{"all_present":(0.90,1.00),"some_present":(0.40,0.89),"none":(0.00,0.39)},
    "tool_fit":       {"full":(0.85,1.00),"partial":(0.40,0.84),"none":(0.00,0.39)},
    "soft_skill_fit": {"strong":(0.75,1.00),"moderate":(0.45,0.74),"weak":(0.00,0.44)}
}

@traceable(name="score_adjustment_node", run_type="chain")
async def score_adjustment_node(state: dict) -> dict:
    section_sims   = state["section_similarities"]
    labels         = state["reasoning_labels"]
    det_report     = state["deterministic_report"]
    math_report    = state["mathematical_report"]
    rule_evidence  = state["rule_based_evidence"]
    jd_weights     = state["jd_weights"]["scoring"]
    jd_id          = state["jd_id"]

    section_scores = {}
    scoring_trace  = {}
    notes_parts    = []

    for section, sec_data in jd_weights.items():
        jd_weight = sec_data.get("weight", 0)
        if jd_weight == 0:
            section_scores[section] = 0.0
            scoring_trace[section] = ScoringTraceEntry(
                score_awarded=0.0, weight=0.0, notes="Section weight=0; skipped")
            continue

        hybrid = section_sims.get(section, {}).get("hybrid_score", 0.0)

        # Step 1: Constrain to reasoning label range
        dim   = SECTION_TO_LABEL_DIMENSION.get(section, "technical_fit")
        label = labels.get(dim, "moderate")
        lo, hi = LABEL_SCORE_RANGES.get(dim, {}).get(label, (0.0, 1.0))
        constrained = max(lo, min(hi, hybrid))

        # Step 2: Apply mathematical report correction
        gt_score = math_report.get("ground_truth_scores", {}).get(section)
        ai_score = math_report.get("ai_scores", {}).get(section)
        section_ev = _find_section_evidence(rule_evidence, section)
        verdict = section_ev.get("verdict", "ACCURATE") if section_ev else "ACCURATE"

        correction_note = ""
        if verdict == "OVERESTIMATED" and gt_score is not None:
            old = constrained
            constrained = min(constrained, gt_score / 100.0)
            correction_note = f"OVER: capped {old:.3f}→{constrained:.3f} by gt={gt_score}"
        elif verdict == "UNDERESTIMATED" and gt_score is not None:
            old = constrained
            constrained = max(constrained, (gt_score / 100.0) * 0.9)
            correction_note = f"UNDER: floored {old:.3f}→{constrained:.3f} by gt×0.9"

        # Step 3: Deterministic penalties
        if det_report.get("overall_analytics", {}).get("weighted_coverage", 100) < 20:
            constrained *= 0.85
        missing_hard = len([e for e in det_report.get("errors", []) if "missing" in e.lower()])
        constrained -= missing_hard * 0.03

        constrained = max(lo, min(hi, constrained))
        raw_section_score = constrained * jd_weight  # contribution to final 100

        section_scores[section] = raw_section_score
        trace_note = f"label={label}({lo:.2f},{hi:.2f}), hybrid={hybrid:.3f}, verdict={verdict}"
        if correction_note:
            trace_note += f", {correction_note}"
        scoring_trace[section] = ScoringTraceEntry(
            score_awarded=round(raw_section_score, 4),
            weight=jd_weight,
            notes=trace_note
        )

    # Step 4: Guardrails AI — SimilarToPreviousValues across batch
    validated_scores, guardrails_fired = await apply_batch_score_guards(section_scores, jd_id)

    # Step 5: Build FinalResultScoringAgent
    final_score = round(sum(validated_scores.values()), 2)

    result = AgentResult(
        final_score=final_score,
        skills_score=round(validated_scores.get("skills", 0), 4),
        experience_score=round(validated_scores.get("experience", 0), 4),
        relevant_experience_score=round(validated_scores.get("relevant_experience", 0), 4),
        projects_score=0.0,
        certificates_score=round(validated_scores.get("certifications", 0), 4),
        tools_score=round(validated_scores.get("tools", 0), 4),
        technologies_score=round(validated_scores.get("technologies", 0), 4),
        qualification_score=round(validated_scores.get("qualification", 0), 4),
        responsibilities_score=round(validated_scores.get("responsibilities", 0), 4),
        salary_score=round(validated_scores.get("salary", 0), 4),
        position_score=round(validated_scores.get("position", 0), 4),
        notes="; ".join(notes_parts) or "Score adjustment complete.",
        scoring_trace=scoring_trace,
        guardrails_applied=guardrails_fired
    )

    final_output = FinalResultScoringAgent(
        current_state=AgentState.VERIFYING_OUTPUT.value,
        inputs={"resume": state["resume_parsed"], "jd": state["jd_normalized"],
                "weights": state["jd_weights"]},
        history=[h.dict() for h in state.get("agent_memory_history", [])],
        result=result,
        success=True,
        token_usage=state.get("token_usage_summary", {})
    )

    output_hash = hash_json(final_output.model_dump())
    return {
        **state,
        "match_output":   final_output.model_dump(),
        "final_score":    final_score,
        "output_hash":    output_hash,
        "agent_state":    AgentState.VERIFYING_OUTPUT.value
    }


def _find_section_evidence(rule_evidence: dict, section: str) -> dict | None:
    for ev in rule_evidence.get("section_evidences", []):
        if ev.get("section_name") == section:
            return ev
    return None
```

---

## 10. Redis Cache Strategy (Complete)

```python
CACHE_KEYS = {
    "ocr":              lambda file_hash:       f"ocr:{file_hash}",
    "parsed":           lambda content_hash:    f"parsed:{content_hash}",
    "embedding":        lambda chunk_hash:      f"emb:{chunk_hash}",
    "weights":          lambda content_hash:    f"weights:{content_hash}",
    "search":           lambda r, j, w, s:     f"search:{r}:{j}:{w}:{s}",
    "phi4":             lambda prompt_hash:     f"phi4:{prompt_hash}",
    "rag":              lambda r, j:           f"rag:{r}:{j}",
    "reason":           lambda r, j, w:        f"reason:{r}:{j}:{w}",
    "reason_context":   lambda output_hash:    f"reason_ctx:{output_hash}",
    "explanation":      lambda output_hash:    f"explain:{output_hash}",
    "score_history":    lambda jd_id, section: f"score_history:{jd_id}:{section}",  # NEW
    "batch":            lambda batch_id:       f"batch:{batch_id}:status",
}

CACHE_TTLS = {
    "ocr":             2592000,   # 30 days
    "parsed":           604800,   # 7 days
    "embedding":        604800,   # 7 days
    "weights":          172800,   # 48 hours
    "search":             3600,   # 1 hour
    "phi4":             86400,    # 24 hours
    "rag":               7200,    # 2 hours
    "reason":            7200,    # 2 hours
    "reason_context":    7200,    # 2 hours
    "explanation":       86400,   # 24 hours
    "score_history":     86400,   # 24 hours — rolling window per JD
    "batch":             3600,    # 1 hour
}
```

---

## 11. Database Schema (Complete SQL — Updated)

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL, org_code VARCHAR(50) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free', created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL, email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20), address TEXT, role VARCHAR(20) DEFAULT 'recruiter',
    hashed_password VARCHAR(255), oauth_provider VARCHAR(50), oauth_sub VARCHAR(255),
    phone_verified BOOLEAN DEFAULT FALSE, email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_org ON users(org_id);

-- OTP tokens
CREATE TABLE otp_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(10) NOT NULL, otp_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(50) NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job Descriptions
CREATE TABLE job_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    uploaded_by UUID REFERENCES users(id),
    file_name VARCHAR(500),
    file_hash VARCHAR(80) NOT NULL,
    content_hash VARCHAR(80) NOT NULL,
    -- jd_pdf_extraction_schema output (no raw_text)
    extracted_json JSONB,
    extraction_hash VARCHAR(80),
    ocr_confidence FLOAT,
    -- jd_weights_schema_format output (includes weight_generation_metadata)
    normalized_json JSONB,
    normalized_hash VARCHAR(80),
    weights_json JSONB,
    weights_hash_pre_hitl VARCHAR(80),
    weights_hash VARCHAR(80),
    hitl_verified BOOLEAN DEFAULT FALSE,
    hitl_verified_at TIMESTAMPTZ,
    hitl_verified_by UUID REFERENCES users(id),
    version INTEGER DEFAULT 1,
    status VARCHAR(30) DEFAULT 'uploaded',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_jd_org ON job_descriptions(org_id);
CREATE INDEX idx_jd_file_hash ON job_descriptions(file_hash);

-- Resumes — file_id PK, no raw_text, no candidate_name, no candidate_email, no org_id
CREATE TABLE resumes (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID,
    file_name VARCHAR(500),
    file_hash VARCHAR(80) NOT NULL,
    content_hash VARCHAR(80) NOT NULL,
    parsed_json JSONB,            -- resume_pdf_extraction_schema output
    extraction_hash VARCHAR(80),
    ocr_confidence FLOAT,
    status VARCHAR(30) DEFAULT 'uploaded',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_resume_file_hash ON resumes(file_hash);
CREATE INDEX idx_resume_batch ON resumes(batch_id);

-- Batches
CREATE TABLE batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    jd_id UUID REFERENCES job_descriptions(id),
    created_by UUID REFERENCES users(id),
    name VARCHAR(255),
    total_resumes INTEGER DEFAULT 0, completed INTEGER DEFAULT 0, failed INTEGER DEFAULT 0,
    status VARCHAR(30) DEFAULT 'queued',
    created_at TIMESTAMPTZ DEFAULT NOW(), completed_at TIMESTAMPTZ
);

-- Match Results — stores all 9 schema outputs
CREATE TABLE match_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID REFERENCES batches(id),
    resume_file_id UUID REFERENCES resumes(file_id),
    jd_id UUID REFERENCES job_descriptions(id),
    output_hash VARCHAR(80),
    -- final_result_scoring_agent_schema
    final_result_json JSONB,
    final_score FLOAT,
    -- deterministic_validator_output_schema
    deterministic_report JSONB,
    -- mathematical_validator_report_schema
    mathematical_report JSONB,
    -- rule_based_evidence_schema
    rule_based_evidence JSONB,
    -- final_validation_report_schema
    rag_final_verdict JSONB,
    -- reasoning engine outputs
    reasoning_labels JSONB,
    reasoning_context TEXT,
    reasoning_hash VARCHAR(80),
    -- LLM explanation
    llm_explanation TEXT,
    explanation_hash VARCHAR(80),
    -- Guardrails metadata
    guardrails_applied JSONB,
    -- Verdicts
    recommendation VARCHAR(30),
    is_valid BOOLEAN DEFAULT FALSE,
    hallucinations_detected BOOLEAN DEFAULT FALSE,
    is_confident BOOLEAN DEFAULT FALSE,
    math_accuracy FLOAT,
    mae FLOAT,
    -- Ranking
    rank INTEGER, percentile FLOAT,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_result_batch ON match_results(batch_id);
CREATE INDEX idx_result_score ON match_results(batch_id, final_score DESC);

-- Reasoning Log
CREATE TABLE reasoning_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID REFERENCES batches(id),
    resume_file_id UUID REFERENCES resumes(file_id),
    jd_id UUID REFERENCES job_descriptions(id),
    structural_facts JSONB,
    evidence_map JSONB,
    reasoning_labels JSONB,
    verification_report JSONB,
    reasoning_context TEXT,
    phases_completed INTEGER DEFAULT 5,
    corrections_applied INTEGER DEFAULT 0,
    cache_hit BOOLEAN DEFAULT FALSE,
    reasoning_hash VARCHAR(80),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hash Chain (append-only)
CREATE TABLE hash_chain_log (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(80), stage VARCHAR(80),
    artifact_type VARCHAR(80), artifact_id VARCHAR(255),
    content_hash VARCHAR(80), chain_hash VARCHAR(80) NOT NULL,
    previous_chain_hash VARCHAR(80), actor VARCHAR(20) DEFAULT 'system',
    metadata JSONB, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chain_session ON hash_chain_log(session_id);

-- Token Usage Log
CREATE TABLE token_usage_log (
    id BIGSERIAL PRIMARY KEY,
    batch_id UUID, resume_file_id UUID,
    model VARCHAR(100), prompt_tokens INTEGER,
    completion_tokens INTEGER, total_tokens INTEGER,
    est_cost_usd NUMERIC(10,6), pipeline_stage VARCHAR(80),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- pgvector tables (768-dim BGE-large-en-v1.5)
CREATE TABLE resume_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_file_id UUID REFERENCES resumes(file_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL, dimension VARCHAR(50) NOT NULL,
    chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
    chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON resume_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX idx_re_file_dim ON resume_embeddings(resume_file_id, dimension);

CREATE TABLE jd_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_id UUID REFERENCES job_descriptions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL, dimension VARCHAR(50) NOT NULL,
    chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
    chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON jd_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);

CREATE TABLE rag_evidence_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id VARCHAR(120) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    section_name VARCHAR(80) NOT NULL,
    chunk_text TEXT NOT NULL, embedding vector(768) NOT NULL,
    chunk_hash VARCHAR(80) NOT NULL, metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON rag_evidence_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
```

---

## 12. LangGraph Pipeline — Complete Graph (v7)

```python
# app/agents/agent_controller.py

def build_graph(sync_conn) -> CompiledGraph:
    checkpointer = PostgresSaver(sync_conn)
    checkpointer.setup()
    g = StateGraph(PipelineState)

    # Pipeline 1
    g.add_node("extract_resume",   extract_resume_node)
    g.add_node("validate_resume",  validate_resume_node)
    g.add_node("embed_resume",     embed_resume_node)   # uses RecursiveJsonSplitter
    # Pipeline 2
    g.add_node("extract_jd",       extract_jd_node)
    g.add_node("validate_jd",      validate_jd_node)
    g.add_node("jd_normalize",     jd_normalize_node)
    g.add_node("assign_weights",   assign_weights_node) # → jd_weights_schema_format
    g.add_node("hitl_pause",       hitl_pause_node)
    # Pipeline 3
    g.add_node("hybrid_search",    hybrid_search_node)
    g.add_node("reasoning_engine", reasoning_engine_node)
    g.add_node("rag_validation",   rag_validation_node) # deterministic uses hybrid internally
    g.add_node("score_adjustment", score_adjustment_node) # → final_result_scoring_agent_schema
    g.add_node("final_validation", final_validation_node)
    g.add_node("explanation_gen",  explanation_gen_node)
    g.add_node("report_generator", report_generator_node)
    g.add_node("error_handler",    error_handler_node)

    g.set_entry_point("extract_resume")

    # Linear edges
    g.add_edge("extract_resume",   "validate_resume")
    g.add_edge("embed_resume",     "hybrid_search")
    g.add_edge("jd_normalize",     "assign_weights")
    g.add_edge("reasoning_engine", "rag_validation")
    g.add_edge("score_adjustment", "final_validation")
    g.add_edge("explanation_gen",  "report_generator")
    g.add_edge("report_generator", END)
    g.add_edge("error_handler",    END)

    # Conditional edges
    g.add_conditional_edges("validate_resume", _route_validate_resume,
        {"embed_resume": "embed_resume", "error_handler": "error_handler"})
    g.add_conditional_edges("assign_weights", _route_weights,
        {"hitl_pause": "hitl_pause", "hybrid_search": "hybrid_search",
         "error_handler": "error_handler"})
    g.add_conditional_edges("hitl_pause", _route_hitl,
        {"hybrid_search": "hybrid_search", "error_handler": "error_handler"})
    g.add_conditional_edges("hybrid_search", _route_hybrid_search,
        {"reasoning_engine": "reasoning_engine", "error_handler": "error_handler"})
    g.add_conditional_edges("rag_validation", _route_rag,
        {"score_adjustment": "score_adjustment", "error_handler": "error_handler"})
    g.add_conditional_edges("final_validation", _route_final_validation,
        {"explanation_gen": "explanation_gen", "error_handler": "error_handler"})

    return g.compile(checkpointer=checkpointer, interrupt_before=["hitl_pause"])
```

---

## 13. Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://raiya:raiya_dev@localhost:5432/raiya
SYNC_DATABASE_URL=postgresql://raiya:raiya_dev@localhost:5432/raiya
REDIS_URL=redis://localhost:6379/0

AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>
AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY>
AZURE_OPENAI_DEPLOYMENT=mmresumeparser
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MODEL_NAME=phi4
 
 Nanonets_Docstrange_api_key: <YOUR_NANONETS_API_KEY> (github repo link: https://github.com/NanoNets/docstrange) (pip command: pip install docstrange)
JWT_SECRET_KEY=your_32_char_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
JWT_REFRESH_EXPIRE_DAYS=30

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<YOUR_LANGSMITH_API_KEY>
LANGCHAIN_PROJECT=raiya-pipeline-v7
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

EMBEDDING_MODEL_PRIMARY=BAAI/bge-large-en-v1.5
EMBEDDING_MODEL_RAG=sentence-transformers/all-MiniLM-L12-v2
EMBEDDING_DIMS_PRIMARY=768
EMBEDDING_DIMS_RAG=384

# RecursiveJsonSplitter
JSON_SPLITTER_RESUME_MAX_CHUNK=300
JSON_SPLITTER_JD_MAX_CHUNK=400
JSON_SPLITTER_EVD_MAX_CHUNK=500

# Hybrid search weights inside deterministic validator
DENSE_WEIGHT_IN_DETERMINISTIC=0.65
BM25_WEIGHT_IN_DETERMINISTIC=0.35
DETERMINISTIC_DENSE_THRESHOLD=0.65
DETERMINISTIC_RRF_K=60

# Guardrails SimilarToPreviousValues
GUARDRAILS_SCORE_STD_DEVS=2.0
GUARDRAILS_FINAL_SCORE_STD_DEVS=2.5

# Cache TTLs
CACHE_TTL_OCR=2592000
CACHE_TTL_EMBEDDING=604800
CACHE_TTL_WEIGHTS=172800
CACHE_TTL_SEARCH=3600
CACHE_TTL_PHI4=86400
CACHE_TTL_RAG=7200
CACHE_TTL_REASON=7200
CACHE_TTL_EXPLANATION=86400
CACHE_TTL_SCORE_HISTORY=86400

PROMPT_COST_PER_1K=0.00030
COMPLETION_COST_PER_1K=0.00060
RAG_MATH_ACCURACY_MIN=80.0
REASONING_PHASE1_TEMP=0.0
REASONING_PHASE3_TEMP=0.1
REASONING_PHASE5_TEMP=0.0

APP_ENV=development
CORS_ORIGINS=["http://localhost:3000","https://app.raiya.ai"]
MAX_BATCH_SIZE=200
```

---

## 14. Complete File Generation Order (v7.0)

```
PHASE A — Core Infrastructure
  1.  app/core/config.py
  2.  app/core/logging_config.py
  3.  app/core/hashing.py
  4.  app/core/security.py
  5.  app/db/database.py
  6.  app/db/redis_client.py             (includes score_history cache key)
  7.  app/db/pgvector_client.py

PHASE B — ORM Models
  8.  app/models/__init__.py
  9.  app/models/user.py
  10. app/models/document.py             (file_id PK, no raw_text)
  11. app/models/batch.py                (MatchResult includes all 9 schema JSONBs)
  12. app/models/audit.py

PHASE C — Pydantic Schemas (all 9 canonical + reasoning)
  13. app/schemas/__init__.py
  14. app/schemas/auth.py
  15. app/schemas/resume.py              (resume_pdf_extraction_schema.json)
  16. app/schemas/jd.py                  (jd_pdf_extraction_schema.json)
  17. app/schemas/jd_weights.py          (jd_weights_schema_format.json + WeightingMetadata)
  18. app/schemas/extracted_rules.py     (extracted_rules_schema.json)
  19. app/schemas/deterministic_output.py (deterministic_validator_output_schema.json)
  20. app/schemas/mathematical_report.py  (mathematical_validator_report_schema.json)
  21. app/schemas/rule_based_evidence.py  (rule_based_evidence_schema.json)
  22. app/schemas/final_result.py         (final_result_scoring_agent_schema.json)
  23. app/schemas/reasoning.py
  24. app/schemas/batch.py
  25. app/schemas/admin.py

PHASE D — Agent Infrastructure
  26. app/agents/agent_state.py
  27. app/agents/agent_authority.py
  28. app/agents/agent_guardrails.py      (+ validate_reasoning_inputs())

PHASE E — Guardrails Config (NEW — before reasoning to avoid circular imports)
  29. app/guardrails_config/__init__.py
  30. app/guardrails_config/score_guards.py      (SimilarToPreviousValues + ValidRange)
  31. app/guardrails_config/explanation_guards.py (DetectPII + ToxicLanguage)
  32. app/guardrails_config/weight_guards.py     (weight ValidRange + sum check)

PHASE F — Chunking Module (NEW)
  33. app/chunking/__init__.py
  34. app/chunking/json_splitter.py       (RecursiveJsonSplitter base wrapper)
  35. app/chunking/resume_chunker.py      (section-aware resume JSON chunking)
  36. app/chunking/jd_chunker.py          (criteria-aware JD JSON chunking)
  37. app/chunking/evidence_chunker.py    (EVD JSON chunking for pgvector)

PHASE G — Reasoning Module
  38. app/reasoning/__init__.py
  39. app/reasoning/reasoning_schemas.py
  40. app/reasoning/reasoning_cache.py
  41. app/reasoning/structural_analyzer.py
  42. app/reasoning/evidence_classifier.py
  43. app/reasoning/label_assigner.py
  44. app/reasoning/cross_verifier.py
  45. app/reasoning/context_synthesizer.py
  46. app/reasoning/reasoning_engine_core.py

PHASE H — RAG Evidence Layer
  47. app/RAG_Validation_layer/__init__.py
  48. app/RAG_Validation_layer/normalizer_pre_score.py
  49. app/RAG_Validation_layer/jd_normalizer.py
  50. app/RAG_Validation_layer/rule_extractor.py           (→ extracted_rules_schema)
  51. app/RAG_Validation_layer/deterministic_validator.py  (hybrid search BGE+BM25 inside)
  52. app/RAG_Validation_layer/mathematical_validator.py   (→ mathematical_validator_report)
  53. app/RAG_Validation_layer/evidence_rule_engine.py
  54. app/RAG_Validation_layer/rule_based_evidence.py      (→ rule_based_evidence_schema)
  55. app/RAG_Validation_layer/evidence_generation.py
  56. app/RAG_Validation_layer/final_report.py             (→ final_validation_report)
  57. app/RAG_Validation_layer/pipeline.py
  58. app/RAG_Validation_layer/evidence_rules.json

PHASE I — Agent Tools
  59. app/agents/tools/__init__.py
  60. app/agents/tools/ocr_tool.py        (Nanonets + Redis cache)
  61. app/agents/tools/embed_tool.py      (BGE + chunk_hash Redis cache)
  62. app/agents/tools/search_tool.py     (hybrid per section + RRF; uses chunking)
  63. app/agents/tools/llm_tool.py        (Azure Phi-4 + prompt cache + token monitor)

PHASE J — Pipeline 1 Nodes
  64. app/agents/nodes/__init__.py
  65. app/agents/nodes/pipeline1/__init__.py
  66. app/agents/nodes/pipeline1/extract_resume.py   (→ resume_pdf_extraction_schema)
  67. app/agents/nodes/pipeline1/validate_resume.py
  68. app/agents/nodes/pipeline1/embed_resume.py     (uses resume_chunker + RecursiveJsonSplitter)

PHASE K — Pipeline 2 Nodes
  69. app/agents/nodes/pipeline2/__init__.py
  70. app/agents/nodes/pipeline2/extract_jd.py       (→ jd_pdf_extraction_schema)
  71. app/agents/nodes/pipeline2/validate_jd.py
  72. app/agents/nodes/pipeline2/jd_normalize.py
  73. app/agents/nodes/pipeline2/assign_weights.py   (→ jd_weights_schema_format)
  74. app/agents/nodes/pipeline2/hitl_pause.py

PHASE L — Pipeline 3 Nodes
  75. app/agents/nodes/pipeline3/__init__.py
  76. app/agents/nodes/pipeline3/hybrid_search.py    (SECTION_SEARCH_CONFIG + RRF + cache)
  77. app/agents/nodes/pipeline3/reasoning_engine.py (5-phase + reasoning_context)
  78. app/agents/nodes/pipeline3/rag_validation.py   (8-step; deterministic uses hybrid)
  79. app/agents/nodes/pipeline3/score_adjustment.py (→ final_result_scoring_agent_schema)
  80. app/agents/nodes/pipeline3/final_validation.py
  81. app/agents/nodes/pipeline3/explanation_gen.py
  82. app/agents/nodes/pipeline3/report_generator.py

PHASE M — LangGraph Controller
  83. app/agents/agent_controller.py

PHASE N — Services
  84. app/services/token_usage_monitor.py
  85. app/services/auth_service.py
  86. app/services/jd_service.py
  87. app/services/batch_service.py
  88. app/services/admin_service.py

PHASE O — API Routes
  89. app/api/v1/routes/__init__.py
  90. app/api/v1/routes/auth.py
  91. app/api/v1/routes/jd.py
  92. app/api/v1/routes/batch.py
  93. app/api/v1/routes/admin.py
  94. app/api/v1/router.py
  95. app/main.py

PHASE P — Prompts
  96.  prompts/v2/jd_weight_assignment/system_prompt.txt
  97.  prompts/v2/react_based_scoring/system_prompt.txt      (Updated ReAct with RAG evidence)
  98.  prompts/v2/final_output_explainer/system_prompt.txt
  99.  prompts/v2/reasoning_engine/phase1_structural.txt
  100. prompts/v2/reasoning_engine/phase3_labels.txt
  101. prompts/v2/reasoning_engine/phase5_context.txt

PHASE Q — Database Migrations
  102. alembic.ini
  103. migrations/env.py
  104. migrations/versions/001_initial_schema.py

PHASE R — Tests
  105. tests/conftest.py
  106. tests/unit/test_hashing.py
  107. tests/unit/test_json_splitter.py          (RecursiveJsonSplitter chunk count/size)
  108. tests/unit/test_resume_chunker.py         (section tags preserved)
  109. tests/unit/test_jd_chunker.py             (criteria stay together)
  110. tests/unit/test_deterministic_hybrid.py   (BGE+BM25 match quality)
  111. tests/unit/test_guardrails_similar.py     (SimilarToPreviousValues drift detection)
  112. tests/unit/test_rule_extractor.py
  113. tests/unit/test_mathematical_validator.py
  114. tests/unit/test_reasoning_engine.py
  115. tests/unit/test_reasoning_cross_verify.py
  116. tests/unit/test_agent_authority.py
  117. tests/unit/test_agent_guardrails.py
  118. tests/unit/test_evidence_rule_engine.py
  119. tests/unit/test_token_monitor.py
  120. tests/integration/test_pipeline1_resume.py
  121. tests/integration/test_pipeline2_jd.py
  122. tests/integration/test_pipeline3_scoring.py
  123. tests/integration/test_reasoning_pipeline.py
  124. tests/integration/test_rag_validation_layer.py
  125. tests/integration/test_hitl_flow.py
  126. tests/integration/test_full_batch.py
  127. tests/eval/test_deepeval_suite.py

PHASE S — Infrastructure
  128. docker/Dockerfile
  129. docker/Dockerfile.test
  130. docker/wait-for-postgres.sh
  131. docker-compose.yml
  132. docker-compose.test.yml
  133. requirements.txt
  134. requirements-dev.txt
  135. .env.example
  136. storage/.gitkeep
  137. README.md
```

---

## 15. Full Pipeline Flow Reference

```
POST /api/v1/batch/create
│
├── Pipeline 2 (JD — once per job):
│   extract_jd → (jd_pdf_extraction_schema) → validate_jd →
│   jd_normalize → assign_weights → (jd_weights_schema_format) →
│   [HITL_WAIT interrupt] → embed_jd_chunks (jd_chunker + RecursiveJsonSplitter)
│
└── Pipeline 1+3 per resume (parallel workers):
    │
    ├── Pipeline 1:
    │   extract_resume → (resume_pdf_extraction_schema) → validate_resume →
    │   embed_resume (resume_chunker + RecursiveJsonSplitter → BGE → pgvector)
    │
    └── Pipeline 3:
        │
        ├── hybrid_search_node
        │   Output: section_similarities {section: {dense,bm25,exact,hybrid,weight}}
        │   Cache: search:{r}:{j}:{w}:{section} TTL=1h
        │
        ├── reasoning_engine_node (5 phases, labels only)
        │   Phase 1: structural_facts (LLM, temp=0.0)
        │   Phase 2: evidence_map [EXPLICIT|PARTIAL|ABSENT] (Python)
        │   Phase 3: reasoning_labels LabelSet (LLM ReAct, temp=0.1)
        │   Phase 4: verified_labels + verification_report (Python)
        │   Phase 5: reasoning_context narrative (LLM, temp=0.0)
        │   Cache: reason:{r}:{j}:{w} TTL=2h
        │
        ├── rag_validation_node (8 steps)
        │   Step 2: jd_normalize
        │   Step 3: DeterministicValidator
        │           → hybrid search BGE+BM25 per section (NEW)
        │           → output: deterministic_validator_output_schema
        │   Step 4: MathematicalValidator
        │           → output: mathematical_validator_report_schema
        │   Step 5: RuleBasedEvidence (14 detectors)
        │           → output: rule_based_evidence_schema
        │   Step 6: FinalReport
        │           → output: final_validation_report_schema
        │   Step 7: EVD_{ts}_{uuid}.json
        │   Step 8: evidence_chunker + RecursiveJsonSplitter → pgvector upsert
        │
        ├── score_adjustment_node
        │   Reads: reasoning_labels (label constraints per section)
        │          deterministic_report (coverage + matched items)
        │          mathematical_report (ground_truth vs ai_score per section)
        │          rule_based_evidence (ACCURATE/OVER/UNDER verdict per section)
        │   ReAct: THOUGHT→ACTION→OBSERVATION→SCORE per section
        │          RAG evidence is the mandatory context
        │   Guardrails: SimilarToPreviousValues per section score
        │   Output: final_result_scoring_agent_schema
        │
        ├── final_validation_node
        │   Guardrails: ValidRange(0,100) + DetectPII + ToxicLanguage
        │   Authority: authorize_score() + authorize_transition()
        │
        ├── explanation_gen_node
        │   Reads: reasoning_context (Phase 5 primary grounding)
        │   Output: 6-section audit explanation (no inference)
        │
        └── report_generator_node
            Batch ranking + ReportLab PDF + report_hash + DB write

WebSocket: ocr|embed|normalize|weight|search|reason_p1..p5|rag_step1..8|adjust|explain|report
```

---

## 16. Requirements.txt (Key Packages)
pip install guardrails-ai
```txt
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic[email]>=2.7.0
pydantic-settings>=2.3.0

# LangGraph + LangChain
langgraph>=0.2.0
langchain>=0.2.0
langchain-text-splitters>=0.2.0    # RecursiveJsonSplitter
langchain-community>=0.2.0
langchain-huggingface>=0.0.3
langsmith>=0.1.0

# Database
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
psycopg[binary]>=3.1.0             # for LangGraph PostgresSaver
alembic>=1.13.0
pgvector>=0.2.5

# Cache
redis[hiredis]>=5.0.3
diskcache>=5.6.3

# Embeddings
sentence-transformers>=3.0.0
rank-bm25>=0.2.2

# Azure Phi-4
azure-ai-inference>=1.0.0b3
azure-core>=1.30.0

# Guardrails AI
guardrails-ai>=0.5.0
# Hub validators (install separately):
# guardrails hub install hub://guardrails/similar_to_previous_values
# guardrails hub install hub://guardrails/valid_range
# guardrails hub install hub://guardrails/detect_pii
# guardrails hub install hub://guardrails/toxic_language

# OCR
httpx>=0.27.0                       # Nanonets async calls

# PDF
reportlab>=4.2.0

# Auth
authlib>=1.3.0
python-jose[cryptography]>=3.3.0
bcrypt>=4.1.0
twilio>=9.0.0
sendgrid>=6.11.0

# Validation
jsonschema>=4.21.0

# DeepEval (dev)
deepeval>=1.0.0

# Utils
python-dotenv>=1.0.1
numpy>=1.26.0
```