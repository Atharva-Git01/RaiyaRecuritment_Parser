# RAG Validation Layer Pipeline

The RAG Validation Layer Pipeline is an automated system designed to evaluate, normalize, and validate AI-generated resume scores against structured Job Descriptions (JDs). It employs a multi-layered approach combining deterministic, mathematical, and semantic checks to ensure AI scoring accuracy, prevent hallucinations, and provide ground-truth evaluation metrics.

---

## 📁 Complete Directory Structure

```
RAG_Validation_layer/
│
├── main.py                          # CLI entry point — orchestrates the full pipeline
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (API keys — gitignored)
├── .env.example                     # Template for required environment variables
├── .env_pinecone                    # Pinecone-specific credentials
├── PIPELINE_WORKFLOW.md             # Visual pipeline architecture (Mermaid diagrams)
├── README.md                        # This file
│
├── src/                             # Main application source code
│   ├── config.py                    # Centralized settings (paths, API keys, model names)
│   ├── logging_config.py            # Standardized logging setup
│   │
│   ├── core/
│   │   └── pipeline.py              # 8-step pipeline orchestrator
│   │
│   ├── processing/
│   │   ├── jd_normalizer.py         # JD token normalization via canonical alias maps
│   │   ├── normalizer_pre_score.py  # Resume skill/education alias definitions
│   │   ├── evidence_generation.py   # Historical evidence document builder
│   │   ├── rule_based_evidence_generation.py  # Dynamic rule engine (14 detectors)
│   │   └── final_report.py          # Consolidated PASS/FAIL verdict generator
│   │
│   ├── validators/
│   │   ├── jd_validator.py          # JD schema validation & weight balancing
│   │   ├── deterministic.py         # Semantic matching via sentence-transformers
│   │   └── mathematical.py          # Ground-truth score calculator (MAE/RMSE)
│   │
│   └── retrieval/
│       ├── database.py              # Pinecone vector DB chunking & upsert
│       └── engine.py                # RAG & Corrective RAG (CRAG) query engine
│
└── data/
    ├── inputs/                      # Raw input files
    │   ├── job_description.json     # Source JD with scoring criteria
    │   ├── score_my_resume_*.json   # AI scorer output (resume + scores)
    │   ├── extracted_rules.json     # Pre-extracted validation rules
    │   ├── rule_based_schema.json   # Schema definition for rules
    │   └── validated_jd.json        # Cached normalized JD
    │
    ├── outputs/                     # Pipeline-generated reports
    │   ├── validated_jd.json        # Normalized & weight-balanced JD
    │   ├── deterministic_validator_output.json  # Semantic match report
    │   ├── mathematical_validator_report.json   # Ground-truth accuracy report
    │   ├── rule_based_evidence.json             # Dynamic rule evaluation results
    │   ├── evidence_rules.json                  # Generated rules (JSON)
    │   ├── extracted_rules.json                 # Rule extraction output
    │   └── final_validation_report.json         # Consolidated PASS/FAIL verdict
    │
    └── historical/                  # Versioned evidence files for vector indexing
        └── EVD_*.json               # Timestamped evidence documents
```

---

## 🏗️ Pipeline Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        main.py (CLI Entry)                         │
│   Parses --jd and --ai args → delegates to pipeline.py            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   src/core/pipeline.py (Orchestrator)               │
│                                                                     │
│  Step 1 ─► Load Inputs (JD + AI Score JSON)                        │
│  Step 2 ─► Normalize & Validate JD       → validated_jd.json       │
│  Step 3 ─► Deterministic Semantic Check   → deterministic_*.json   │
│  Step 4 ─► Mathematical Accuracy Check    → mathematical_*.json    │
│  Step 5 ─► Rule-Based Evidence Generation → rule_based_evidence.*  │
│  Step 6 ─► Final Consolidated Report      → final_validation_*.json│
│  Step 7 ─► Historical Evidence Generation → EVD_*.json             │
│  Step 8 ─► Pinecone Database Update       → Vector DB upsert       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📄 Detailed File-by-File Workflow

---

### Root Files

#### `main.py` — CLI Entry Point

- **What**: Unified command-line interface for the entire pipeline.
- **Why**: Provides a single command to run all 8 validation steps end-to-end.
- **How**: Uses `argparse` to accept optional `--jd` and `--ai` paths. Defaults come from `src/config.py`. Calls `run_pipeline()` from `src/core/pipeline.py`.
- **When**: Run this to execute the full validation pipeline.
- **Where**: Invoked from terminal: `python main.py [--jd path] [--ai path]`

