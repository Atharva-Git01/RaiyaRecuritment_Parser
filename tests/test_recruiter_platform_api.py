from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT_DIR / 'server.py'


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


@dataclass
class _Principal:
    user_id: int
    tenant_id: int
    email: str
    full_name: str
    roles: list[str]
    session_id: int


@contextmanager
def _db_connection():
    class _Cursor:
        def execute(self, *_args, **_kwargs):
            return None

        def fetchall(self):
            return []

    class _Connection:
        def cursor(self):
            return _Cursor()

    yield _Connection()


def _register_stub_modules(tmp_path: Path) -> SimpleNamespace:
    settings = SimpleNamespace(
        app_name='test-app',
        cors_origins=['*'],
        assets_dir=tmp_path / 'assets',
        frontend_dir=tmp_path / 'frontend',
        migrations_dir=tmp_path / 'migrations',
        storage_backend='local',
        queue_backend='local',
        azure_key_vault_url='',
        app_env='test',
        refresh_token_days=7,
        cookie_secure=False,
        stripe_webhook_secret='',
    )
    settings.frontend_dir.mkdir(parents=True, exist_ok=True)
    (settings.frontend_dir / 'login.html').write_text('<html></html>', encoding='utf-8')
    (settings.frontend_dir / 'styles.css').write_text('', encoding='utf-8')

    app_pkg = types.ModuleType('app')
    app_pkg.__path__ = []

    repositories = types.ModuleType('app.repositories')
    repositories.log_request = lambda **_kwargs: None
    repositories.connection_ready = lambda: True
    repositories.get_session = lambda _session_id: None
    repositories.get_user_by_id = lambda _user_id, _tenant_id: None
    repositories.create_session = lambda *_args, **_kwargs: 1

    auth = types.ModuleType('app.auth')
    auth.ACCESS_COOKIE_NAME = 'access'
    auth.REFRESH_COOKIE_NAME = 'refresh'
    auth.SSO_STATE_COOKIE_NAME = 'sso_state'
    auth.Principal = _Principal
    auth.attach_auth_cookies = lambda *_args, **_kwargs: None
    auth.build_sso_authorization_url = lambda *_args, **_kwargs: 'https://example.test/sso'
    auth.clear_auth_cookies = lambda *_args, **_kwargs: None
    auth.decode_oidc_id_token = lambda *_args, **_kwargs: {}
    auth.decode_sso_state = lambda *_args, **_kwargs: {}
    auth.decode_token = lambda *_args, **_kwargs: {'sid': 1, 'tenant_id': 1, 'sub': 1}
    auth.discover_oidc_metadata = lambda *_args, **_kwargs: {}
    auth.exchange_oidc_code = lambda *_args, **_kwargs: {}
    auth.issue_sso_state = lambda *_args, **_kwargs: 'state'
    auth.issue_token_bundle = lambda *_args, **_kwargs: {}
    auth.principal_roles_from_claims = lambda *_args, **_kwargs: []
    auth.verify_password = lambda *_args, **_kwargs: True

    config = types.ModuleType('app.config')
    config.ensure_runtime_directories = lambda _settings: None
    config.get_settings = lambda: settings

    logging_utils = types.ModuleType('app.logging_utils')
    logging_utils.get_logger = lambda _name: _DummyLogger()
    logging_utils.new_request_id = lambda: 'req-test'

    migrations = types.ModuleType('app.migrations')
    migrations.ensure_runtime_ready = lambda: None

    queue_backends = types.ModuleType('app.queue_backends')
    queue_backends.get_queue_backend = lambda _settings: SimpleNamespace()

    saas_db = types.ModuleType('app.saas_db')
    saas_db.get_db_connection = _db_connection

    storage_backends = types.ModuleType('app.storage_backends')
    storage_backends.get_storage_backend = lambda _settings: SimpleNamespace()

    uploads = types.ModuleType('app.uploads')
    uploads.build_object_key = lambda *_args, **_kwargs: 'object-key'
    uploads.read_and_validate_upload = lambda *_args, **_kwargs: b''
    uploads.sanitize_filename = lambda name: name
    uploads.scan_upload = lambda *_args, **_kwargs: {'status': 'clean'}

    app_pkg.repositories = repositories

    sys.modules['app'] = app_pkg
    sys.modules['app.repositories'] = repositories
    sys.modules['app.auth'] = auth
    sys.modules['app.config'] = config
    sys.modules['app.logging_utils'] = logging_utils
    sys.modules['app.migrations'] = migrations
    sys.modules['app.queue_backends'] = queue_backends
    sys.modules['app.saas_db'] = saas_db
    sys.modules['app.storage_backends'] = storage_backends
    sys.modules['app.uploads'] = uploads

    return settings


def _load_server_module(tmp_path: Path):
    settings = _register_stub_modules(tmp_path)
    sys.modules.pop('server', None)
    spec = importlib.util.spec_from_file_location('server', SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module, settings


@pytest.fixture
def server_module(tmp_path):
    module, _settings = _load_server_module(tmp_path)
    return module


@pytest.fixture
def client(server_module):
    return TestClient(server_module.app)


def test_upload_endpoint_saves_jd_files(client, server_module, tmp_path):
    server_module.JD_DIR = tmp_path / 'jd'

    response = client.post(
        '/api/upload?type=jd',
        files=[
            ('files', ('jd-one.pdf', b'jd-one', 'application/pdf')),
            ('files', ('jd-two.docx', b'jd-two', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')),
        ],
    )

    assert response.status_code == 200
    assert response.json() == {'status': 'success', 'count': 2}
    assert (server_module.JD_DIR / 'jd-one.pdf').read_bytes() == b'jd-one'
    assert (server_module.JD_DIR / 'jd-two.docx').read_bytes() == b'jd-two'


def test_upload_endpoint_rejects_invalid_type(client):
    response = client.post('/api/upload?type=invalid', files=[('files', ('bad.pdf', b'data', 'application/pdf'))])

    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid upload type.'


def test_process_endpoint_returns_docstrange_result(client, server_module, tmp_path):
    docstrange_dir = tmp_path / 'DocStrange extraction and parsing'
    docstrange_dir.mkdir(parents=True, exist_ok=True)
    (docstrange_dir / 'main.py').write_text(
        'def run_bulk_extraction():\n'
        '    return {"status": "started", "processed": 3}\n',
        encoding='utf-8',
    )
    server_module.ROOT_DIR = tmp_path

    response = client.post('/api/process')

    assert response.status_code == 200
    assert response.json() == {'status': 'started', 'processed': 3}


def test_jobs_endpoint_reports_queued_and_completed_items(client, server_module, tmp_path):
    resumes_dir = tmp_path / 'resumes'
    parsed_dir = tmp_path / 'parsed'
    resumes_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    (resumes_dir / 'queued.pdf').write_bytes(b'queued')
    (resumes_dir / 'done.pdf').write_bytes(b'done')
    (parsed_dir / 'done.json').write_text('{"score": 92}', encoding='utf-8')

    server_module.RESUMES_DIR = resumes_dir
    server_module.PARSED_DIR = parsed_dir

    response = client.get('/api/jobs')

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 2

    queued = next(job for job in jobs if job['filename'] == 'queued.pdf')
    completed = next(job for job in jobs if job['filename'] == 'done.pdf')

    assert queued['status'] == 'Queued'
    assert queued['progress'] == 0
    assert queued['step'] == 'Pending'

    assert completed['status'] == 'Completed'
    assert completed['progress'] == 100
    assert completed['step'] == 'Extraction Done'
    assert completed['score'] == 92
