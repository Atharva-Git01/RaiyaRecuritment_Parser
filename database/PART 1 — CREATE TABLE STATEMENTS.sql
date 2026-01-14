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