#### `requirements.txt` — Dependencies

- **What**: Lists all Python package dependencies.
- **Key packages**: `langchain` ecosystem (core, openai, pinecone, huggingface), `sentence-transformers`, `pinecone-client`, `openai`, `pydantic`, `pydantic-settings`, `python-dotenv`.

#### `.env.example` — Environment Template

- **What**: Template showing required environment variables.
- **Variables**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY`.

---

### `src/config.py` — Centralized Configuration

- **What**: Single source of truth for all paths, API keys, and model settings.
- **Why**: Eliminates hardcoded paths across modules; all modules import `settings`.
- **How**: Uses `pydantic-settings.BaseSettings` to load from `.env` file and environment variables. Defines `BASE_DIR`, `DATA_DIR`, `INPUT_DIR`, `OUTPUT_DIR`, `HISTORICAL_DIR`, all default input/output file paths, Pinecone index name (`rag-validation-index`), and embedding model (`all-MiniLM-L12-v2`).
- **When**: Auto-loaded at import time. Every module imports `from src.config import settings`.

### `src/logging_config.py` — Logging Setup

- **What**: Standardized logging configuration for all modules.
- **Why**: Consistent `[timestamp] LEVEL in module: message` format across the pipeline.
- **How**: Creates a `rag_validation` logger with `StreamHandler` to stdout. Format: `[%Y-%m-%d %H:%M:%S] %(levelname)s in %(module)s: %(message)s`.
- **When**: Imported as `from src.logging_config import logger` by every module.

---

### `src/core/` — Core Orchestration

#### `src/core/pipeline.py` — Pipeline Orchestrator

- **What**: Central coordinator that manages the 8-step validation flow.
- **Why**: Ensures correct execution order and data handoff between modules.
- **How**: Defines 8 step functions (`step1_load_inputs` through `step8_database_update`), each lazily importing its module to avoid circular dependencies. The `run_pipeline()` function chains them:
  1. **Step 1** — Load raw JD and AI scorer JSON files; validate they exist.
  2. **Step 2** — Call `validate_jd()` from `jd_validator.py`; save `validated_jd.json`.
  3. **Step 3** — Instantiate `DeterministicValidator` with the validated JD; run `.validate(ai_score)`; save `deterministic_validator_output.json`.
  4. **Step 4** — Instantiate `MathematicalValidator` with JD, AI score, and deterministic report; calculate ground truth; save `mathematical_validator_report.json`.
  5. **Step 5** — Call `generate_rule_based_evidence()` with JD and AI score; save `rule_based_evidence.json`.
  6. **Step 6** — Call `generate_final_report()` which reads deterministic + math reports and outputs `final_validation_report.json`.
  7. **Step 7** — Call `generate_historical_evidence()` which compiles all outputs into a versioned `EVD_*.json` file in `data/historical/`.
  8. **Step 8** — Call `run_database_update()` which chunks the latest evidence and upserts embeddings to Pinecone.
- **When**: Called by `main.py` or directly via `from src.core.pipeline import run_pipeline`.
- **Where**: Outputs are saved to `data/outputs/` and `data/historical/`.

---

### `src/processing/` — Normalization & Processing

#### `src/processing/normalizer_pre_score.py` — Alias Dictionaries

- **What**: Defines three canonical alias dictionaries: `tech_aliases` (60+ technology mappings), `skill_aliases` (18 conceptual skill mappings), and `edu_aliases` (7 education degree mappings).
- **Why**: Ensures vocabulary consistency between JD and resume before scoring. E.g., `"react"`, `"react.js"`, `"react native"` all map to `"ReactJS"`.
- **How**: Each dictionary maps lowercase variant strings to a canonical form. The `normalize_for_scoring()` function processes a parsed resume dict: normalizes skills using `tech_aliases + skill_aliases`, normalizes education degrees using `edu_aliases`, and includes fuzzy matching via `SequenceMatcher` (threshold 0.8) as a fallback.
- **When**: Called during resume pre-processing before JD-vs-resume comparison. Also imported by `jd_normalizer.py` for JD-side normalization.

#### `src/processing/jd_normalizer.py` — JD Token Normalizer

- **What**: Normalizes all JD fields using the canonical alias maps from `normalizer_pre_score.py`.
- **Why**: Raw JDs contain inconsistent naming (e.g., `"react"` vs `"ReactJS"`). Normalization ensures apples-to-apples comparison with resume tokens.
- **How**: The `normalize_jd()` master function processes the JD dict:
  - **List fields** (`technologies`, `skills`, `tools`, `projects`, `certificates`) → each item is alias-matched using word-boundary regex (`\b...\b`) to prevent false positives (e.g., `"be"` in `"cyber"`).
  - **Sentence fields** (`responsibilities`) → whitespace-cleaned only, no alias mapping.
  - **String fields** (`experience`, `qualification`, `position`, etc.) → whitespace normalized.
  - **Scoring block** → each section validated for `weight` + `criteria` structure.
  - **Experience range** → extracted via regex from the experience string (e.g., `"3-8 years"` → `{"min": 3.0, "max": 8.0}`).
  - Canonical values (e.g., `"HTML5"`, `"VS Code"`) are fast-path preserved to prevent incorrect title-casing.
- **When**: Called as the first step inside `jd_validator.validate_jd()`.

#### `src/processing/evidence_generation.py` — Historical Evidence Builder

- **What**: Compiles all validation outputs into a unified, versioned evidence document for historical indexing.
- **Why**: Creates a searchable record of each validation session that can be embedded and stored in Pinecone for future RAG queries.
- **How**: The `generate_historical_evidence()` function:
  1. Loads `validated_jd.json`, `deterministic_validator_output.json`, `mathematical_validator_report.json`, and `final_validation_report.json`.
  2. Builds a `text_blob` — a flat searchable string containing job title, qualifications, experience, skills, tools, technologies, semantic match pairs, ground truth scores, and final notes.
  3. Extracts a sorted `keywords` list from skills, tools, and technologies.
  4. Compiles a `summary` dict with deterministic validity, coverage, token overlap, math accuracy, MAE, RMSE, and final verdict.
  5. Packages everything with `raw_sources` (full validator outputs) and saves as `EVD_{timestamp}_{uuid}.json` in `data/historical/`.
- **When**: Step 7 of the pipeline, after the final report is generated.
- **Where**: Output saved to `data/historical/EVD_*.json`.

#### `src/processing/rule_based_evidence_generation.py` — Dynamic Rule Engine

- **What**: The largest module (798 lines). Dynamically analyzes JD and resume to generate validation rules, applies them to adjust scores, and produces per-section evidence.
- **Why**: Static rules can't cover all edge cases. This module detects issues like internship bias, job hopping, salary mismatches, and AI over-estimation that a simple keyword match would miss.
- **How**: Three-phase process:

  **Phase 1 — Base Evaluation**: For each scoring section, computes ground-truth coverage:
  - Keyword sections (`skills`, `technologies`, `tools`, `projects`, `certificates`, `responsibilities`) → exact + regex keyword matching against resume items.
  - Bracket sections (`experience`, `relevant_experience`) → maps total years to JD-defined brackets.
  - Special sections (`salary`, `qualification`, `position`) → custom evaluators with bracket/degree/role matching.

  **Phase 2 — Dynamic Rule Generation** (`_generate_dynamic_rules`): Runs 14 detectors:
  | # | Detector | Triggers When |
  |---|----------|---------------|
  | 1 | Internship Bias | ≥50% of experience entries are intern/trainee roles |
  | 2 | Missing Summary | Professional summary is empty or <10 chars |
  | 3 | Job Hopping | Average job tenure < 7 months |
  | 4 | AI Over-estimation | AI section score exceeds keyword match by >40 points |
  | 5 | Experience Below Minimum | Total years < JD minimum requirement |
  | 6 | Qualification Gap | JD requires Master's but candidate doesn't have one |
  | 7 | Low Skill Coverage | <25% of JD skills matched in resume |
  | 8 | Zero-Weight Non-Zero Score | AI scores >0 on a section with weight=0 |
  | 9 | Salary Mismatch | AI salary score exceeds bracket coverage by >30 |
  | 10 | Missing Certifications | JD requires certs (weight>0) but resume has none |
  | 11 | Missing Projects | JD values projects (weight>0) but resume has none |
  | 12 | Low Tool Coverage | <20% of JD tools matched |
  | 13 | Position Level Mismatch | JD wants lead/senior but candidate is junior/intern |
  | 14 | Single Employer Bias | Only 1 employer with <2 years total experience |

  Each rule specifies a `condition` and an `action` (`cap`, `multiply`, `subtract`, `add`, `override`).

  **Phase 3 — Rule Application**: Applies each generated rule to adjust base coverage scores. Produces per-section evidence with AI score vs ground truth comparison, delta, and verdict (`ACCURATE`, `OVERESTIMATED`, `UNDERESTIMATED`). Tolerance: ±10 points.

- **When**: Step 5 of the pipeline. Also saves generated rules to `data/outputs/evidence_rules.json`.
- **Where**: Output saved to `data/outputs/rule_based_evidence.json`.

#### `src/processing/final_report.py` — Consolidated Verdict Generator

- **What**: Aggregates results from deterministic and mathematical validators into a single PASS/FAIL verdict.
- **Why**: Provides a clear, actionable final answer: did the AI scorer's output pass validation?
- **How**: The `generate_final_report()` function:
  1. Loads `deterministic_validator_output.json` → checks `is_valid`.
  2. Loads `mathematical_validator_report.json` → checks `global_metrics.is_valid`.
  3. `final_verdict = det_valid AND math_valid`.
  4. If failed, generates detailed `notes` explaining which validator failed and why (including per-section hallucination errors and accuracy percentages).
  5. Outputs `component_verdicts` and `metrics_summary` (accuracy, MAE).
- **When**: Step 6 of the pipeline, after both validators have run.
- **Where**: Output saved to `data/outputs/final_validation_report.json`.

---

### `src/validators/` — Validation Layer

#### `src/validators/jd_validator.py` — JD Schema Validator

- **What**: Master JD validation function that produces a fully normalized and weight-balanced JD dict.
- **Why**: Raw JDs may have missing sections, inconsistent weights, or unscaled criteria. This ensures the JD is pipeline-ready.
- **How**: The `validate_jd()` function performs 4 steps:
  1. **Normalize** — calls `normalize_jd()` from `jd_normalizer.py` (alias maps, string cleaning, experience range extraction).
  2. **Validate scoring structure** — ensures all 11 required scoring fields exist (`skills`, `experience`, `relevant_experience`, `projects`, `certificates`, `tools`, `technologies`, `qualification`, `responsibilities`, `salary`, `position`). Missing sections get zero-weight blocks. Extra sections are preserved.
  3. **Scale criteria** — scales all numeric criteria values within each section so the maximum equals 100.
  4. **Normalize weights** — ensures total weight sums to ~100. If all weights are 0, applies default distribution (e.g., `relevant_experience: 30`, `technologies: 20`, `salary: 15`). Otherwise normalizes proportionally.
- **When**: Step 2 of the pipeline. Can also run standalone: `python -m src.validators.jd_validator`.
- **Where**: Output saved to `data/outputs/validated_jd.json`.

#### `src/validators/deterministic.py` — Semantic Matching Validator

- **What**: Compares JD criteria keywords against resume content using `sentence-transformers` (`all-MiniLM-L12-v2`) embeddings.
- **Why**: Simple string matching misses semantic equivalences (e.g., `"React"` ↔ `"ReactJS"`, `"REST API"` ↔ `"API Development"`). Embedding-based cosine similarity catches these.
- **How**:
  - **Model**: Lazy-loads `all-MiniLM-L12-v2` as a singleton. Uses pure-Python cosine similarity (avoids NumPy/torch ABI issues).
  - **Per-section analysis**: For each scoring section (skipping numeric-only sections like `experience`, `salary`, `position`):
    1. Extracts JD keywords from `validated_jd["scoring"][section]["criteria"]`.
    2. Extracts resume items from the AI scorer's `inputs.resume` (maps sections to relevant resume fields via `SECTION_FIELD_MAP`).
    3. Encodes both sets, computes pairwise cosine similarity.
    4. Matches at threshold ≥ 0.9. Reports `matched_skills`, `weighted_coverage` (0-100%), and `token_overlap` (0-1).
  - **Hallucination check**: Verifies that all matched JD items actually exist in the JD criteria set.
  - **Overall analytics**: Aggregates all sections for a combined resume-level coverage metric.
- **When**: Step 3 of the pipeline. Can also run standalone: `python -m src.validators.deterministic`.
- **Where**: Output saved to `data/outputs/deterministic_validator_output.json`.

#### `src/validators/mathematical.py` — Ground Truth Calculator

- **What**: Independently recalculates scores from scratch and compares them against the AI scorer's output.
- **Why**: Detects numerical inaccuracies in the AI's scoring by establishing an independent "ground truth".
- **How**: The `MathematicalValidator.calculate_ground_truth()` method:
  - **Keyword sections** (`skills`, `technologies`, `tools`, etc.) → uses `weighted_coverage` from the deterministic report as ground truth.
  - **Bracket sections** (`experience`, `relevant_experience`) → maps candidate's total years to JD-defined score brackets.
  - **Salary** → converts to LPA, maps to bracket score.
  - **Qualification** → checks degrees against criteria (Master's > Bachelor's > Other).
  - **Position** → checks if lead/manager vs individual contributor.
  - **Error metrics**: Computes MAE (Mean Absolute Error) and RMSE (Root Mean Square Error) across all sections.
  - **Validity threshold**: `accuracy >= 80%` where `accuracy = 100 - |AI_final - GT_final|`.
- **When**: Step 4 of the pipeline. Requires deterministic report from Step 3.
- **Where**: Output saved to `data/outputs/mathematical_validator_report.json`.

---

### `src/retrieval/` — Retrieval Layer (RAG)

#### `src/retrieval/database.py` — Vector Database Manager

- **What**: Chunks evidence documents, generates embeddings, and upserts them to Pinecone.
- **Why**: Enables semantic search over historical validation sessions for future queries.
- **How**:
  - **Chunking strategy**: Section-based chunking (not naive text splitting):
    - **Rule-based evidence** → one chunk per scoring section + overall summary chunk. Each chunk includes header (job title, ID, timestamp), section metrics (AI score, ground truth, delta, coverage), criteria evaluation details, and verdict.
    - **Historical evidence** → one chunk per section from deterministic results + summary chunk with math accuracy, coverage, and final verdict.
  - **Metadata**: Each chunk carries `job_id`, `job_title`, `timestamp`, `source_type`, `section_name`, and source-specific metrics.
  - **Index management**: Auto-creates Pinecone index (`rag-validation-index`) with cosine metric on AWS us-east-1 if it doesn't exist.
  - **Embedding**: Uses `HuggingFaceEmbeddings` with `all-MiniLM-L12-v2` (384 dimensions).
  - **Upsert**: Uses `PineconeVectorStore.from_texts()` via LangChain with chunk IDs formatted as `{evidence_id}#{section_name}`.
