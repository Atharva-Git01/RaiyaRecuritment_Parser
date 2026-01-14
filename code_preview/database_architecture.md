# Deep Relational Database Architecture

This document outlines a professional, production-ready relational database architecture for the Resume Parser & Orchestrator pipeline. It is designed to support multi-tenancy, batch processing, detailed resume parsing, AI scoring, and comprehensive reporting.

## 1. High-Level Entity Groups

The architecture is organized into the following logical groups:

*   **Multi-tenant Foundation**: `tenants`, `users`, `roles`, `user_permissions`.
*   **Job Description Management**: `job_descriptions`, `jd_versions`, `jd_skills`, `jd_requirements`.
*   **Batch & File Ingestion**: `batches`, `files`, `storage_objects`.
*   **Pipeline Execution**: `jobs`, `checkpoints`, `workers`, `worker_heartbeats`.
*   **Candidate Model (Resume)**: `resumes`, `resume_experiences`, `resume_projects`, `resume_technologies`, `resume_skills`, `resume_education`, `resume_contacts`.
*   **Employer Canonicalization**: `employers`, `employer_projects`, `employer_departments`, `employer_roles`.
*   **Scoring & Evaluation**: `local_match_scores`, `ai_scores`, `score_resolutions`, `weightage_profiles`.
*   **Results & Reporting**: `results`, `reports`, `report_rows`.
*   **Audit & Monitoring**: `audit_logs`, `error_logs`.

## 2. Schema Design

### 2.1 Multi-tenant Foundation

**`tenants`**
*   `tenant_id` (UUID, PK): Unique identifier.
*   `name` (VARCHAR): Tenant name.
*   `slug` (VARCHAR): URL-friendly identifier.
*   `settings` (JSONB): Feature flags, defaults.

**`users`**
*   `user_id` (UUID, PK)
*   `tenant_id` (UUID, FK): Multi-tenancy scope.
*   `email` (VARCHAR): Unique per tenant.
*   `role` (VARCHAR): RBAC role (owner, admin, recruiter, viewer).

### 2.2 Job Description Management

**`job_descriptions`**
*   `jd_id` (UUID, PK)
*   `parameters` (JSONB): Structured criteria (skills, exp, salary).
*   `raw_text_path` (TEXT): Pointer to source file.

**`jd_versions`**
*   Tracks history of JD changes for audit and rollback.

### 2.3 Batch & File Processing

**`batches`**
*   `batch_id` (UUID, PK)
*   `status` (ENUM): Lifecycle state (created, processing, completed).
*   `total_files`, `processed_files`: Progress tracking.

**`files`**
*   `file_id` (UUID, PK)
*   `storage_path` (TEXT): Object store location (S3/MinIO).
*   `sha256` (CHAR): Deduplication hash.

### 2.4 Pipeline Execution

**`jobs`**
*   `job_id` (UUID, PK)
*   `status` (ENUM): queued, in_progress, completed, failed.
*   `worker_id` (UUID, FK): Claimed by worker.
*   `lock_token` (UUID): Optimistic locking for idempotency.

**`checkpoints`**
*   Stores intermediate state (`payload_path`) after each pipeline step (extract, parse, validate, score) to enable resume/replay.

### 2.5 Resume / Candidate Model

**`resumes`**
*   `resume_id` (UUID, PK)
*   `parsed_json_path` (TEXT): Pointer to full AI output.
*   `status` (ENUM): raw, parsed, validated, scored.

**Normalized Tables**: `resume_experiences`, `resume_skills`, `resume_education`, `resume_projects` store structured data for SQL querying and filtering.

### 2.6 Scoring & AI Evaluation

**`local_match_scores`**
*   Deterministic scoring based on keyword/regex matching.

**`ai_scores`**
*   `ai_score_json_path` (TEXT): Canonical LLM output.
*   `ai_raw_response_path` (TEXT): Audit trail of raw LLM response.

**`weightage_profiles`**
*   Configurable weights for scoring components (skills vs experience).

## 3. Operational Considerations

*   **Job Claiming**: Workers use atomic updates (`UPDATE ... WHERE status='queued'`) to claim jobs.
*   **Checkpointing**: State is saved to object store and referenced in `checkpoints` table after every step.
*   **Idempotency**: File SHA256 prevents duplicate processing; Job lock tokens prevent double execution.
*   **Storage**: Heavy artifacts (PDFs, JSON blobs) live in Object Store; DB holds pointers and metadata.

## 4. Security & Compliance

*   **PII**: Sensitive fields (email, phone) should be encrypted at rest.
*   **Audit**: All access to `resumes` or `reports` is logged in `audit_logs`.
*   **Retention**: `is_deleted` flags and background GC policies for data lifecycle management.

## 5. Performance

*   **Partitioning**: `jobs`, `audit_logs`, `files` partitioned by time (monthly) or `tenant_id`.
*   **Indexing**: GIN indexes on `JSONB` columns (`parameters`, `scores`) for fast search.
