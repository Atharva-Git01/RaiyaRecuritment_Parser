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