- **When**: Step 8 of the pipeline (final step). Can also run standalone: `python -m src.retrieval.database`.

#### `src/retrieval/engine.py` — RAG & Corrective RAG Engine

- **What**: The query interface (680 lines). Retrieves relevant evidence from Pinecone and generates LLM-powered answers via Azure OpenAI.
- **Why**: Allows users to ask natural-language questions about validation results, grounded in historical evidence.
- **How**: Two retrieval modes:

  **Standard RAG** (`retrieve_evidence()`):
  1. Embed query using `all-MiniLM-L12-v2`.
  2. Retrieve top-K chunks from Pinecone via `similarity_search_with_score()`.
  3. Build a RAG prompt with retrieved chunks as grounded context.
  4. Call Azure OpenAI via LangChain `ChatPromptTemplate` chain.
  5. Return query, matches, prompt, and LLM response.

  **Corrective RAG / CRAG** (`corrective_retrieve_evidence()`):
  1. **Retrieve** — Same as standard RAG (top-K from Pinecone).
  2. **Grade** — Each chunk is individually graded for relevance by the LLM using a structured `GradeResponse` schema (relevant: bool, confidence: float, reasoning: str) via `JsonOutputParser`.
  3. **Classify** — Overall retrieval quality is classified:
     - `CORRECT` (≥50% relevant) → strict grounding on evidence.
     - `AMBIGUOUS` (>0% but <50%) → evidence as supplement.
     - `INCORRECT` (0% relevant) → LLM uses own knowledge with caveats.
  4. **Refine** — Keep only relevant chunks.
  5. **Generate** — Classification-aware prompt adapts the system instruction based on evidence quality.

