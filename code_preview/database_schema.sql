-- Enable UUID extension if needed (Postgres 13+ has gen_random_uuid() built-in)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 1. Multi-tenant Foundation
-- ==========================================

CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    billing_plan VARCHAR(64),
    contact_email VARCHAR(255),
    settings JSONB, -- feature flags, default weightages
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_created_at ON tenants(created_at);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(32), -- owner|admin|recruiter|viewer|worker
    password_hash VARCHAR(1024),
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ,
    metadata JSONB,
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant_role ON users(tenant_id, role);
CREATE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- ==========================================
-- 2. Job Description & JD Versions
-- ==========================================

CREATE TABLE job_descriptions (
    jd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    created_by UUID REFERENCES users(user_id),
    title VARCHAR(512),
    description TEXT,
    raw_text_path TEXT, -- object store pointer
    normalized_json_path TEXT,
    parameters JSONB, -- {min_exp, mandatory_skills[], locations[], salary_range, qualification}
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_jds_tenant_created ON job_descriptions(tenant_id, created_at);
CREATE INDEX idx_jds_parameters ON job_descriptions USING GIN (parameters);

CREATE TABLE jd_versions (
    jd_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_id UUID NOT NULL REFERENCES job_descriptions(jd_id),
    version_number INT,
    normalized_json_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE jd_skills (
    jd_skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_id UUID NOT NULL REFERENCES job_descriptions(jd_id),
    name VARCHAR(255),
    required BOOLEAN DEFAULT false,
    weight FLOAT DEFAULT 1
);

CREATE INDEX idx_jd_skills_jd_id ON jd_skills(jd_id);

-- ==========================================
-- 3. Batch & File Processing
-- ==========================================

CREATE TYPE batch_status AS ENUM ('created', 'processing', 'completed', 'failed', 'cancelled');

CREATE TABLE batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    jd_id UUID REFERENCES job_descriptions(jd_id), -- nullable if multiple-JD flows
    created_by UUID REFERENCES users(user_id),
    name VARCHAR(255),
    status batch_status DEFAULT 'created',
    total_files INT DEFAULT 0,
    processed_files INT DEFAULT 0,
    results_json_path TEXT, -- object store pointer
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_batches_tenant_status ON batches(tenant_id, status);
CREATE INDEX idx_batches_jd_id ON batches(jd_id);

CREATE TABLE files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    batch_id UUID REFERENCES batches(batch_id),
    uploader_id UUID REFERENCES users(user_id),
    original_filename VARCHAR(1024),
    storage_path TEXT, -- S3/MinIO pointer
    sha256 CHAR(64), -- dedupe
    mime_type VARCHAR(80),
    size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    parsed_preview TEXT, -- small cached text
    is_deleted BOOLEAN DEFAULT false
);

CREATE INDEX idx_files_tenant_sha256 ON files(tenant_id, sha256);
CREATE INDEX idx_files_batch_id ON files(batch_id);
CREATE INDEX idx_files_uploaded_at ON files(uploaded_at);

-- ==========================================
-- 4. Pipeline Execution & Fault Tolerance
-- ==========================================

CREATE TABLE workers (
    worker_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255),
    version VARCHAR(64),
    tenant_id UUID, -- NULLABLE (if worker bound to tenant)
    status VARCHAR(32), -- idle, busy, offline
    last_seen TIMESTAMPTZ,
    metrics JSONB
);

CREATE TABLE worker_heartbeats (
    id BIGSERIAL PRIMARY KEY,
    worker_id UUID NOT NULL REFERENCES workers(worker_id),
    last_seen TIMESTAMPTZ,
    jobs_processed INT,
    metrics JSONB
);

CREATE INDEX idx_worker_heartbeats_last_seen ON worker_heartbeats(last_seen);

CREATE TYPE job_status AS ENUM ('queued', 'in_progress', 'failed', 'completed', 'cancelled');

CREATE TABLE jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    batch_id UUID REFERENCES batches(batch_id),
    file_id UUID NOT NULL REFERENCES files(file_id),
    resume_id UUID, -- FK added later
    status job_status DEFAULT 'queued',
    progress INT DEFAULT 0,
    last_step VARCHAR(64),
    attempts INT DEFAULT 0,
    worker_id UUID REFERENCES workers(worker_id),
    error_message TEXT,
    queued_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    lock_token UUID -- optional optimistic locking token
);

CREATE INDEX idx_jobs_status_queued_at ON jobs(status, queued_at);
CREATE INDEX idx_jobs_worker_status ON jobs(worker_id, status);
CREATE INDEX idx_jobs_tenant_id ON jobs(tenant_id);

CREATE TABLE checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    step_name VARCHAR(64), -- 'extraction','parsing','validation','scoring','report'
    payload_path TEXT, -- pointer to artifact (JSON in object store)
    payload_hash CHAR(64),
    meta JSONB, -- timings, duration, worker notes
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_checkpoints_job_step ON checkpoints(job_id, step_name);

-- ==========================================
-- 5. Resume / Candidate Model (Normalized)
-- ==========================================

CREATE TYPE resume_status AS ENUM ('raw', 'parsed', 'validated', 'scored');

