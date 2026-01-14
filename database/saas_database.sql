-- ======================================================================================
-- SAAS DATABASE CREATION SCRIPT
-- Combined from PART 1, 2, and 3
-- ======================================================================================

CREATE DATABASE IF NOT EXISTS saas_db;
USE saas_db;

-- ======================================================================================
-- PART 1: CREATE TABLES
-- ======================================================================================

-- ===========================
-- TENANT CORE TABLES
-- ===========================

CREATE TABLE tenants (
    tenant_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_name VARCHAR(255) NOT NULL,
    status ENUM('active','suspended','closed') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- AUTHENTICATION & IDENTITY
-- ===========================

CREATE TABLE global_users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    phone VARCHAR(30),
    profile_data JSON,
    is_verified BOOLEAN DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE user_tenants (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    assigned_roles JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE auth_providers (
    provider_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    provider_uid VARCHAR(255) NOT NULL,
    provider_tokens JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE sessions (
    session_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    jwt_id VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    device_fingerprint VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE mfa_settings (
    user_id BIGINT UNSIGNED PRIMARY KEY,
    totp_secret VARBINARY(512),
    recovery_codes JSON,
    mfa_enabled BOOLEAN DEFAULT FALSE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE password_history (
    history_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- AUTHORIZATION / RBAC / ABAC
-- ===========================

CREATE TABLE permissions (
    permission_key VARCHAR(200) PRIMARY KEY,
    category VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE role_templates (
    template_role_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    default_permissions JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE custom_roles (
    custom_role_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    permissions JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE policy_rules (
    rule_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED,
    expression TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE effective_permissions (
    user_id BIGINT UNSIGNED PRIMARY KEY,
    permissions_cache JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- TENANT LIFECYCLE
-- ===========================

CREATE TABLE tenant_onboarding_jobs (
    onboarding_job_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending','running','completed','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================================
-- PART 2: CREATE TABLES
-- ======================================================================================

-- ===========================
-- SERVICES & PRICING
-- ===========================

CREATE TABLE services (
    service_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service_code VARCHAR(100) NOT NULL UNIQUE,
    service_name VARCHAR(255) NOT NULL,
    service_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tenant_services (
    tenant_service_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    activation_source VARCHAR(100),
    enabled BOOLEAN DEFAULT TRUE,
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE service_access_control (
    access_control_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service_id BIGINT UNSIGNED NOT NULL,
    scope_type ENUM('tenant','bu','dept','role','user') NOT NULL,
    scope_id BIGINT UNSIGNED NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE service_entitlements (
    entitlement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    effective_entitlement JSON,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rate_plans (
    rate_plan_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service_id BIGINT UNSIGNED NOT NULL,
    pricing_type ENUM('fixed','usage','tiered') NOT NULL,
    base_rate DECIMAL(12,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tenant_rate_overrides (
    override_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    rate_plan_id BIGINT UNSIGNED NOT NULL,
    override_rate DECIMAL(12,2) NOT NULL,
    effective_from DATE,
    effective_to DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE business_unit_rates (
    bu_rate_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    rate_modifier DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rate_cards (
    rate_card_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    computed_rate DECIMAL(12,2) NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE service_cost_summary (
    cost_summary_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    billing_period DATE NOT NULL,
    total_cost DECIMAL(12,2) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- BUSINESS UNITS & SHARED RESOURCES
-- ===========================

CREATE TABLE business_units (
    bu_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    bu_name VARCHAR(255) NOT NULL,
    settings_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE departments (
    dept_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    dept_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE projects (
    project_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    dept_id BIGINT UNSIGNED,
    project_name VARCHAR(255) NOT NULL,
    visibility ENUM('private','bu','tenant','public') DEFAULT 'bu',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE bu_users (
    bu_user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    roles JSON,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE job_descriptions (
    jd_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    jd_title VARCHAR(255) NOT NULL,
    jd_data_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE batches (
    batch_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    uploader_user_id BIGINT UNSIGNED,
    status ENUM('pending','processing','completed','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE jobs (
    job_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT UNSIGNED,
    jd_id BIGINT UNSIGNED,
    requester_user_id BIGINT UNSIGNED,
    status ENUM('queued','running','completed','failed') DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE resume_results (
    result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    parsed_resume_json JSON,
    scores_json JSON,
    report_url VARCHAR(500),
    processed_at TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- BILLING & SUBSCRIPTIONS
-- ===========================

CREATE TABLE plan_catalog (
    plan_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(255) NOT NULL,
    features_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE subscriptions (
    subscription_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    plan_id BIGINT UNSIGNED NOT NULL,
    subscription_status ENUM('active','expired','cancelled') DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE credits (
    credit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    balance DECIMAL(12,2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'USD',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE credit_ledger_entries (
    ledger_entry_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    credit_id BIGINT UNSIGNED NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE transactions (
    transaction_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    gateway VARCHAR(100),
    gateway_txn_id VARCHAR(255),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status ENUM('success','failed','pending') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE invoices (
    invoice_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    billing_period DATE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE invoice_line_items (
    line_item_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    invoice_id BIGINT UNSIGNED NOT NULL,
    description VARCHAR(255),
    amount DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE billing_events (
    billing_event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    event_type VARCHAR(100),
    event_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE usage_metering (
    metering_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    usage_count BIGINT UNSIGNED DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- RATE ENGINE LOGS
-- ===========================

CREATE TABLE rate_calculation_engine_logs (
    engine_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED,
    input_json JSON,
    output_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================================
-- PART 3: CREATE TABLES
-- ======================================================================================

-- ===========================
-- JOB SCHEDULING & WORKER ORCHESTRATION
-- ===========================

CREATE TABLE job_queue (
    queue_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_type VARCHAR(100) NOT NULL,
    payload_json JSON,
    status ENUM('queued','processing','completed','failed') DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE worker_pools (
    worker_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    worker_type VARCHAR(100) NOT NULL,
    status ENUM('idle','busy','offline') DEFAULT 'idle',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE job_dispatch (
    dispatch_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    worker_id BIGINT UNSIGNED NOT NULL,
    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE retry_policies (
    retry_policy_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_type VARCHAR(100) NOT NULL,
    max_retries INT DEFAULT 3
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dead_letter_queue (
    dlq_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    reason TEXT,
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scheduled_tasks (
    task_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cron_expression VARCHAR(255) NOT NULL,
    handler_name VARCHAR(255) NOT NULL,
    last_run_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE job_metrics (
    metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    runtime_ms INT,
    memory_used_mb INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- EVENT SYSTEM & WEBHOOKS
-- ===========================

CREATE TABLE events (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(150) NOT NULL,
    payload_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE event_outbox (
    outbox_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(150) NOT NULL,
    payload_json JSON,
    delivery_status ENUM('pending','sent','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tenant_webhooks (
    webhook_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    url VARCHAR(500) NOT NULL,
    subscribed_events JSON,
    secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    channel VARCHAR(100),
    message TEXT,
    status ENUM('pending','sent','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- CACHE / SEARCH / INDEXING
-- ===========================

CREATE TABLE cache_keys (
    cache_key VARCHAR(255) PRIMARY KEY,
    value_json JSON,
    expires_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE search_index_metadata (
    index_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(255) NOT NULL,
    status ENUM('ready','building','failed') DEFAULT 'ready',
    last_synced_at TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE search_sync_jobs (
    sync_job_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    index_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending','running','completed','failed') DEFAULT 'pending',
    started_at TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- STORAGE & FILE METADATA
-- ===========================

CREATE TABLE object_storage_metadata (
    file_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    path VARCHAR(500) NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE presigned_urls (
    url_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    file_id BIGINT UNSIGNED NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    url_token VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE virus_scan_results (
    scan_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    file_id BIGINT UNSIGNED NOT NULL,
    scan_status ENUM('clean','infected','error') DEFAULT 'clean',
    scan_report_json JSON,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE storage_lifecycle_policies (
    rule_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    rule_definition JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- API GATEWAY & THROTTLING
-- ===========================

CREATE TABLE api_keys (
    api_key_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    status ENUM('active','revoked') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rate_limits (
    limit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    api_key_id BIGINT UNSIGNED NOT NULL,
    limit_value INT NOT NULL,
    time_window INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE request_logs (
    request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    api_key_id BIGINT UNSIGNED NOT NULL,
    endpoint VARCHAR(500),
    status_code INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE abuse_detection_logs (
    abuse_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    api_key_id BIGINT UNSIGNED NOT NULL,
    reason TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- OBSERVABILITY / LOGGING / MONITORING
-- ===========================

CREATE TABLE metrics (
    metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED,
    metric_name VARCHAR(200),
    metric_value FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE traces (
    trace_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    span_id BIGINT UNSIGNED,
    parent_span_id BIGINT UNSIGNED,
    trace_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE structured_logs (
    log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED,
    log_level VARCHAR(20),
    message TEXT,
    context_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE health_checks (
    check_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100),
    status ENUM('healthy','warning','critical') DEFAULT 'healthy',
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE incident_alerts (
    alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED,
    severity ENUM('low','medium','high','critical') DEFAULT 'low',
    message TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



-- ===========================
-- BACKUP LAYER
-- ===========================

CREATE TABLE backup_policies (
    policy_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    frequency VARCHAR(50),
    retention INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE database_backups (
    backup_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    backup_location VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE object_storage_backups (
    object_backup_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    location VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tenant_snapshots (
    snapshot_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    snapshot_location VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE bu_snapshots (
    bu_snapshot_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bu_id BIGINT UNSIGNED NOT NULL,
    snapshot_location VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE restore_requests (
    request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    restore_type ENUM('tenant','bu','file','database'),
    status ENUM('pending','running','completed','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE disaster_recovery_metadata (
    dr_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    replication_status VARCHAR(100),
    last_test_time TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================================================================================
-- PART 1: FOREIGN KEY CONSTRAINTS
-- ======================================================================================

-- ===========================
-- FOREIGN KEY CONSTRAINTS
-- ===========================

ALTER TABLE user_tenants
  ADD CONSTRAINT fk_ut_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_ut_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE auth_providers
  ADD CONSTRAINT fk_ap_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE sessions
  ADD CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE mfa_settings
  ADD CONSTRAINT fk_mfa_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE password_history
  ADD CONSTRAINT fk_ph_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE custom_roles
  ADD CONSTRAINT fk_cr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE policy_rules
  ADD CONSTRAINT fk_pr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE effective_permissions
  ADD CONSTRAINT fk_ep_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE tenant_onboarding_jobs
  ADD CONSTRAINT fk_toj_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

-- ======================================================================================
-- PART 2: FOREIGN KEY CONSTRAINTS
-- ======================================================================================

-- SERVICES & PRICING FKs
ALTER TABLE tenant_services
  ADD CONSTRAINT fk_ts_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_ts_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE service_entitlements
  ADD CONSTRAINT fk_se_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_se_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE rate_plans
  ADD CONSTRAINT fk_rp_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE tenant_rate_overrides
  ADD CONSTRAINT fk_tro_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_tro_rateplan FOREIGN KEY (rate_plan_id) REFERENCES rate_plans(rate_plan_id);

ALTER TABLE business_unit_rates
  ADD CONSTRAINT fk_bur_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_bur_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE rate_cards
  ADD CONSTRAINT fk_rc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_rc_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE service_cost_summary
  ADD CONSTRAINT fk_scs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- BUSINESS UNITS & RESOURCES FKs
ALTER TABLE business_units
  ADD CONSTRAINT fk_bu_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE departments
  ADD CONSTRAINT fk_dept_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE projects
  ADD CONSTRAINT fk_proj_dept FOREIGN KEY (dept_id) REFERENCES departments(dept_id);

ALTER TABLE bu_users
  ADD CONSTRAINT fk_buusers_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_buusers_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE job_descriptions
  ADD CONSTRAINT fk_jd_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE batches
  ADD CONSTRAINT fk_batches_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_batches_uploader FOREIGN KEY (uploader_user_id) REFERENCES global_users(user_id);

ALTER TABLE jobs
  ADD CONSTRAINT fk_jobs_batch FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
  ADD CONSTRAINT fk_jobs_jd FOREIGN KEY (jd_id) REFERENCES job_descriptions(jd_id),
  ADD CONSTRAINT fk_jobs_requester FOREIGN KEY (requester_user_id) REFERENCES global_users(user_id);

ALTER TABLE resume_results
  ADD CONSTRAINT fk_rr_job FOREIGN KEY (job_id) REFERENCES jobs(job_id);


-- BILLING & SUBSCRIPTIONS FKs
ALTER TABLE subscriptions
  ADD CONSTRAINT fk_sub_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_sub_plan FOREIGN KEY (plan_id) REFERENCES plan_catalog(plan_id);

ALTER TABLE credits
  ADD CONSTRAINT fk_credits_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE credit_ledger_entries
  ADD CONSTRAINT fk_ledger_credit FOREIGN KEY (credit_id) REFERENCES credits(credit_id);

ALTER TABLE transactions
  ADD CONSTRAINT fk_txn_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE invoices
  ADD CONSTRAINT fk_inv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE invoice_line_items
  ADD CONSTRAINT fk_line_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id);

ALTER TABLE billing_events
  ADD CONSTRAINT fk_be_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE usage_metering
  ADD CONSTRAINT fk_usage_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_usage_service FOREIGN KEY (service_id) REFERENCES services(service_id);

-- ======================================================================================
-- PART 3: FOREIGN KEY CONSTRAINTS
-- ======================================================================================

-- JOB SYSTEM FKs
ALTER TABLE job_dispatch
  ADD CONSTRAINT fk_jd_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id),
  ADD CONSTRAINT fk_jd_worker FOREIGN KEY (worker_id) REFERENCES worker_pools(worker_id);

ALTER TABLE dead_letter_queue
  ADD CONSTRAINT fk_dlq_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id);

ALTER TABLE job_metrics
  ADD CONSTRAINT fk_jm_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id);


-- EVENT SYSTEM FKs
ALTER TABLE tenant_webhooks
  ADD CONSTRAINT fk_tw_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE notifications
  ADD CONSTRAINT fk_notif_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- SEARCH INDEXING FKs
ALTER TABLE search_sync_jobs
  ADD CONSTRAINT fk_ssj_idx FOREIGN KEY (index_id) REFERENCES search_index_metadata(index_id);


-- STORAGE METADATA FKs
ALTER TABLE object_storage_metadata
  ADD CONSTRAINT fk_osm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE presigned_urls
  ADD CONSTRAINT fk_pu_file FOREIGN KEY (file_id) REFERENCES object_storage_metadata(file_id);

ALTER TABLE virus_scan_results
  ADD CONSTRAINT fk_vsr_file FOREIGN KEY (file_id) REFERENCES object_storage_metadata(file_id);


-- STORAGE LIFECYCLE
ALTER TABLE storage_lifecycle_policies
  ADD CONSTRAINT fk_slp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- API GATEWAY FKs
ALTER TABLE api_keys
  ADD CONSTRAINT fk_apikeys_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE rate_limits
  ADD CONSTRAINT fk_rl_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);

ALTER TABLE request_logs
  ADD CONSTRAINT fk_rl_log_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);

ALTER TABLE abuse_detection_logs
  ADD CONSTRAINT fk_adl_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);


-- OBSERVABILITY FKs
ALTER TABLE metrics
  ADD CONSTRAINT fk_metrics_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE structured_logs
  ADD CONSTRAINT fk_logs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE incident_alerts
  ADD CONSTRAINT fk_incident_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- BACKUP LAYER FKs
ALTER TABLE backup_policies
  ADD CONSTRAINT fk_bp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE database_backups
  ADD CONSTRAINT fk_db_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE object_storage_backups
  ADD CONSTRAINT fk_osb_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE tenant_snapshots
  ADD CONSTRAINT fk_tsnap_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE bu_snapshots
  ADD CONSTRAINT fk_busnap_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE restore_requests
  ADD CONSTRAINT fk_rr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE disaster_recovery_metadata
  ADD CONSTRAINT fk_drm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);
-- ======================================================================================
-- PART 4: MISSING SECTIONS (EXTENSIBILITY, SCHEMA, SANDBOX, PRIVACY, FINOPS)
-- ======================================================================================

-- ===========================
-- EXTENSIBILITY CONTRACT LAYER
-- ===========================

CREATE TABLE entity_metadata (
    metadata_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    entity_type VARCHAR(100) NOT NULL, -- e.g., 'user', 'job', 'department'
    entity_id BIGINT UNSIGNED NOT NULL,
    meta_key VARCHAR(255) NOT NULL,
    meta_value JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE custom_field_definitions (
    field_def_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    field_type ENUM('text', 'number', 'date', 'boolean', 'json', 'dropdown') NOT NULL,
    validation_rules JSON,
    is_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_field_name (tenant_id, entity_type, field_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE custom_field_values (
    value_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    field_def_id BIGINT UNSIGNED NOT NULL,
    entity_id BIGINT UNSIGNED NOT NULL,
    field_value TEXT, -- Storing as text, can be cast based on type
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE custom_object_definitions (
    object_def_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    object_name VARCHAR(255) NOT NULL,
    schema_definition JSON NOT NULL,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_object_name (tenant_id, object_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE custom_object_records (
    record_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    object_def_id BIGINT UNSIGNED NOT NULL,
    tenant_id BIGINT UNSIGNED NOT NULL,
    record_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE event_schemas (
    schema_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(150) NOT NULL,
    schema_version INT NOT NULL,
    schema_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_event_version (event_type, schema_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- SCHEMA MANAGEMENT & MIGRATIONS
-- ===========================

CREATE TABLE migration_history (
    migration_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failed') DEFAULT 'success'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE schema_drift_logs (
    log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    drift_details JSON,
    status ENUM('detected', 'resolved', 'ignored') DEFAULT 'detected'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- SANDBOX / STAGING PER TENANT
-- ===========================

CREATE TABLE sandbox_environments (
    sandbox_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    sandbox_name VARCHAR(255) NOT NULL,
    status ENUM('provisioning', 'active', 'expired', 'deleted') DEFAULT 'provisioning',
    expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE data_copy_jobs (
    job_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_tenant_id BIGINT UNSIGNED NOT NULL,
    target_sandbox_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    config_json JSON, -- e.g., masking rules to apply
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- DATA MASKING & PRIVACY
-- ===========================

CREATE TABLE pii_classification_registry (
    classification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    field_name VARCHAR(255) NOT NULL, -- e.g., 'email', 'ssn'
    sensitivity_level ENUM('public', 'internal', 'confidential', 'restricted') DEFAULT 'internal',
    masking_type ENUM('none', 'partial', 'full', 'hash') DEFAULT 'none'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE masking_policies (
    policy_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED, -- Null means applies to all unless overridden
    policy_definition JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- FINOPS & COST ANALYTICS
-- ===========================

CREATE TABLE cost_forecasts (
    forecast_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    forecast_period_start DATE NOT NULL,
    forecast_period_end DATE NOT NULL,
    predicted_cost DECIMAL(12, 2),
    confidence_score DECIMAL(5, 2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE budget_alerts (
    alert_config_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    period ENUM('monthly', 'quarterly', 'yearly') DEFAULT 'monthly',
    budget_limit DECIMAL(12, 2) NOT NULL,
    alert_threshold_percent INT DEFAULT 80,
    notification_channels JSON, -- e.g., list of emails or webhooks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ===========================
-- FOREIGN KEY CONSTRAINTS FOR NEW TABLES
-- ======================================================================================

ALTER TABLE entity_metadata
  ADD CONSTRAINT fk_em_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE custom_field_definitions
  ADD CONSTRAINT fk_cfd_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE custom_field_values
  ADD CONSTRAINT fk_cfv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_cfv_def FOREIGN KEY (field_def_id) REFERENCES custom_field_definitions(field_def_id);

ALTER TABLE custom_object_definitions
  ADD CONSTRAINT fk_cod_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE custom_object_records
  ADD CONSTRAINT fk_cor_def FOREIGN KEY (object_def_id) REFERENCES custom_object_definitions(object_def_id),
  ADD CONSTRAINT fk_cor_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE schema_drift_logs
  ADD CONSTRAINT fk_sdl_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE sandbox_environments
  ADD CONSTRAINT fk_sb_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE data_copy_jobs
  ADD CONSTRAINT fk_dcj_source FOREIGN KEY (source_tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_dcj_sandbox FOREIGN KEY (target_sandbox_id) REFERENCES sandbox_environments(sandbox_id);

ALTER TABLE masking_policies
  ADD CONSTRAINT fk_mp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE cost_forecasts
  ADD CONSTRAINT fk_cf_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE budget_alerts
  ADD CONSTRAINT fk_ba_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);
