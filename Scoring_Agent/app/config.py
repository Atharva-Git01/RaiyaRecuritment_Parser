from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _csv(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv('APP_NAME', 'raiya-resume-core')
    app_env: str = os.getenv('APP_ENV', 'development')
    app_secret_key: str = os.getenv('APP_SECRET_KEY', '')
    app_base_url: str = os.getenv('APP_BASE_URL', 'http://localhost:8000')
    access_token_minutes: int = int(os.getenv('ACCESS_TOKEN_MINUTES', '60'))
    refresh_token_days: int = int(os.getenv('REFRESH_TOKEN_DAYS', '14'))
    cors_origins: List[str] = field(default_factory=lambda: _csv('CORS_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000'))
    cookie_secure: bool = _bool('COOKIE_SECURE', False)
    storage_backend: str = os.getenv('STORAGE_BACKEND', 'local')
    queue_backend: str = os.getenv('QUEUE_BACKEND', 'database')
    scan_backend: str = os.getenv('SCAN_BACKEND', 'stub_local')
    azure_blob_connection_string: str = os.getenv('AZURE_BLOB_CONNECTION_STRING', '')
    azure_blob_container: str = os.getenv('AZURE_BLOB_CONTAINER', 'resume-screening')
    azure_blob_quarantine_container: str = os.getenv('AZURE_BLOB_QUARANTINE_CONTAINER', 'resume-screening-quarantine')
    azure_service_bus_connection_string: str = os.getenv('AZURE_SERVICE_BUS_CONNECTION_STRING', '')
    azure_service_bus_queue: str = os.getenv('AZURE_SERVICE_BUS_QUEUE', 'resume-jobs')
    azure_key_vault_url: str = os.getenv('AZURE_KEY_VAULT_URL', '')
    upload_max_bytes: int = int(os.getenv('UPLOAD_MAX_BYTES', str(10 * 1024 * 1024)))
    poll_interval_seconds: int = int(os.getenv('WORKER_POLL_INTERVAL_SECONDS', '5'))
    max_job_attempts: int = int(os.getenv('MAX_JOB_ATTEMPTS', '3'))
    retry_backoff_seconds: int = int(os.getenv('RETRY_BACKOFF_SECONDS', '30'))
    orphaned_job_seconds: int = int(os.getenv('ORPHANED_JOB_SECONDS', '600'))
    request_log_retention_days: int = int(os.getenv('REQUEST_LOG_RETENTION_DAYS', '30'))
    result_retention_days: int = int(os.getenv('RESULT_RETENTION_DAYS', '365'))
    default_tenant_name: str = os.getenv('DEFAULT_TENANT_NAME', 'Default Tenant')
    default_business_unit_name: str = os.getenv('DEFAULT_BUSINESS_UNIT_NAME', 'Default Business Unit')
    bootstrap_admin_name: str = os.getenv('BOOTSTRAP_ADMIN_NAME', 'Platform Admin')
    bootstrap_admin_email: str = os.getenv('BOOTSTRAP_ADMIN_EMAIL', 'admin@example.com')
    bootstrap_admin_password: str = os.getenv('BOOTSTRAP_ADMIN_PASSWORD', '')
    auto_apply_migrations: bool = _bool('AUTO_APPLY_MIGRATIONS', True)
    stripe_api_key: str = os.getenv('STRIPE_API_KEY', '')
    stripe_webhook_secret: str = os.getenv('STRIPE_WEBHOOK_SECRET', '')

    @property
    def local_storage_root(self) -> Path:
        return ROOT_DIR / 'storage'

    @property
    def local_object_root(self) -> Path:
        return self.local_storage_root / 'objects'

    @property
    def temp_materialized_root(self) -> Path:
        return self.local_storage_root / 'materialized'

    @property
    def frontend_dir(self) -> Path:
        return ROOT_DIR / 'frontend'

    @property
    def assets_dir(self) -> Path:
        return ROOT_DIR / 'assets'

    @property
    def uploads_dir(self) -> Path:
        return ROOT_DIR / 'uploads'

    @property
    def reports_dir(self) -> Path:
        return self.local_storage_root / 'reports'

    @property
    def results_dir(self) -> Path:
        return self.local_storage_root / 'results'

    @property
    def tmp_dir(self) -> Path:
        return self.local_storage_root / 'tmp'

    @property
    def ui_settings_dir(self) -> Path:
        return self.local_storage_root / 'ui_settings'

    @property
    def compat_upload_dir(self) -> Path:
        return self.local_storage_root / 'compat_uploads'

    @property
    def migrations_dir(self) -> Path:
        return ROOT_DIR / 'database' / 'migrations'

    def validate_runtime(self) -> None:
        if not self.app_secret_key:
            raise RuntimeError('APP_SECRET_KEY must be configured.')
        if self.storage_backend.lower() == 'azure_blob' and not self.azure_blob_connection_string:
            raise RuntimeError('AZURE_BLOB_CONNECTION_STRING must be configured for azure_blob storage.')
        if self.queue_backend.lower() == 'azure_service_bus' and not self.azure_service_bus_connection_string:
            raise RuntimeError('AZURE_SERVICE_BUS_CONNECTION_STRING must be configured for azure_service_bus queueing.')
        if self.app_env.lower() == 'production' and not self.cookie_secure:
            raise RuntimeError('COOKIE_SECURE must be true in production.')
        if self.app_env.lower() == 'production' and not self.azure_key_vault_url:
            raise RuntimeError('AZURE_KEY_VAULT_URL must be configured in production.')


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def ensure_runtime_directories(settings: Settings | None = None) -> None:
    active = settings or get_settings()
    for directory in (
        active.local_storage_root,
        active.local_object_root,
        active.temp_materialized_root,
        active.uploads_dir,
        active.results_dir,
        active.reports_dir,
        active.tmp_dir,
        active.ui_settings_dir,
        active.compat_upload_dir,
        active.migrations_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

