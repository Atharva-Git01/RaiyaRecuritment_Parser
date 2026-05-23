# RAIYA Backend — PostgreSQL 16 + pgvector Database Setup

> **Complete Database Architecture & Setup Guide** for the RAIYA AI-Powered Resume Screening System  
> PostgreSQL 16 · pgvector 0.7+ · Redis 7.x · SQLAlchemy (async + sync) · Alembic Migrations

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation & Initial Setup](#installation--initial-setup)
3. [Database Configuration](#database-configuration)
4. [Schema Overview](#schema-overview)
5. [Core Tables (Relational)](#core-tables-relational)
6. [pgvector Tables (Embeddings)](#pgvector-tables-embeddings)
7. [Audit & Observability Tables](#audit--observability-tables)
8. [Pipeline 4 & Memory Tables](#pipeline-4--memory-tables)
9. [Indexes & Performance](#indexes--performance)
10. [Entity Relationship Diagram](#entity-relationship-diagram)
11. [Alembic Migrations](#alembic-migrations)
12. [SQLAlchemy Connection Layer](#sqlalchemy-connection-layer)
13. [pgvector Operations](#pgvector-operations)
14. [Redis Cache Layer](#redis-cache-layer)
15. [Backup & Maintenance](#backup--maintenance)
16. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Component | Version | Purpose |
|:---|:---:|:---|
| PostgreSQL | 16.x | Primary relational database |
| pgvector extension | 0.7+ | Vector similarity search (768-dim embeddings) |
| Redis | 7.x | Cache layer (OCR, embeddings, search, LLM responses) |
| Python | 3.11+ | Backend runtime |
| SQLAlchemy | 2.x | Async + sync ORM |
| Alembic | latest | Database migration management |
| asyncpg | latest | Async PostgreSQL driver (FastAPI routes + pipeline nodes) |
| psycopg[binary] | 3.x | Async PostgreSQL driver used by `langgraph-checkpoint-postgres` for `AsyncPostgresSaver` |
| psycopg2-binary | latest | Sync PostgreSQL driver (Alembic only) |
| langgraph-checkpoint-postgres | 2.x | `AsyncPostgresSaver` — creates and manages the `checkpoints`, `checkpoint_writes`, `checkpoint_blobs` tables |

---

## Installation & Initial Setup

### 1. Install PostgreSQL 16

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16
```

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Windows (Chocolatey):**
```powershell
choco install postgresql16
```

**Docker (Recommended for development):**
```bash
docker run -d \
  --name raiya-postgres \
  -e POSTGRES_USER=raiya \
  -e POSTGRES_PASSWORD=raiya_dev \
  -e POSTGRES_DB=raiya \
  -p 5432:5432 \
  -v raiya_pgdata:/var/lib/postgresql/data \
  pgvector/pgvector:pg16
```

> **Note**: The `pgvector/pgvector:pg16` image comes pre-installed with the pgvector extension.

### 2. Install pgvector Extension

If not using the pgvector Docker image:

```bash
# Build from source
cd /tmp
git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install  # requires sudo on Linux
```

### 3. Create the Database & User

```sql
-- Connect as superuser
sudo -u postgres psql

-- Create the RAIYA user and database
CREATE USER raiya WITH PASSWORD 'raiya_dev' CREATEDB;
CREATE DATABASE raiya OWNER raiya;

-- Connect to the RAIYA database
\c raiya

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify pgvector is installed
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Expected output: 0.7.4 (or higher)

-- Grant schema permissions
GRANT ALL PRIVILEGES ON DATABASE raiya TO raiya;
GRANT ALL ON SCHEMA public TO raiya;
```

### 4. Install Redis

```bash
# Docker (recommended)
docker run -d \
  --name raiya-redis \
  -p 6379:6379 \
  redis:7-alpine

# Or via package manager
sudo apt install -y redis-server  # Ubuntu
brew install redis                # macOS
```

### 5. Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: raiya-postgres
    environment:
      POSTGRES_USER: raiya
      POSTGRES_PASSWORD: raiya_dev
      POSTGRES_DB: raiya
    ports:
      - "5432:5432"
    volumes:
      - raiya_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U raiya"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: raiya-redis
    ports:
      - "6379:6379"
    volumes:
      - raiya_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  raiya_pgdata:
  raiya_redis_data:
```

```bash
docker-compose up -d
```

---

## Database Configuration

### Environment Variables (`.env`)

```env
# PostgreSQL Connection URLs
DATABASE_URL=postgresql+asyncpg://raiya:raiya_dev@localhost:5432/raiya
SYNC_DATABASE_URL=postgresql://raiya:raiya_dev@localhost:5432/raiya

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Connection URL Breakdown

| Component | Async (FastAPI, nodes, AsyncPostgresSaver) | Sync (Alembic only) |
|:---|:---|:---|
| **Driver** | `postgresql+asyncpg` | `postgresql` (psycopg2) |
| **User** | `raiya` | `raiya` |
| **Password** | `raiya_dev` | `raiya_dev` |
| **Host** | `localhost` | `localhost` |
| **Port** | `5432` | `5432` |
| **Database** | `raiya` | `raiya` |

> **Note on the checkpointer**: `AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)` consumes the **async** URL, not the sync one. The sync engine is now only used by Alembic migrations.

### Settings Class (`app/core/config.py`)

```python
# ── Database (PostgreSQL 16 + pgvector) ──────────────────────
DATABASE_URL: str = "postgresql+asyncpg://raiya:raiya_dev@localhost:5432/raiya"
SYNC_DATABASE_URL: str = "postgresql://raiya:raiya_dev@localhost:5432/raiya"

# ── Embeddings (unified: BGE-large-en-v1.5 for all) ────────
EMBEDDING_MODEL_PRIMARY: str = "BAAI/bge-large-en-v1.5"
EMBEDDING_DIMS_PRIMARY: int = 768
```

---

## Schema Overview

The RAIYA database contains **15 Alembic-managed tables** organized into 4 categories. A live database will additionally hold **3 LangGraph-managed checkpoint tables** (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) created at app startup by `AsyncPostgresSaver.setup()` — they are **not** declared in `app/models/` and **not** part of any Alembic revision. See [LangGraph Async Checkpointer](#langgraph-async-checkpointer) below.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAIYA Database Schema (15 tables)                    │
│                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │  CORE (6 tables)    │  │  VECTOR / pgvector (3 tables)           │  │
│  │  organizations      │  │  resume_embeddings      (768-dim)       │  │
│  │  users              │  │  jd_embeddings          (768-dim)       │  │
│  │  otp_tokens         │  │  rag_evidence_embeddings (768-dim)      │  │
│  │  job_descriptions   │  └─────────────────────────────────────────┘  │
│  │  resumes            │                                                │
│  │  batches            │  ┌─────────────────────────────────────────┐  │
│  └─────────────────────┘  │  AUDIT (4 tables)                       │  │
│                            │  match_results                          │  │
│  ┌─────────────────────┐  │  reasoning_log                          │  │
│  │  PIPELINE (2 tables)│  │  hash_chain_log                         │  │
│  │  interview_         │  │  token_usage_log                        │  │
│  │    invitations      │  └─────────────────────────────────────────┘  │
│  │  pipeline_memory    │                                                │
│  └─────────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

| Category | Table Count | Purpose |
|:---|:---:|:---|
| **Core** | 6 | Multi-tenant user management, documents, batch processing |
| **pgvector** | 3 | 768-dim BGE-large-en-v1.5 embeddings for semantic search |
| **Audit** | 4 | Scoring results, reasoning trails, hash chains, token costs |
| **Pipeline** | 2 | Interview email logs, node execution memory |

---

## Core Tables (Relational)

### `organizations`

Multi-tenant organization management. Every user, JD, and batch belongs to an organization.

```sql
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    org_code        VARCHAR(50)  UNIQUE NOT NULL,
    plan            VARCHAR(50)  DEFAULT 'free',    -- free|pro|enterprise
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);
```

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | UUID | PK, auto-gen | Organization identifier |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `org_code` | VARCHAR(50) | UNIQUE, NOT NULL | URL-safe org slug |
| `plan` | VARCHAR(50) | DEFAULT 'free' | Subscription tier |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |

---

### `users`

Recruiter accounts with password or OAuth authentication.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    full_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20),
    address         TEXT,
    role            VARCHAR(20) DEFAULT 'recruiter',  -- recruiter|admin|superadmin
    hashed_password VARCHAR(255),
    oauth_provider  VARCHAR(50),     -- google|github|null
    oauth_sub       VARCHAR(255),    -- OAuth subject ID
    phone_verified  BOOLEAN DEFAULT FALSE,
    email_verified  BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(org_id);
```

**Key relationships:**
- `org_id` → `organizations.id` (CASCADE delete)
- Referenced by: `job_descriptions.uploaded_by`, `batches.created_by`, `otp_tokens.user_id`

---

### `otp_tokens`

One-time password tokens for email/SMS authentication.

```sql
CREATE TABLE otp_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    channel     VARCHAR(10) NOT NULL,       -- email|sms
    otp_hash    VARCHAR(255) NOT NULL,      -- bcrypt-hashed OTP
    purpose     VARCHAR(50) NOT NULL,       -- login|reset|verify
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

### `job_descriptions`

JD documents with full pipeline lifecycle tracking: extraction → normalization → weight assignment → HiTL verification.

```sql
CREATE TABLE job_descriptions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID REFERENCES organizations(id),
    uploaded_by                 UUID REFERENCES users(id),
    file_name                   VARCHAR(500),
    file_hash                   VARCHAR(80) NOT NULL,       -- SHA-256 of file bytes
    content_hash                VARCHAR(80) NOT NULL,       -- SHA-256 of extracted JSON
    extracted_json              JSONB,                      -- jd_pdf_extraction_schema output
    extraction_hash             VARCHAR(80),
    ocr_confidence              FLOAT,                      -- Nanonets confidence (0-100)
    normalized_json             JSONB,                      -- Alias-resolved JD
    normalized_hash             VARCHAR(80),
    weights_json                JSONB,                      -- jd_weights_schema_format output
    weights_hash_pre_hitl       VARCHAR(80),                -- Hash before human review
    weights_hash                VARCHAR(80),                -- Hash after HiTL approval
    weight_strategy             VARCHAR(80) DEFAULT 'criteria_average_normalized',
    weight_generation_metadata  JSONB,                      -- Phase 14 metadata
    normalization_factor        FLOAT,                      -- Total raw weight for normalization
    total_raw_weight            FLOAT,                      -- Sum of adjusted raw weights
    hitl_verified               BOOLEAN DEFAULT FALSE,
    hitl_verified_at            TIMESTAMPTZ,
    hitl_verified_by            UUID REFERENCES users(id),
    version                     INTEGER DEFAULT 1,
    status                      VARCHAR(30) DEFAULT 'uploaded',
    -- Status flow: uploaded → extracting → weights_assigned → hitl_pending → verified → active
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jd_org       ON job_descriptions(org_id);
CREATE INDEX idx_jd_file_hash ON job_descriptions(file_hash);
```

**JSONB columns store these reference schemas:**

| Column | Reference Schema | Size Estimate |
|:---|:---|:---|
| `extracted_json` | `jd_pdf_extraction_schema.json` | 5–20 KB |
| `weights_json` | `jd_weights_schema_format.json` | 10–50 KB |
| `weight_generation_metadata` | Phase 14 audit metadata | 2–5 KB |

---

### `resumes`

Resume documents. Primary key is `file_id` (NOT `id`). No `raw_text` column — Nanonets returns structured JSON directly. Candidate name/email are derived from `parsed_json` at query time via ORM properties.

```sql
CREATE TABLE resumes (
    file_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        UUID,                           -- Links to batches.id
    file_name       VARCHAR(500),
    file_hash       VARCHAR(80) NOT NULL,           -- SHA-256 of file bytes
    content_hash    VARCHAR(80) NOT NULL,           -- SHA-256 of extracted JSON
    parsed_json     JSONB,                          -- resume_pdf_extraction_schema output
    extraction_hash VARCHAR(80),
    ocr_confidence  FLOAT,
    status          VARCHAR(30) DEFAULT 'uploaded', -- uploaded|processing|completed|failed
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resume_file_hash ON resumes(file_hash);
CREATE INDEX idx_resume_batch     ON resumes(batch_id);
```

> **Important Design Decision**: The `resumes` table has **no** `candidate_name` or `candidate_email` columns. These values are read dynamically from `parsed_json` via SQLAlchemy `@property` decorators on the `Resume` ORM model:
> ```python
> @property
> def candidate_name(self) -> str:
>     return self.parsed_json.get("name", "Unknown") if self.parsed_json else "Unknown"
>
> @property
> def candidate_email(self) -> str:
>     return self.parsed_json.get("email", "") if self.parsed_json else ""
> ```

---

### `batches`

Batch processing groups. Each batch links a JD to multiple resumes for scoring.

```sql
CREATE TABLE batches (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                    UUID REFERENCES organizations(id),
    jd_id                     UUID REFERENCES job_descriptions(id),
    created_by                UUID REFERENCES users(id),
    name                      VARCHAR(255),
    total_resumes             INTEGER DEFAULT 0,
    completed                 INTEGER DEFAULT 0,
    failed                    INTEGER DEFAULT 0,
    status                    VARCHAR(30) DEFAULT 'queued',
    -- Status flow: queued → processing → completed|failed|partial
    email_notification_status VARCHAR(30) DEFAULT 'pending',
    -- Email status: pending → sent|failed|skipped
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    completed_at              TIMESTAMPTZ
);
```

---

## pgvector Tables (Embeddings)

All three vector tables use the **same embedding model** and dimension for consistency:

| Parameter | Value |
|:---|:---|
| **Model** | `BAAI/bge-large-en-v1.5` |
| **Dimensions** | 768 |
| **Distance Metric** | Cosine similarity (`<=>` operator) |
| **Index Type** | IVFFlat (100 lists) |
| **Chunking** | `RecursiveJsonSplitter` (300–500 tokens per chunk) |

### `resume_embeddings`

Stores chunked resume embeddings for semantic retrieval during scoring.

```sql
CREATE TABLE resume_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_file_id  UUID REFERENCES resumes(file_id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    dimension       VARCHAR(50) NOT NULL,     -- skills|experience|education|general
    chunk_text      TEXT NOT NULL,             -- Original text chunk
    embedding       vector(768) NOT NULL,     -- BGE-large-en-v1.5 vector
    chunk_hash      VARCHAR(80) NOT NULL,     -- SHA-256 of chunk text
    metadata        JSONB,                    -- Optional metadata
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity index (cosine distance)
CREATE INDEX ON resume_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Composite lookup index
CREATE INDEX idx_re_file_dim ON resume_embeddings(resume_file_id, dimension);
```

**Chunking configuration:**
```python
# RecursiveJsonSplitter settings
JSON_SPLITTER_RESUME_MAX_CHUNK = 300  # tokens per chunk
```

---

### `jd_embeddings`

Stores chunked JD embeddings for dense retrieval in hybrid search.

```sql
CREATE TABLE jd_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_id       UUID REFERENCES job_descriptions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    dimension   VARCHAR(50) NOT NULL,     -- requirements|responsibilities|qualifications|general
    chunk_text  TEXT NOT NULL,
    embedding   vector(768) NOT NULL,
    chunk_hash  VARCHAR(80) NOT NULL,
    metadata    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX ON jd_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Chunking configuration:**
```python
JSON_SPLITTER_JD_MAX_CHUNK = 400  # tokens per chunk
```

---

### `rag_evidence_embeddings`

Stores RAG validation evidence vectors for historical retrieval and audit.

```sql
CREATE TABLE rag_evidence_embeddings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id   VARCHAR(120) NOT NULL,      -- EVD_{timestamp}_{uuid}
    source_type   VARCHAR(50) NOT NULL,       -- rule_based|deterministic|mathematical
    section_name  VARCHAR(80) NOT NULL,       -- skills|experience|technologies|...
    chunk_text    TEXT NOT NULL,
    embedding     vector(768) NOT NULL,
    chunk_hash    VARCHAR(80) NOT NULL,
    metadata      JSONB,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX ON rag_evidence_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Chunking configuration:**
```python
JSON_SPLITTER_EVD_MAX_CHUNK = 500  # tokens per chunk
```

---

## Audit & Observability Tables

### `match_results`

The central scoring output table. Stores all 9 canonical pipeline schema outputs as JSONB columns for every resume-JD pair.

```sql
CREATE TABLE match_results (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id                UUID REFERENCES batches(id),
    resume_file_id          UUID REFERENCES resumes(file_id),
    jd_id                   UUID REFERENCES job_descriptions(id),
    output_hash             VARCHAR(80),

    -- final_result_scoring_agent_schema (complete pipeline output)
    final_result_json       JSONB,
    final_score             FLOAT,

    -- deterministic_validator_output_schema
    deterministic_report    JSONB,

    -- mathematical_validator_report_schema
    mathematical_report     JSONB,

    -- rule_based_evidence_schema
    rule_based_evidence     JSONB,

    -- final_validation_report_schema (RAG verdict)
    rag_final_verdict       JSONB,

    -- Reasoning engine outputs
    reasoning_labels        JSONB,            -- Phase 4 label assignments
    reasoning_context       TEXT,             -- Full reasoning narrative
    reasoning_hash          VARCHAR(80),

    -- LLM explanation
    llm_explanation         TEXT,             -- Human-readable explanation
    explanation_hash        VARCHAR(80),

    -- Guardrails metadata
    guardrails_applied      JSONB,

    -- Scoring trace (added in migration 002)
    scoring_trace           JSONB,            -- Per-section score derivation
    weight_strategy_used    VARCHAR(80),

    -- Verdicts
    recommendation          VARCHAR(30),      -- excellent|good|average|poor|rejected
    is_valid                BOOLEAN DEFAULT FALSE,
    hallucinations_detected BOOLEAN DEFAULT FALSE,
    is_confident            BOOLEAN DEFAULT FALSE,
    math_accuracy           FLOAT,            -- % accuracy vs ground truth
    mae                     FLOAT,            -- importance_weighted_mae

    -- Ranking
    rank                    INTEGER,          -- Position within batch
    percentile              FLOAT,            -- Percentile within batch
    cache_hit               BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_result_batch ON match_results(batch_id);
CREATE INDEX idx_result_score ON match_results(batch_id, final_score);
```

**JSONB columns map to these reference schemas:**

| Column | Reference Schema | Validated By |
|:---|:---|:---|
| `final_result_json` | `final_result_scoring_agent_schema.json` | `FinalResultScoringAgent` |
| `deterministic_report` | `deterministic_validator_output_schema.json` | `DeterministicValidatorOutput` |
| `mathematical_report` | `mathematical_validator_report_schema.json` | `MathematicalValidatorReport` |
| `rule_based_evidence` | `rule_based_evidence_schema.json` | `RuleBasedEvidenceSchema` |
| `rag_final_verdict` | `final_validation_report_schema.json` | `FinalValidationReport` |
| `reasoning_labels` | Internal reasoning schema | — |
| `guardrails_applied` | `extracted_rules_schema.json` | `ExtractedRules` |
| `scoring_trace` | Scoring trace (within final_result) | `ScoringTraceEntry` |

---

### `reasoning_log`

Detailed 5-phase reasoning engine audit trail per resume-JD pair.

```sql
CREATE TABLE reasoning_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id            UUID REFERENCES batches(id),
    resume_file_id      UUID REFERENCES resumes(file_id),
    jd_id               UUID REFERENCES job_descriptions(id),
    structural_facts    JSONB,     -- Phase 1: factual extraction
    evidence_map        JSONB,     -- Phase 2: evidence mapping
    reasoning_labels    JSONB,     -- Phase 3: label assignment
    verification_report JSONB,     -- Phase 5: verification output
    reasoning_context   TEXT,      -- Full narrative text
    phases_completed    INTEGER DEFAULT 5,
    corrections_applied INTEGER DEFAULT 0,
    cache_hit           BOOLEAN DEFAULT FALSE,
    reasoning_hash      VARCHAR(80),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

### `hash_chain_log`

Append-only tamper-proof hash chain for pipeline integrity verification. Each entry chains to the previous via `chain_hash`.

```sql
CREATE TABLE hash_chain_log (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          VARCHAR(80),
    stage               VARCHAR(80),       -- extract_jd|embed_resume|score_adjustment|...
    artifact_type       VARCHAR(80),       -- jd_extraction|resume_parsed|match_output|...
    artifact_id         VARCHAR(255),
    content_hash        VARCHAR(80),       -- SHA-256 of artifact content
    chain_hash          VARCHAR(80) NOT NULL,   -- H(content_hash || previous_chain_hash)
    previous_chain_hash VARCHAR(80),
    actor               VARCHAR(20) DEFAULT 'system',   -- system|human|llm
    metadata            JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chain_session ON hash_chain_log(session_id);
```

**Chain verification:**
```python
# Verify chain integrity
chain_hash = sha256(f"{content_hash}{previous_chain_hash}".encode()).hexdigest()
```

---

### `token_usage_log`

LLM token monitoring for cost tracking and budget management.

```sql
CREATE TABLE token_usage_log (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        UUID,
    resume_file_id  UUID,
    model           VARCHAR(100),       -- phi4|bge-large-en-v1.5
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    total_tokens    INTEGER,
    est_cost_usd    NUMERIC(10, 6),     -- Estimated cost in USD
    pipeline_stage  VARCHAR(80),        -- weight_assignment|reasoning|explanation|...
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**Cost calculation formula:**
```python
est_cost_usd = (prompt_tokens / 1000 * 0.00030) + (completion_tokens / 1000 * 0.00060)
```

---

### `weight_generation_log`

Weight assignment audit trail (added in migration 002).

```sql
CREATE TABLE weight_generation_log (
    id                  BIGSERIAL PRIMARY KEY,
    jd_id               UUID REFERENCES job_descriptions(id),
    strategy            VARCHAR(80),            -- ontology_label_criteria_average_normalized
    raw_weights         JSONB,                  -- Pre-normalization weights
    normalized_weights  JSONB,                  -- Post-normalization (sum=100)
    normalization_factor FLOAT,
    section_criteria    JSONB,                  -- Criteria per section
    validation_passed   BOOLEAN DEFAULT FALSE,
    validation_errors   JSONB,
    llm_model           VARCHAR(100),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Pipeline 4 & Memory Tables

### `interview_invitations`

HR email notification log for Pipeline 4. Each row represents a single notification email sent to the HR recruiter.

```sql
CREATE TABLE interview_invitations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id          UUID REFERENCES batches(id),
    hr_email          VARCHAR(255) NOT NULL,
    hr_name           VARCHAR(255),
    job_title         VARCHAR(500),
    candidates_count  INTEGER DEFAULT 0,
    email_subject     VARCHAR(500),
    status            VARCHAR(30) DEFAULT 'queued',    -- queued|sent|failed
    smtp_response     TEXT,
    error_message     TEXT,
    retry_count       INTEGER DEFAULT 0,
    candidates_json   JSONB,                           -- Snapshot of candidates included
    sent_at           TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_interview_invitations_batch_id
    ON interview_invitations(batch_id);
```

**`candidates_json` structure:**
```json
[
  {
    "rank": 1,
    "candidate_name": "Jane Doe",
    "candidate_email": "jane@example.com",
    "final_score": 87.5,
    "recommendation": "excellent",
    "skills_score": 22.3,
    "experience_score": 18.1,
    "technologies_score": 19.8,
    "qualification_score": 14.2
  }
]
```

---

### `pipeline_memory`

Node-level execution tracking for crash recovery, pipeline resume, and audit trails.

```sql
CREATE TABLE pipeline_memory (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(80) NOT NULL,
    batch_id        VARCHAR(80),
    node_name       VARCHAR(100) NOT NULL,     -- extract_jd|hybrid_search|send_interview_emails|...
    status          VARCHAR(30) DEFAULT 'started',  -- started|completed|failed
    state_snapshot  JSONB,                     -- Pipeline state at completion (optional)
    error_message   TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX ON pipeline_memory(session_id);
CREATE INDEX ON pipeline_memory(batch_id);
```

**Usage via `PipelineMemoryStore`:**
```python
from app.db.memory_persistence import get_memory_store

store = get_memory_store()

# Log node execution
log_id = await store.log_node_start("session_123", "hybrid_search", batch_id="batch_456")
await store.log_node_complete(log_id, state_snapshot={"final_score": 87.5})

# Resume from failure
last_node = await store.get_last_completed_node("session_123")
# Returns: "hybrid_search" → resume from next node
```

---

## Indexes & Performance

### Index Summary

| Table | Index Name | Columns | Type | Purpose |
|:---|:---|:---|:---|:---|
| `users` | `idx_users_org` | `org_id` | B-tree | Org user lookup |
| `users` | (unique) | `email` | B-tree | Login uniqueness |
| `job_descriptions` | `idx_jd_org` | `org_id` | B-tree | Org JD listing |
| `job_descriptions` | `idx_jd_file_hash` | `file_hash` | B-tree | Duplicate detection |
| `resumes` | `idx_resume_file_hash` | `file_hash` | B-tree | Duplicate detection |
| `resumes` | `idx_resume_batch` | `batch_id` | B-tree | Batch resume listing |
| `match_results` | `idx_result_batch` | `batch_id` | B-tree | Batch results lookup |
| `match_results` | `idx_result_score` | `batch_id, final_score` | B-tree | Ranked results |
| `hash_chain_log` | `idx_chain_session` | `session_id` | B-tree | Chain verification |
| `resume_embeddings` | (ivfflat) | `embedding` | IVFFlat | Cosine similarity |
| `resume_embeddings` | `idx_re_file_dim` | `resume_file_id, dimension` | B-tree | Scoped search |
| `jd_embeddings` | (ivfflat) | `embedding` | IVFFlat | Cosine similarity |
| `rag_evidence_embeddings` | (ivfflat) | `embedding` | IVFFlat | Cosine similarity |
| `interview_invitations` | `ix_interview_invitations_batch_id` | `batch_id` | B-tree | Batch email lookup |
| `pipeline_memory` | (auto) | `session_id` | B-tree | Session lookup |
| `pipeline_memory` | (auto) | `batch_id` | B-tree | Batch tracking |

### IVFFlat Index Tuning

```sql
-- Default: 100 lists (good for <100K rows per table)
CREATE INDEX ON resume_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- For 100K–1M rows: increase lists
-- Rule of thumb: lists = sqrt(row_count)
ALTER INDEX resume_embeddings_embedding_idx SET (lists = 316);

-- Set probes at query time (higher = more accurate, slower)
SET ivfflat.probes = 10;  -- Default: 1, Recommended: 10-20
```

### Recommended PostgreSQL Configuration

```ini
# postgresql.conf tuning for RAIYA workload

# Memory
shared_buffers = 4GB              # 25% of system RAM
effective_cache_size = 12GB       # 75% of system RAM
work_mem = 256MB                  # For sorting/hashing operations
maintenance_work_mem = 1GB        # For CREATE INDEX, VACUUM

# Parallelism
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 16

# WAL
wal_buffers = 64MB
max_wal_size = 4GB
min_wal_size = 1GB

# pgvector-specific
# Increase work_mem for IVFFlat index builds
# maintenance_work_mem should be ≥ embedding_table_size

# Connection pooling
max_connections = 200
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    organizations ||--o{ users : "has"
    organizations ||--o{ job_descriptions : "has"
    organizations ||--o{ batches : "has"

    users ||--o{ otp_tokens : "has"
    users ||--o{ job_descriptions : "uploaded"

    job_descriptions ||--o{ batches : "scored by"
    job_descriptions ||--o{ jd_embeddings : "embedded as"

    batches ||--o{ match_results : "contains"
    batches ||--o{ interview_invitations : "notified via"
    batches }o--|| users : "created by"

    resumes ||--o{ match_results : "scored in"
    resumes ||--o{ resume_embeddings : "embedded as"

    match_results }o--|| job_descriptions : "against"

    organizations {
        UUID id PK
        VARCHAR name
        VARCHAR org_code UK
        VARCHAR plan
    }

    users {
        UUID id PK
        UUID org_id FK
        VARCHAR full_name
        VARCHAR email UK
        VARCHAR role
    }

    job_descriptions {
        UUID id PK
        UUID org_id FK
        JSONB extracted_json
        JSONB weights_json
        BOOLEAN hitl_verified
    }

    resumes {
        UUID file_id PK
        UUID batch_id
        JSONB parsed_json
        VARCHAR file_hash
    }

    batches {
        UUID id PK
        UUID jd_id FK
        UUID created_by FK
        INTEGER total_resumes
        VARCHAR status
    }

    match_results {
        UUID id PK
        UUID batch_id FK
        UUID resume_file_id FK
        FLOAT final_score
        JSONB final_result_json
        VARCHAR recommendation
    }

    resume_embeddings {
        UUID id PK
        UUID resume_file_id FK
        vector_768 embedding
        VARCHAR dimension
    }

    jd_embeddings {
        UUID id PK
        UUID jd_id FK
        vector_768 embedding
        VARCHAR dimension
    }

    rag_evidence_embeddings {
        UUID id PK
        VARCHAR evidence_id
        vector_768 embedding
        VARCHAR source_type
    }

    interview_invitations {
        UUID id PK
        UUID batch_id FK
        VARCHAR hr_email
        VARCHAR status
        JSONB candidates_json
    }

    pipeline_memory {
        BIGINT id PK
        VARCHAR session_id
        VARCHAR node_name
        VARCHAR status
    }
```

---

## Alembic Migrations

### Migration History

| Revision | File | Description |
|:---|:---|:---|
| `001` | `001_initial_schema.py` | Core tables (9) + pgvector extension + 3 embedding tables + indexes |
| `002` | `002_weight_metadata_pgvector.py` | Weight audit columns on `job_descriptions` + `match_results` + `weight_generation_log` table |
| `003` | `003_interview_invitations.py` | `interview_invitations` + `pipeline_memory` tables + `batches.email_notification_status` |

### Alembic Configuration

**`migrations/env.py`** connects to the database and auto-discovers all ORM models:

```python
# Loads from SYNC_DATABASE_URL environment variable
db_url = os.getenv("SYNC_DATABASE_URL", "postgresql://raiya:raiya_dev@localhost:5432/raiya")

# Auto-discovers all models via: from app.models import *
target_metadata = Base.metadata
```

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply a specific migration
alembic upgrade 001
alembic upgrade 002
alembic upgrade 003

# Rollback one migration
alembic downgrade -1

# Rollback to initial state
alembic downgrade base

# Check current version
alembic current

# Generate a new migration (auto-detect changes)
alembic revision --autogenerate -m "description"

# Show migration history
alembic history
```

### Creating New Migrations

```bash
# 1. Modify an ORM model in app/models/
# 2. Auto-generate migration
alembic revision --autogenerate -m "add_new_column_to_batches"

# 3. Review the generated file in migrations/versions/
# 4. Apply
alembic upgrade head
```

---

## SQLAlchemy Connection Layer

### Dual Engine Architecture

RAIYA uses two SQLAlchemy engines for different use cases:

```python
# app/db/database.py

# ── Async Engine (FastAPI routes, pipeline nodes) ────────────────
async_engine = create_async_engine(
    "postgresql+asyncpg://raiya:raiya_dev@localhost:5432/raiya",
    pool_size=20,           # Concurrent connections
    max_overflow=10,        # Burst capacity
    pool_pre_ping=True,     # Detect stale connections
    pool_recycle=3600,      # Recycle connections every hour
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync Engine (Alembic only) ────────────────────────────────────
# Historically backed the sync LangGraph PostgresSaver, but the v8 lifespan
# now uses AsyncPostgresSaver against settings.DATABASE_URL (async URL).
# This sync engine is kept for Alembic, which has no async story.
sync_engine = create_engine(
    "postgresql://raiya:raiya_dev@localhost:5432/raiya",
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)
```

### LangGraph Async Checkpointer

The LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) are **owned by `langgraph-checkpoint-postgres`** — not declared in `app/models/` and not part of Alembic migrations. They are created idempotently at startup by `AsyncPostgresSaver.setup()` inside the FastAPI lifespan:

```python
# app/db/memory_persistence.py
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@asynccontextmanager
async def open_async_checkpointer():
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as cp:
        await cp.setup()   # idempotent; creates checkpoints / checkpoint_writes / checkpoint_blobs
        yield cp

# app/main.py
async with open_async_checkpointer() as checkpointer:
    app.state.checkpointer = checkpointer
    app.state.graph = build_graph(checkpointer=checkpointer)
    yield
```

> **Do not declare these tables in `app/models/` or include them in Alembic.** Letting two systems own the same schema causes drift. The pgvector tables and the 15 application tables in this doc remain Alembic-managed; the three checkpoint tables are LangGraph-managed.
>
> **HITL resume mechanism**: state persists across the `interrupt_before=["hitl_pause"]` pause via the checkpoint tables. Resume is one async call: `await graph.ainvoke(Command(resume={"hitl_verified": True, "jd_weights": approved}), context=ctx, config={"configurable": {"thread_id": session_id}})`.

### FastAPI Dependency

```python
# Usage in FastAPI route handlers
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Route example
@router.get("/batches")
async def list_batches(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Batch).order_by(Batch.created_at.desc()))
    return result.scalars().all()
```

### Connection Pool Sizing Guide

| Use Case | Pool Size | Max Overflow | Total |
|:---|:---:|:---:|:---:|
| Development (1 worker) | 5 | 5 | 10 |
| Staging (2 workers) | 10 | 5 | 15 |
| Production (4 workers) | 20 | 10 | 30 |
| High Load (8 workers) | 30 | 20 | 50 |

> **Rule**: `(pool_size + max_overflow) × worker_count ≤ max_connections`

---

## pgvector Operations

### Embedding Lifecycle

```
Resume PDF → Nanonets OCR → JSON → RecursiveJsonSplitter → BGE-large-en-v1.5 → pgvector
```

### Upsert Operations (via `pgvector_client.py`)

```python
from app.db.pgvector_client import upsert_resume_embeddings, search_resume_embeddings

# ── Upsert embeddings ────────────────────────────────────────────
# Deletes existing embeddings for the resume, then inserts new ones
count = await upsert_resume_embeddings(
    session=db_session,
    resume_file_id="uuid-string",
    chunks=[
        {"chunk_index": 0, "dimension": "skills", "text": "Python, FastAPI...", "chunk_hash": "abc123"},
        {"chunk_index": 1, "dimension": "experience", "text": "5 years at...", "chunk_hash": "def456"},
    ],
    embeddings=[
        [0.123, -0.456, ...],  # 768-dim vector
        [0.789, -0.012, ...],
    ],
)
```

### Search Operations

```python
# ── Cosine similarity search ─────────────────────────────────────
results = await search_resume_embeddings(
    session=db_session,
    query_embedding=[0.1, -0.2, ...],     # 768-dim query vector
    resume_file_id="uuid-string",          # Optional: scope to specific resume
    dimension="skills",                     # Optional: scope to dimension
    top_k=10,                              # Number of results
)

# Returns:
# [
#     {"chunk_text": "Python, FastAPI...", "dimension": "skills",
#      "chunk_index": 0, "chunk_hash": "abc123", "similarity": 0.92},
#     ...
# ]
```

### Raw SQL for pgvector

```sql
-- Cosine similarity search (used by pgvector_client.py)
SELECT chunk_text, dimension, chunk_index,
       1 - (embedding <=> $1::vector) AS similarity
FROM resume_embeddings
WHERE resume_file_id = $2
ORDER BY embedding <=> $1::vector
LIMIT 10;

-- Euclidean distance (L2)
SELECT *, embedding <-> $1::vector AS distance
FROM jd_embeddings ORDER BY distance LIMIT 5;

-- Inner product
SELECT *, (embedding <#> $1::vector) * -1 AS inner_product
FROM resume_embeddings ORDER BY embedding <#> $1::vector LIMIT 5;

-- Count embeddings per resume
SELECT resume_file_id, COUNT(*) as chunk_count
FROM resume_embeddings
GROUP BY resume_file_id;

-- Average embedding dimension check
SELECT AVG(array_length(embedding::float[], 1)) FROM resume_embeddings;
```

### Hybrid Search (Pipeline 3)

The `hybrid_search` node combines pgvector dense search with BM25 sparse search:

```
Dense Score (pgvector):  weight = 0.65
BM25 Score (sparse):     weight = 0.35
Fusion: Reciprocal Rank Fusion (RRF, k=60)

Final Score = 0.65 × dense_similarity + 0.35 × bm25_score
```

---

## Redis Cache Layer

### Cache Architecture

Redis serves as a multi-layer cache to avoid redundant OCR, embedding, LLM, and search computations:

```
Request → Redis Cache Check → Hit? → Return Cached
                             ↓ Miss
                       Compute → Store in Redis (with TTL) → Return
```

### Cache Key Patterns

| Key Pattern | TTL | Description |
|:---|:---:|:---|
| `ocr:{file_hash}` | 30 days | Nanonets OCR extraction result |
| `parsed:{content_hash}` | 7 days | Parsed/validated document JSON |
| `emb:{chunk_hash}` | 7 days | Pre-computed embedding vectors |
| `weights:{content_hash}` | 48 hours | JD weight assignments |
| `search:{r_hash}:{j_hash}:{w_hash}:{section}` | 1 hour | Hybrid search results |
| `phi4:{prompt_hash}` | 24 hours | LLM completion responses |
| `rag:{r_hash}:{j_hash}` | 2 hours | RAG validation results |
| `reason:{r_hash}:{j_hash}:{w_hash}` | 2 hours | Reasoning engine output |
| `reason_ctx:{output_hash}` | 2 hours | Reasoning context text |
| `explain:{output_hash}` | 24 hours | LLM explanation text |
| `score_history:{jd_id}:{section}` | 24 hours | Historical score distribution |
| `batch:{batch_id}:status` | 1 hour | Batch processing status |

### Redis Connection

```python
# app/db/redis_client.py
redis_client = aioredis.from_url(
    "redis://localhost:6379/0",
    encoding="utf-8",
    decode_responses=True,
    max_connections=50,
)
```

---

## Backup & Maintenance

### Automated Backups

```bash
# Full database dump (including pgvector data)
pg_dump -U raiya -h localhost -d raiya -F c -f raiya_backup_$(date +%Y%m%d).dump

# Restore from dump
pg_restore -U raiya -h localhost -d raiya -c raiya_backup_20260521.dump

# SQL-only dump (portable)
pg_dump -U raiya -h localhost -d raiya --schema-only > raiya_schema.sql
pg_dump -U raiya -h localhost -d raiya --data-only > raiya_data.sql
```

### Maintenance Operations

```sql
-- ── VACUUM (reclaim space, update statistics) ───────────────────
VACUUM ANALYZE match_results;
VACUUM ANALYZE resume_embeddings;
VACUUM ANALYZE jd_embeddings;
VACUUM ANALYZE rag_evidence_embeddings;

-- ── Reindex pgvector IVFFlat indexes ────────────────────────────
-- Required after significant data changes (>20% new rows)
REINDEX INDEX resume_embeddings_embedding_idx;
REINDEX INDEX jd_embeddings_embedding_idx;
REINDEX INDEX rag_evidence_embeddings_embedding_idx;

-- ── Table size monitoring ───────────────────────────────────────
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size,
    pg_size_pretty(pg_relation_size(oid)) AS data_size,
    pg_size_pretty(pg_indexes_size(oid)) AS index_size
FROM pg_class
WHERE relkind = 'r'
  AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ORDER BY pg_total_relation_size(oid) DESC;

-- ── Embedding count per table ───────────────────────────────────
SELECT 'resume_embeddings' AS table_name, COUNT(*) FROM resume_embeddings
UNION ALL
SELECT 'jd_embeddings', COUNT(*) FROM jd_embeddings
UNION ALL
SELECT 'rag_evidence_embeddings', COUNT(*) FROM rag_evidence_embeddings;

-- ── Dead row cleanup ────────────────────────────────────────────
-- Useful after bulk upsert operations (pgvector_client deletes + reinserts)
SELECT schemaname, relname, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

### Data Retention Policies

```sql
-- Delete old token usage logs (>90 days)
DELETE FROM token_usage_log
WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete old hash chain entries (>180 days)
DELETE FROM hash_chain_log
WHERE created_at < NOW() - INTERVAL '180 days';

-- Delete completed pipeline memory entries (>30 days)
DELETE FROM pipeline_memory
WHERE status = 'completed'
  AND completed_at < NOW() - INTERVAL '30 days';

-- Archive old match results (move to archive table)
-- Keep in main table for active batches only
```

---

## Troubleshooting

### Common Issues

**1. pgvector extension not found**
```
ERROR: could not open extension control file ".../vector.control": No such file
```
**Fix**: Install pgvector from source or use the `pgvector/pgvector:pg16` Docker image.

---

**2. Connection pool exhaustion**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached
```
**Fix**: Increase `pool_size` and `max_overflow` in `database.py`, or ensure sessions are properly closed.

---

**3. IVFFlat index returns poor results**
```sql
-- Check if index needs rebuilding (after major data changes)
SELECT * FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%embedding%';

-- Rebuild
REINDEX INDEX CONCURRENTLY resume_embeddings_embedding_idx;

-- Increase probes for better accuracy
SET ivfflat.probes = 20;
```

---

**4. JSONB query performance**
```sql
-- Create GIN index on frequently queried JSONB columns
CREATE INDEX idx_mr_final_result
    ON match_results USING GIN (final_result_json);

-- Query with index support
SELECT * FROM match_results
WHERE final_result_json @> '{"result": {"final_score": 85}}';
```

---

**5. Alembic migration conflicts**
```bash
# Check current migration state
alembic current

# If heads diverge, merge
alembic merge heads -m "merge_migration"

# Force stamp to specific revision (use cautiously)
alembic stamp 003
```

---

**6. Redis connection refused**
```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```
**Fix**: Ensure Redis is running (`docker ps` or `redis-cli ping`). Check `REDIS_URL` in `.env`.

---

### Health Check Queries

```sql
-- Database connectivity
SELECT 1 AS healthy;

-- pgvector extension version
SELECT extversion FROM pg_extension WHERE extname = 'vector';

-- Table row counts
SELECT 'organizations' AS tbl, COUNT(*) FROM organizations
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'job_descriptions', COUNT(*) FROM job_descriptions
UNION ALL SELECT 'resumes', COUNT(*) FROM resumes
UNION ALL SELECT 'batches', COUNT(*) FROM batches
UNION ALL SELECT 'match_results', COUNT(*) FROM match_results
UNION ALL SELECT 'resume_embeddings', COUNT(*) FROM resume_embeddings
UNION ALL SELECT 'jd_embeddings', COUNT(*) FROM jd_embeddings
UNION ALL SELECT 'rag_evidence_embeddings', COUNT(*) FROM rag_evidence_embeddings
UNION ALL SELECT 'interview_invitations', COUNT(*) FROM interview_invitations
UNION ALL SELECT 'pipeline_memory', COUNT(*) FROM pipeline_memory;

-- Active connections
SELECT datname, count(*) FROM pg_stat_activity
WHERE datname = 'raiya' GROUP BY datname;

-- Long-running queries (>5 seconds)
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE datname = 'raiya'
  AND state != 'idle'
  AND now() - pg_stat_activity.query_start > interval '5 seconds';
```

---

*Generated: 2026-05-21 | RAIYA Backend v8.0 | PostgreSQL 16 + pgvector 0.7+*
