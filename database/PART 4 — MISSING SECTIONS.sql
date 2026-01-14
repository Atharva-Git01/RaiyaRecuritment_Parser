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
