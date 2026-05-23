# Resume Extraction & Parsing — Final Workflow

## Module Overview

**Directory:** `modularized_resume_extraction_normalization/`

This module is **Pipeline 1** of the RAIYA Recruiting Solution — the foundational data preparation layer. It takes raw resume files (PDF, DOCX, TXT, images) and converts them into clean, structured JSON with consistent field normalization. The module leverages the **DocStrange document extraction engine** for all processing, followed by a **Pydantic-based schema validation layer** that normalizes outputs into a single canonical schema.

> [!IMPORTANT]
> **Design Principles:**
> - **Unified Extraction** — Rely on the DocStrange document extraction library for all format handling (PDF, DOCX, Images).
> - **Schema-First Storage** — Only validated and normalized JSON is stored in the primary output and cache directories.
> - **Content-aware caching** — SHA-256 of raw file bytes enables deduplication across renamed/resubmitted files.
> - **Auditability** — Detailed validation reports are stored separately for every extraction run.

> [!NOTE]
> **Frontend Integration:** The RAIYA frontend (`/platform` page) simulates this pipeline's resume upload step. Resumes are only uploadable after the recruiter has created and confirmed a Job Description with weights via the `/create-job` page. The frontend uses `localStorage` to gate access: `raiya_confirmed_job` must exist before the resume upload section is unlocked.

---

## Architecture

```mermaid
graph TD
    INPUT["📄 Raw Resume File
    (PDF/DOCX/TXT/Image)"]

    subgraph "CLI Entry Point — main.py"
        MENU["📋 Interactive Menu
        (File Selection)"]
        CONFIG["⚙️ Config
        (Directories & Extensions)"]
    end

    subgraph "Hashing & Cache Layer"
        HASH_FILE["🔑 File SHA-256
        (Binary Fingerprint)"]
        CACHE{{"♻️ Cache Lookup
        (hashed_resume_extraction_results/)"}}
    end

    subgraph "Extraction & Validation Layer"
        DOCSTRANGE["📚 docstrange
        DocumentExtractor
        (extract_data with JSON schema)"]
        
        DETECT["🔍 Format Detection
        (structured_json / cloud_flat_json /
        specified_fields / extraction_failed)"]
        
        VALIDATE["🛡️ Pydantic Validation
        (ValidatedResumeSchema)"]
    end

    subgraph "Frontend Integration"
        FE_GATE["🔒 JD Confirmation Gate
        (raiya_confirmed_job in localStorage)"]
        FE_UPLOAD["📤 /platform Resume Upload
        (Batch Upload — up to 200 files)"]
        FE_SCORE["⚡ Start Scoring
        (Routes to /processing)"]
    end

    OUTPUT_PRIMARY["🏆 Validated JSON
    (resume_extraction_outputs/)"]
    
    OUTPUT_REPORT["📊 Validation Report
    (validated_resume_outputs/)"]
    
    CACHE_STORE["🗄️ Cache Store
    (hash.txt + hash.meta.json)"]

    INPUT --> CONFIG --> MENU
    MENU --> HASH_FILE
    HASH_FILE --> CACHE
    CACHE -->|"HIT"| OUTPUT_PRIMARY
    CACHE -->|"MISS"| DOCSTRANGE
    DOCSTRANGE -->|"Raw JSON"| DETECT
    DETECT --> VALIDATE
    
    VALIDATE -->|"Validated dict"| OUTPUT_PRIMARY
    VALIDATE -->|"Validation metadata"| OUTPUT_REPORT
    OUTPUT_PRIMARY --> CACHE_STORE

    FE_GATE -->|"Confirmed"| FE_UPLOAD
    FE_UPLOAD --> FE_SCORE
    FE_SCORE -.->|"Triggers backend"| MENU

    style CACHE fill:#f4a261,color:#000
    style DOCSTRANGE fill:#264653,color:#fff
    style VALIDATE fill:#059669,color:#fff
    style DETECT fill:#7c3aed,color:#fff
    style OUTPUT_PRIMARY fill:#059669,color:#fff
    style FE_GATE fill:#ef4444,color:#fff
    style FE_UPLOAD fill:#6366f1,color:#fff
    style FE_SCORE fill:#3b82f6,color:#fff
```

