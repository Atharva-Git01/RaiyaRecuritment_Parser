CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    plan_id BIGINT UNSIGNED NULL,
    subscription_status VARCHAR(64) NOT NULL DEFAULT 'active',
    stripe_customer_id VARCHAR(255) NULL,
    stripe_subscription_id VARCHAR(255) NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    current_period_start DATETIME NULL,
    current_period_end DATETIME NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    billing_period DATE NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    invoice_status VARCHAR(64) DEFAULT 'issued',
    stripe_invoice_id VARCHAR(255) NULL,
    pdf_url VARCHAR(500) NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_events (
    billing_event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    event_type VARCHAR(100),
    event_data JSON,
    external_event_id VARCHAR(255) NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_events (
    usage_event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    batch_id BIGINT UNSIGNED NOT NULL,
    job_id BIGINT UNSIGNED NOT NULL,
    meter_type VARCHAR(100) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    details_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS billing_sync_runs (
    billing_sync_run_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NULL,
    provider VARCHAR(100) NOT NULL,
    sync_type VARCHAR(100) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    details_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
);

ALTER TABLE subscriptions MODIFY COLUMN subscription_status VARCHAR(64) NOT NULL DEFAULT 'active';
ALTER TABLE subscriptions MODIFY COLUMN plan_id BIGINT UNSIGNED NULL;
ALTER TABLE subscriptions ADD COLUMN stripe_customer_id VARCHAR(255) NULL;
ALTER TABLE subscriptions ADD COLUMN stripe_subscription_id VARCHAR(255) NULL;
ALTER TABLE subscriptions ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE subscriptions ADD COLUMN current_period_start DATETIME NULL;
ALTER TABLE subscriptions ADD COLUMN current_period_end DATETIME NULL;
ALTER TABLE subscriptions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE invoices ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE invoices ADD COLUMN invoice_status VARCHAR(64) DEFAULT 'issued';
ALTER TABLE invoices ADD COLUMN stripe_invoice_id VARCHAR(255) NULL;
ALTER TABLE invoices ADD COLUMN pdf_url VARCHAR(500) NULL;
ALTER TABLE invoices ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE billing_events ADD COLUMN external_event_id VARCHAR(255) NULL;
