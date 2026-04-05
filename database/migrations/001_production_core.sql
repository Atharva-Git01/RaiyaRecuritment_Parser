CREATE TABLE IF NOT EXISTS tenants (
    tenant_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_name VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS global_users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    phone VARCHAR(30),
    full_name VARCHAR(255),
    password_hash VARCHAR(512),
    profile_data JSON,
    status VARCHAR(64) DEFAULT 'active',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_tenants (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    assigned_roles JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    tenant_id BIGINT UNSIGNED NOT NULL,
    jwt_id VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    expires_at DATETIME NOT NULL,
    device_fingerprint VARCHAR(255),
    revoked_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_templates (
    template_role_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    default_permissions JSON
);

CREATE TABLE IF NOT EXISTS services (
    service_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service_code VARCHAR(100) NOT NULL UNIQUE,
    service_name VARCHAR(255) NOT NULL,
    service_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_entitlements (
    entitlement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    effective_entitlement JSON,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_units (
    bu_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    bu_name VARCHAR(255) NOT NULL,
    settings_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_descriptions (
    jd_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    jd_title VARCHAR(255) NOT NULL,
    jd_data_json JSON,
    source_object_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS batches (
    batch_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    uploader_user_id BIGINT UNSIGNED,
    status VARCHAR(64) NOT NULL DEFAULT 'received',
    batch_guid VARCHAR(64),
    job_description_id BIGINT UNSIGNED NULL,
    idempotency_key VARCHAR(255) NULL,
    submitted_count INT NOT NULL DEFAULT 0,
    completed_count INT NOT NULL DEFAULT 0,
    failed_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT UNSIGNED,
    jd_id BIGINT UNSIGNED,
    requester_user_id BIGINT UNSIGNED,
    resume_filename VARCHAR(255) NULL,
    resume_file_id BIGINT UNSIGNED NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'received',
    stage VARCHAR(64) NOT NULL DEFAULT 'received',
    progress INT NOT NULL DEFAULT 0,
    attempts INT NOT NULL DEFAULT 0,
    idempotency_key VARCHAR(255) NULL,
    scan_status VARCHAR(64) NOT NULL DEFAULT 'pending',
    warnings_json JSON NULL,
    last_error TEXT NULL,
    worker_id VARCHAR(255) NULL,
    started_at DATETIME NULL,
    heartbeat_at DATETIME NULL,
    available_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS object_storage_metadata (
    object_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    batch_id BIGINT UNSIGNED NULL,
    job_id BIGINT UNSIGNED NULL,
    purpose VARCHAR(100) NOT NULL,
    backend VARCHAR(100) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    content_type VARCHAR(200),
    size_bytes BIGINT UNSIGNED DEFAULT 0,
    checksum_sha256 VARCHAR(128),
    created_by_user_id BIGINT UNSIGNED NULL,
    quarantine_flag BOOLEAN DEFAULT FALSE,
    metadata_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resume_results (
    result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    batch_id BIGINT UNSIGNED NULL,
    tenant_id BIGINT UNSIGNED NULL,
    parsed_resume_json JSON,
    validated_resume_json JSON,
    scores_json JSON,
    local_score_json JSON,
    ai_score_json JSON,
    rag_audit_json JSON,
    explanation_json JSON,
    structured_explanation_json JSON,
    warnings_json JSON,
    result_status VARCHAR(64) DEFAULT 'completed',
    result_stage VARCHAR(64) DEFAULT 'completed',
    report_url VARCHAR(500),
    report_object_id BIGINT UNSIGNED NULL,
    processed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rate_limits (
    rate_limit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    scope_key VARCHAR(100) NOT NULL,
    subject_key VARCHAR(255) NOT NULL,
    limit_count INT NOT NULL,
    request_count INT NOT NULL DEFAULT 0,
    window_started_at DATETIME NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS request_logs (
    request_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NULL,
    user_id BIGINT UNSIGNED NULL,
    request_id VARCHAR(100) NOT NULL,
    method VARCHAR(20) NOT NULL,
    path VARCHAR(500) NOT NULL,
    status_code INT NOT NULL,
    duration_ms DECIMAL(12,2) NOT NULL,
    ip_address VARCHAR(100) NULL,
    user_agent VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NULL,
    actor_user_id BIGINT UNSIGNED NULL,
    event_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(100) NULL,
    target_id VARCHAR(255) NULL,
    payload_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tenant_domains (
    tenant_domain_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tenant_oidc_configs (
    oidc_config_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    discovery_url VARCHAR(500) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    client_secret VARCHAR(500) NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scopes VARCHAR(500) NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS virus_scan_results (
    virus_scan_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    object_id BIGINT UNSIGNED NOT NULL,
    engine VARCHAR(100) NOT NULL,
    status VARCHAR(64) NOT NULL,
    details_json JSON NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dead_letter_queue (
    dlq_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    reason TEXT,
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE global_users MODIFY COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE global_users ADD COLUMN full_name VARCHAR(255) NULL;
ALTER TABLE global_users ADD COLUMN password_hash VARCHAR(512) NULL;
ALTER TABLE global_users ADD COLUMN status VARCHAR(64) DEFAULT 'active';
ALTER TABLE global_users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE global_users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE user_tenants ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE sessions ADD COLUMN tenant_id BIGINT UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE sessions ADD COLUMN refresh_token_hash VARCHAR(255) NULL;
ALTER TABLE sessions ADD COLUMN revoked_at DATETIME NULL;
ALTER TABLE sessions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE sessions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE business_units ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE job_descriptions ADD COLUMN source_object_id BIGINT UNSIGNED NULL;
ALTER TABLE job_descriptions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE batches MODIFY COLUMN status VARCHAR(64) NOT NULL DEFAULT 'received';
ALTER TABLE batches ADD COLUMN batch_guid VARCHAR(64) NULL;
ALTER TABLE batches ADD COLUMN job_description_id BIGINT UNSIGNED NULL;
ALTER TABLE batches ADD COLUMN idempotency_key VARCHAR(255) NULL;
ALTER TABLE batches ADD COLUMN submitted_count INT NOT NULL DEFAULT 0;
ALTER TABLE batches ADD COLUMN completed_count INT NOT NULL DEFAULT 0;
ALTER TABLE batches ADD COLUMN failed_count INT NOT NULL DEFAULT 0;
ALTER TABLE batches ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE jobs MODIFY COLUMN status VARCHAR(64) NOT NULL DEFAULT 'received';
ALTER TABLE jobs ADD COLUMN resume_filename VARCHAR(255) NULL;
ALTER TABLE jobs ADD COLUMN resume_file_id BIGINT UNSIGNED NULL;
ALTER TABLE jobs ADD COLUMN stage VARCHAR(64) NOT NULL DEFAULT 'received';
ALTER TABLE jobs ADD COLUMN progress INT NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN attempts INT NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN idempotency_key VARCHAR(255) NULL;
ALTER TABLE jobs ADD COLUMN scan_status VARCHAR(64) NOT NULL DEFAULT 'pending';
ALTER TABLE jobs ADD COLUMN warnings_json JSON NULL;
ALTER TABLE jobs ADD COLUMN last_error TEXT NULL;
ALTER TABLE jobs ADD COLUMN worker_id VARCHAR(255) NULL;
ALTER TABLE jobs ADD COLUMN started_at DATETIME NULL;
ALTER TABLE jobs ADD COLUMN heartbeat_at DATETIME NULL;
ALTER TABLE jobs ADD COLUMN available_at DATETIME NULL;
ALTER TABLE jobs ADD COLUMN completed_at DATETIME NULL;
ALTER TABLE jobs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE object_storage_metadata CHANGE COLUMN file_id object_id BIGINT UNSIGNED AUTO_INCREMENT;
ALTER TABLE object_storage_metadata CHANGE COLUMN path object_key VARCHAR(500) NOT NULL;
ALTER TABLE object_storage_metadata ADD COLUMN batch_id BIGINT UNSIGNED NULL;
ALTER TABLE object_storage_metadata ADD COLUMN job_id BIGINT UNSIGNED NULL;
ALTER TABLE object_storage_metadata ADD COLUMN purpose VARCHAR(100) NOT NULL DEFAULT 'generic';
ALTER TABLE object_storage_metadata ADD COLUMN backend VARCHAR(100) NOT NULL DEFAULT 'local';
ALTER TABLE object_storage_metadata ADD COLUMN original_filename VARCHAR(255) NULL;
ALTER TABLE object_storage_metadata ADD COLUMN content_type VARCHAR(200) NULL;
ALTER TABLE object_storage_metadata ADD COLUMN size_bytes BIGINT UNSIGNED DEFAULT 0;
ALTER TABLE object_storage_metadata ADD COLUMN checksum_sha256 VARCHAR(128) NULL;
ALTER TABLE object_storage_metadata ADD COLUMN created_by_user_id BIGINT UNSIGNED NULL;
ALTER TABLE object_storage_metadata ADD COLUMN quarantine_flag BOOLEAN DEFAULT FALSE;
ALTER TABLE object_storage_metadata ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE resume_results ADD COLUMN batch_id BIGINT UNSIGNED NULL;
ALTER TABLE resume_results ADD COLUMN tenant_id BIGINT UNSIGNED NULL;
ALTER TABLE resume_results ADD COLUMN validated_resume_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN local_score_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN ai_score_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN rag_audit_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN explanation_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN structured_explanation_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN warnings_json JSON NULL;
ALTER TABLE resume_results ADD COLUMN result_status VARCHAR(64) DEFAULT 'completed';
ALTER TABLE resume_results ADD COLUMN result_stage VARCHAR(64) DEFAULT 'completed';
ALTER TABLE resume_results ADD COLUMN report_object_id BIGINT UNSIGNED NULL;
ALTER TABLE resume_results ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE resume_results ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