---

## Module Structure

```
modularized_resume_extraction_normalization/
├── main.py                                    # CLI entry point & processing pipeline
├── streamlit_resume_extraction.py             # Streamlit GUI with validation integration
├── requirements.txt                           # Dependency list (Python 3.12.0)
├── resume_extraction_parsing_final_workflow.md # ← This document
│
├── modules/
│   ├── __init__.py                # Package init — re-exports all public APIs
│   ├── config.py                  # Config class — directories, supported extensions, knobs
│   ├── file_utils.py              # File discovery, size formatting, filename sanitization
│   ├── menu.py                    # Interactive CLI menu — selection parsing
│   ├── hashing.py                 # SHA-256 hashing + cache system
│   ├── resume_schema_validation.py    # Pydantic schema validation & normalization
│   ├── reference_parsed_resume_format.json  # Canonical resume schema reference
│   └── docstrange-main/           # Embedded document extraction library
│
├── resume_extraction_outputs/         # Primary output (Validated & Normalized JSON)
│   └── *.json
│
├── validated_resume_outputs/          # Audit directory (Validation reports)
│   └── *_validation_report.json
│
├── hashed_resume_extraction_results/  # Content hash cache (Stores Validated JSON)
│   ├── <sha256>.txt
│   └── <sha256>.meta.json
│
└── resumes/                           # Input resume files
```

---

## Per-Resume Processing Pipeline — Simple 7-Step Flow

The `process_single_resume()` function executes the following pipeline for each file:

```mermaid
graph TD
    START["▶ Start: resume_path"]

    STEP1["STEP 1: File SHA-256
    Binary fingerprint of raw file bytes
    🔑 file_hash = sha256_bytes(...)"]

    STEP2{"STEP 2: Cache Check
    lookup_hash(file_hash, ...)"}

    CACHE_HIT["♻️ CACHE HIT
    Load cached Validated JSON
    → save to primary output"]

    STEP3["STEP 3: docstrange Extraction
    extractor = DocumentExtractor()
    result.extract_data(schema=RESUME_SCHEMA)"]

    STEP4["STEP 4: Pydantic Validation
    validate_resume(raw_json)
    → detect format & unwrap"]

    STEP5{"STEP 5: Select Data
    Validation Pass?"}

    DATA_VAL["🏆 Validated Dict"]
    DATA_RAW["⚠️ Raw Fallback"]

    STEP6["STEP 6: Primary Storage
    Store in Cache + Save to
    resume_extraction_outputs/<stem>.json"]

    STEP7["STEP 7: Audit Report
    Save validation metrics to
    validated_resume_outputs/"]

    DONE["✅ Done — return True"]

    START --> STEP1 --> STEP2
    STEP2 -->|"HIT"| CACHE_HIT --> DONE
    STEP2 -->|"MISS"| STEP3 --> STEP4 --> STEP5
    STEP5 -->|"Yes"| DATA_VAL --> STEP6
    STEP5 -->|"No"| DATA_RAW --> STEP6
    STEP6 --> STEP7 --> DONE

    style STEP1 fill:#6a4c93,color:#fff
    style STEP2 fill:#f4a261,color:#000
    style CACHE_HIT fill:#e9c46a,color:#000
    style STEP3 fill:#264653,color:#fff
    style STEP4 fill:#059669,color:#fff
    style DATA_VAL fill:#059669,color:#fff
    style DATA_RAW fill:#e76f51,color:#fff
    style STEP6 fill:#1d3557,color:#fff
```

---

## Frontend Resume Upload Workflow

The RAIYA frontend simulates the resume upload and scoring trigger process. This workflow is gated by Job Description creation and confirmation.

### End-to-End Frontend Flow