- **When**: After the pipeline has run and evidence is indexed. Used for querying.
- **Where**: CLI usage:
  ```bash
  python -m src.retrieval.engine --query "..." --mode corrective
  python -m src.retrieval.engine --query "..." --mode standard --top-k 5
  ```

---

### `data/` — Data Storage

#### `data/inputs/`
| File | Purpose |
|------|---------|
| `job_description.json` | Raw JD with scoring criteria, weights, and technology/skill lists |
| `score_my_resume_*.json` | AI scorer output containing `inputs.resume` and `result` with per-section scores |
| `extracted_rules.json` | Pre-extracted validation rules |
| `rule_based_schema.json` | Schema definition for rules |

#### `data/outputs/`
| File | Generated By | Contains |
|------|-------------|----------|
| `validated_jd.json` | `jd_validator.py` | Normalized JD with balanced weights and scaled criteria |
| `deterministic_validator_output.json` | `deterministic.py` | Per-section semantic match results, hallucination checks |
| `mathematical_validator_report.json` | `mathematical.py` | Ground truth scores, MAE, RMSE, accuracy verdict |
| `rule_based_evidence.json` | `rule_based_evidence_generation.py` | 14-detector analysis, adjusted scores, per-section verdicts |
| `evidence_rules.json` | `rule_based_evidence_generation.py` | Dynamically generated rules (JSON array) |
| `final_validation_report.json` | `final_report.py` | Consolidated PASS/FAIL verdict with component verdicts |