CREATE TABLE resumes (
    resume_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    file_id UUID NOT NULL REFERENCES files(file_id),
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(64),
    location VARCHAR(255),
    current_designation VARCHAR(255),
    raw_text_path TEXT, -- pointer to extracted text
    normalized_text_path TEXT,
    parsed_json_path TEXT, -- AI parser output (raw)
    validated_json_path TEXT, -- validator normalized JSON
    status resume_status DEFAULT 'raw',
    last_parsed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_resumes_tenant_email ON resumes(tenant_id, email);
-- CREATE INDEX idx_resumes_parsed_json ON resumes USING GIN (parsed_json_path); -- If storing JSONB

-- Update jobs with resume_id FK
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_resume FOREIGN KEY (resume_id) REFERENCES resumes(resume_id);

CREATE TABLE employers (
    employer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(512) UNIQUE, -- canonical
    aliases JSONB,
    website VARCHAR(1024)
);

CREATE TABLE resume_experiences (
    resume_exp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(resume_id),
    employer_id UUID REFERENCES employers(employer_id), -- if canonicalized
    company VARCHAR(512),
    role VARCHAR(512),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE,
    description TEXT,
    location VARCHAR(255),
    months_experience INT, -- computed
    order_index INT
);

CREATE INDEX idx_resume_exp_resume_id ON resume_experiences(resume_id);
-- Full text indexes can be added here

CREATE TABLE resume_projects (
    resume_project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(resume_id),
    name VARCHAR(512),
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE resume_project_technologies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_project_id UUID NOT NULL REFERENCES resume_projects(resume_project_id),
    technology VARCHAR(255)
);

CREATE TABLE resume_skills (
    resume_skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(resume_id),
    skill_name VARCHAR(255), -- canonicalized
    skill_type VARCHAR(32), -- skill|tool|technology|soft
    source VARCHAR(64), -- 'parser','llm','fallback_regex'
    confidence FLOAT
);

CREATE INDEX idx_resume_skills_resume_id ON resume_skills(resume_id);
CREATE INDEX idx_resume_skills_name ON resume_skills(skill_name);

CREATE TABLE resume_education (
    resume_edu_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(resume_id),
    degree VARCHAR(255),
    institution VARCHAR(255),
    year_start INT,
    year_end INT,
    major VARCHAR(255),
    grade VARCHAR(64)
);

CREATE TABLE resume_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(resume_id),
    contact_type VARCHAR(32), -- linkedin, github, email, phone, website, other
    value VARCHAR(1024)
);

-- ==========================================
-- 6. Scoring & AI Evaluation
-- ==========================================

CREATE TABLE local_match_scores (
    local_score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    job_id UUID,
    resume_id UUID REFERENCES resumes(resume_id),
    jd_id UUID REFERENCES job_descriptions(jd_id),
    scores JSONB, -- {skills: 0-100, experience: 0-100, ...}
    final_score INT,
    breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_local_scores_scores ON local_match_scores USING GIN (scores);

CREATE TABLE ai_scores (
    ai_score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    job_id UUID,
    resume_id UUID REFERENCES resumes(resume_id),
    jd_id UUID REFERENCES job_descriptions(jd_id),
    ai_ok BOOLEAN,
    ai_raw_response_path TEXT, -- pointer to raw response JSON in object store
    ai_score_json_path TEXT, -- canonical LLM output JSON (stored)
    final_score INT,
    notes VARCHAR(240),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE score_resolutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID REFERENCES resumes(resume_id),
    job_id UUID REFERENCES jobs(job_id),
    local_score_id UUID REFERENCES local_match_scores(local_score_id),
    ai_score_id UUID REFERENCES ai_scores(ai_score_id),
    resolved_score INT,
    policy VARCHAR(32), -- ai_prefer, local_fallback, weighted_avg
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE weightage_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    name VARCHAR(255),
    weights JSONB, -- used by scoring engine & UI
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ==========================================
-- 7. Results, Reporting & Exports
-- ==========================================

CREATE TABLE results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    batch_id UUID REFERENCES batches(batch_id),
    job_id UUID REFERENCES jobs(job_id),
    resume_id UUID REFERENCES resumes(resume_id),
    jd_id UUID REFERENCES job_descriptions(jd_id),
    local_score_id UUID REFERENCES local_match_scores(local_score_id),
    ai_score_id UUID REFERENCES ai_scores(ai_score_id),
    final_score INT,
    summary TEXT, -- recruiter-facing
    result_json_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    batch_id UUID REFERENCES batches(batch_id),
    report_type VARCHAR(32), -- pdf, excel, csv, json
    storage_path TEXT,
    generated_by UUID REFERENCES users(user_id),
    generated_at TIMESTAMPTZ DEFAULT now(),
    meta JSONB -- filters, topK, JD used
);

-- ==========================================
-- 8. Audit & Monitoring
-- ==========================================

CREATE TABLE audit_logs (
    audit_id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(tenant_id),
    user_id UUID REFERENCES users(user_id),
    object_type VARCHAR(64),
    object_id UUID,
    action VARCHAR(64), -- CREATE, UPDATE, DELETE, EXPORT, AI_REQUEST, READ
    details JSONB,
    ip_address VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE error_logs (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    job_id UUID REFERENCES jobs(job_id),
    file_id UUID REFERENCES files(file_id),
    error_type VARCHAR(128),
    message TEXT,
    traceback TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE storage_objects (
    object_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(tenant_id),
    path TEXT,
    object_type VARCHAR(64), -- resume_text, parsed_json, pdf_report, ai_response
    size_bytes BIGINT,
    checksum CHAR(64),
    created_at TIMESTAMPTZ DEFAULT now()
);