```mermaid
sequenceDiagram
    participant R as Recruiter
    participant CJ as /create-job
    participant LS as localStorage
    participant PL as /platform
    participant PR as /processing
    participant RE as /results

    Note over R,CJ: Phase 1: JD Creation
    R->>CJ: Create JD (manual or upload)
    CJ->>CJ: Fill form + assign weights
    CJ->>LS: Auto-save draft every 1s
    R->>CJ: Confirm weights (total=100)
    R->>CJ: Click "Create Job"
    CJ->>CJ: Shadowy confirmation modal
    R->>CJ: "Yes, Create Job"
    CJ->>LS: Save raiya_confirmed_job
    CJ->>PL: Redirect

    Note over R,PL: Phase 2: Resume Upload Gate
    PL->>LS: Read raiya_confirmed_job
    alt No confirmed job
        PL->>PL: Show locked state
        PL->>R: "Create Job Description" button
    else Job confirmed
        PL->>PL: Show JD summary card
        R->>PL: Click "View Details"
        PL->>PL: Shadowy modal (full JD + weights)
        R->>PL: "Start Resume Scoring"
        PL->>PL: "Are you ready?" alert
        R->>PL: "Yes, Let's Go!"
        PL->>PL: Unlock resume upload
    end

    Note over R,PL: Phase 3: Scoring
    R->>PL: Upload resumes (8 demo files)
    R->>PL: "Start Scoring with 8 Resumes"
    PL->>PR: Navigate to /processing
    PR->>PR: Batch processing simulation
    PR->>RE: Navigate to /results
```

### Platform Page State Machine

```mermaid
stateDiagram-v2
    [*] --> CheckLocalStorage: Page Mount

    CheckLocalStorage --> LockedState: No confirmed job
    CheckLocalStorage --> JobReady: raiya_confirmed_job found

    LockedState --> CreateJob: Click "Create Job Description"
    CreateJob --> [*]: Route to /create-job

    JobReady --> ViewJD: Click "View Details"
    ViewJD --> ScoringAlert: Click "Start Scoring"
    ViewJD --> JobReady: Close modal

    ScoringAlert --> ViewJD: Click "Review Again"
    ScoringAlert --> ScoringReady: Click "Yes, Let's Go!"

    ScoringReady --> ResumesUploaded: Upload resumes
    ResumesUploaded --> Scoring: "Start Scoring"
    Scoring --> [*]: Route to /processing
```

### Frontend Gate Logic

| Condition | Platform State | Resume Upload |
|-----------|---------------|---------------|
| No `raiya_confirmed_job` | Lock icon + "Create Job Description" CTA | **Locked** (hidden) |
| Job confirmed, not reviewed | JD summary card + "View Details" button | **Locked** (overlay) |
| Job reviewed + scoring confirmed | Full JD visible, resume section active | **Unlocked** |
| Resumes uploaded | File list with remove buttons | "Start Scoring" button active |

---

## Output Locations

| Output | Path | Format |
|--------|------|--------|
| **Validated JSON** | `resume_extraction_outputs/<stem>.json` | Primary clean output |
| **Validation report** | `validated_resume_outputs/<stem>_validation_report.json` | Audit diagnostics |
| **Hash cache** | `hashed_resume_extraction_results/` | Validated data store |

---

## Running the Pipeline

### Prerequisites

```bash
# Install dependencies from requirements.txt
pip install -r requirements.txt
```

### Execution — CLI

```bash
python main.py
```

### Execution — Streamlit GUI

```bash
streamlit run streamlit_resume_extraction.py
```

### Execution — Frontend (Static Demo)

```bash
cd raiya-resume-scoring-frontend
npm install
npm run dev
# Navigate to http://localhost:3000/create-job → create JD → /platform → upload resumes
```

---

## Pipeline Infrastructure ERD (Conceptual)

The following diagram illustrates the conceptual relationships between high-level system components such as the configuration, raw files, extraction results, and the cache layer. This is distinct from the database ERD and focuses on the file-and-process infrastructure.