#### `data/historical/`
| File Pattern | Generated By | Contains |
|--------------|-------------|----------|
| `EVD_{timestamp}_{uuid}.json` | `evidence_generation.py` | Versioned evidence documents with text blobs, keywords, summaries, and raw validator outputs |

---

## ⚙️ Prerequisites & Configuration

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Create a `.env` file from the template:
```bash
cp .env.example .env
```

Required environment variables:
```env
PINECONE_API_KEY=your_pinecone_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_openai_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

All settings are centralized in `src/config.py` via Pydantic Settings.

---

## 🚀 How to Run

### Run the Full Pipeline
```powershell
python main.py
```

With custom inputs:
```powershell
python main.py --jd data/inputs/job_description.json --ai data/inputs/score_my_resume_20260211_151434.json
```

### Run Specific Modules

| Command | What It Does |
|---------|-------------|
| `python -m src.validators.jd_validator` | Normalize & validate JD only |
| `python -m src.validators.deterministic` | Run semantic matching only |
| `python -m src.validators.mathematical` | Run ground-truth calculation only |
| `python -m src.processing.rule_based_evidence_generation` | Generate dynamic rules & evidence |
| `python -m src.processing.final_report` | Generate consolidated verdict |
| `python -m src.processing.evidence_generation` | Generate historical evidence document |
| `python -m src.retrieval.database` | Update Pinecone vector database |
| `python -m src.retrieval.engine --query "..." --mode corrective` | Query via Corrective RAG |
| `python -m src.retrieval.engine --query "..." --mode standard` | Query via Standard RAG |

### Logs
All modules use a standardized logging format defined in `src/logging_config.py`. Logs provide detailed insights into the validation steps and results.

---

## 🔑 Key Technologies

| Component | Technology |
|-----------|-----------|
| Embeddings | `sentence-transformers/all-MiniLM-L12-v2` (384-dim) |
| Vector DB | Pinecone (Serverless, AWS us-east-1, cosine metric) |
| LLM | Azure OpenAI (GPT-4o) |
| Framework | LangChain (core, openai, pinecone, huggingface) |
| Config | Pydantic Settings + python-dotenv |
| Similarity | Pure-Python cosine (avoids NumPy/torch ABI issues) |


### data\historical\EVD_20260311_110353_7e48751c.json(evidence) format:
{
  "evidence_id": "EVD_{timestamp}_{uuid}",
  "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffff+00:00",
  "job_id": "string",
  "job_title": "string",
  "text_blob": "string",
  "keywords": ["string"],
  "summary": {
    "deterministic_valid": true,
    "overall_coverage": float,
    "overall_token_overlap": float,
    "math_accuracy": float,
    "math_mae": float,
    "math_rmse": float,
    "final_verdict": true
  },
  "raw_sources": {
    "deterministic_validator_output": { ... },
    "mathematical_validator_report": { ... },
    "rule_based_evidence": { ... }
  }
}