```dot
graph ERD {
    // Pipeline Infrastructure ERD
    rankdir=TB;
    node [fontname="Segoe UI, Arial", fontsize=10, shape=box, style=filled, fillcolor="#f8f9fa", color="#adb5bd"];
    edge [fontname="Segoe UI, Arial", fontsize=9, color="#6c757d"];

    // ENTITIES
    CONFIG [label="CONFIG", fillcolor="#e9ecef"];
    RESUME [label="RESUME_FILE", fillcolor="#d1e7dd"];
    EXTRACT [label="EXTRACTION_RESULT", fillcolor="#fff3cd"];
    VALID [label="VALIDATED_RESUME", fillcolor="#cfe2ff"];
    CACHE [label="HASH_CACHE", fillcolor="#f8d7da"];

    // Weak Entity (double border)
    REPORT [peripheries=2, label="VALIDATION_REPORT", fillcolor="#f8d7da"];

    // ATTRIBUTES - CONFIG
    node [shape=ellipse, style=none, fillcolor=none, color="#6c757d"];
    CONFIG_ID [label=<<u>config_id</u>>];
    SUPPORTED [label="supported_extensions"];
    INPUT [label="input_directory"];
    OUTPUT [label="output_directory"];
    CACHE_DIR [label="hashed_output_directory"];
    WORKERS [label="max_workers"];

    CONFIG -- CONFIG_ID;
    CONFIG -- SUPPORTED;
    CONFIG -- INPUT;
    CONFIG -- OUTPUT;
    CONFIG -- CACHE_DIR;
    CONFIG -- WORKERS;

    // ATTRIBUTES - RESUME
    RESUME_ID [label=<<u>resume_id</u>>];
    FILE_NAME [label="file_name"];
    FILE_TYPE [label="file_extension"];
    FILE_PATH [label="file_path"];
    HASH [label="sha256_hash"];
    SIZE [label="file_size"];

    RESUME -- RESUME_ID;
    RESUME -- FILE_NAME;
    RESUME -- FILE_TYPE;
    RESUME -- FILE_PATH;
    RESUME -- HASH;
    RESUME -- SIZE;

    // ATTRIBUTES - EXTRACTION
    EXTRACTION_ID [label=<<u>extraction_id</u>>];
    FORMAT [label="source_format"];
    SUCCESS [label="is_success"];
    RAW_DATA [label="raw_json_content"];

    EXTRACT -- EXTRACTION_ID;
    EXTRACT -- FORMAT;
    EXTRACT -- SUCCESS;
    EXTRACT -- RAW_DATA;

    // ATTRIBUTES - VALIDATED
    VALID_ID [label=<<u>validation_id</u>>];
    NORMALIZED [label="canonical_json"];
    PASSED [label="is_valid"];
    TIMESTAMP [label="validated_at"];

    VALID -- VALID_ID;
    VALID -- NORMALIZED;
    VALID -- PASSED;
    VALID -- TIMESTAMP;

    // ATTRIBUTES - REPORT (weak)
    REPORT_ID [label="report_id (PK)"];
    ERRORS [label="error_list"];
    WARNINGS [label="warning_list"];
    FIELDS [label="populated_fields_count"];

    REPORT -- REPORT_ID;
    REPORT -- ERRORS;
    REPORT -- WARNINGS;
    REPORT -- FIELDS;

    // ATTRIBUTES - CACHE
    CACHE_ID [label=<<u>cache_id</u>>];
    CACHE_HASH [label="sha256_hash"];
    MAPPING [label="validated_json_path"];

    CACHE -- CACHE_ID;
    CACHE -- CACHE_HASH;
    CACHE -- MAPPING;

    // RELATIONSHIPS
    node [shape=diamond, style=filled, fillcolor="#ffffff", color="#adb5bd"];
    USES [label="USES_CONFIG"];
    PRODUCES [label="PRODUCES"];
    VALIDATES [label="VALIDATES"];
    GENERATES [label="GENERATES"];
    CACHED [label="CACHED_AS"];

    CONFIG -- USES [label="1"];
    USES -- RESUME [label="n"];

    RESUME -- PRODUCES [label="1"];
    PRODUCES -- EXTRACT [label="1"];

    EXTRACT -- VALIDATES [label="1"];
    VALIDATES -- VALID [label="1"];

    VALID -- GENERATES [label="1"];
    GENERATES -- REPORT [label="1"];

    RESUME -- CACHED [label="1"];
    CACHED -- CACHE [label="1"];
}
```
