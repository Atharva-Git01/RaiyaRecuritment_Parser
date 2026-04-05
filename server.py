from __future__ import annotations

import hashlib
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from app import repositories
from app.auth import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    SSO_STATE_COOKIE_NAME,
    Principal,
    attach_auth_cookies,
    build_sso_authorization_url,
    clear_auth_cookies,
    decode_oidc_id_token,
    decode_sso_state,
    decode_token,
    discover_oidc_metadata,
    exchange_oidc_code,
    issue_sso_state,
    issue_token_bundle,
    principal_roles_from_claims,
    verify_password,
)
from app.config import ensure_runtime_directories, get_settings
from app.logging_utils import get_logger, new_request_id
from app.migrations import ensure_runtime_ready
from app.queue_backends import get_queue_backend
from app.saas_db import get_db_connection
from app.storage_backends import get_storage_backend
from app.uploads import build_object_key, read_and_validate_upload, sanitize_filename, scan_upload

ROOT_DIR = Path(__file__).resolve().parent
logger = get_logger(__name__)
settings = get_settings()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SSOStartRequest(BaseModel):
    email: EmailStr
    redirect_path: str = '/recruiter-platform.html'


class ScanResultRequest(BaseModel):
    status: str
    engine: str = 'external-scanner'
    details: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_directories(settings)
    ensure_runtime_ready()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)

if settings.assets_dir.exists():
    app.mount('/assets', StaticFiles(directory=str(settings.assets_dir)), name='assets')


def _iso_or_none(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else None


async def _resolve_principal(request: Request, required: bool = True) -> Optional[Principal]:
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required.')
        return None
    payload = decode_token(access_token, 'access')
    session_id = int(payload.get('sid') or 0)
    tenant_id = int(payload.get('tenant_id') or 0)
    user_id = int(payload.get('sub') or 0)
    session = repositories.get_session(session_id)
    if not session or session.get('revoked_at'):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session is no longer valid.')
    expires_at = session.get('expires_at')
    if expires_at and isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session has expired.')
    user = repositories.get_user_by_id(user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User account was not found.')
    principal = Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        email=str(user.get('email') or ''),
        full_name=str(user.get('full_name') or ''),
        roles=list(user.get('assigned_roles') or []),
        session_id=session_id,
    )
    request.state.principal = principal
    return principal


async def get_current_principal(request: Request) -> Principal:
    principal = await _resolve_principal(request, required=True)
    assert principal is not None
    return principal


def require_roles(*allowed_roles: str) -> Callable:
    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not set(principal.roles).intersection(set(allowed_roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient role for this action.')
        return principal
    return dependency


def _rate_limit(scope_key: str, subject_key: str, limit_count: int, window_seconds: int) -> None:
    decision = repositories.check_rate_limit(scope_key, subject_key, limit_count, window_seconds)
    if not decision['allowed']:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail='Rate limit exceeded.')


def _ensure_tenant_can_submit(tenant_id: int) -> None:
    subscription = repositories.get_subscription_for_tenant(tenant_id)
    if subscription and str(subscription.get('subscription_status') or '').lower() in {'expired', 'cancelled', 'delinquent', 'suspended'}:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail='Tenant subscription does not allow new batch creation.')


def _pending_migrations() -> list[str]:
    migrations_dir = settings.migrations_dir
    if not migrations_dir.exists():
        return []
    expected = {path.name for path in migrations_dir.glob('*.sql')}
    applied = set()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT version FROM schema_migrations')
            applied = {row[0] for row in cursor.fetchall()}
    except Exception:
        return sorted(expected)
    return sorted(expected - applied)


def _storage_ready() -> dict:
    try:
        storage = get_storage_backend(settings)
        backend_name = settings.storage_backend.lower()
        if backend_name == 'azure_blob':
            storage.container.get_container_properties()
        return {'ready': True, 'backend': backend_name}
    except Exception as exc:
        return {'ready': False, 'error': str(exc)}


def _queue_ready() -> dict:
    try:
        queue = get_queue_backend(settings)
        backend_name = settings.queue_backend.lower()
        if backend_name == 'azure_service_bus' and (getattr(queue, '_sender', None) is None or getattr(queue, '_receiver', None) is None):
            raise RuntimeError('Azure Service Bus sender/receiver could not be created.')
        return {'ready': True, 'backend': backend_name}
    except Exception as exc:
        return {'ready': False, 'error': str(exc)}


def _key_vault_ready() -> dict:
    if not settings.azure_key_vault_url:
        return {'ready': settings.app_env.lower() != 'production', 'status': 'skipped'}
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        client = SecretClient(vault_url=settings.azure_key_vault_url, credential=DefaultAzureCredential())
        pager = client.list_properties_of_secrets()
        next(iter(pager), None)
        return {'ready': True}
    except Exception as exc:
        return {'ready': False, 'error': str(exc)}


@app.middleware('http')
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or new_request_id()
    request.state.request_id = request_id
    started = time.perf_counter()
    principal = None
    try:
        principal = await _resolve_principal(request, required=False)
    except HTTPException:
        principal = None
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers['x-request-id'] = request_id
    repositories.log_request(
        tenant_id=getattr(principal, 'tenant_id', None),
        user_id=getattr(principal, 'user_id', None),
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        ip_address=_client_ip(request),
        user_agent=request.headers.get('user-agent'),
    )
    return response


@app.get('/')
async def root() -> Response:
    login_path = settings.frontend_dir / 'login.html'
    if login_path.exists():
        return FileResponse(login_path)
    return RedirectResponse('/recruiter-platform.html')


@app.get('/app.js')
async def app_js() -> Response:
    return FileResponse(ROOT_DIR / 'app.js')


@app.get('/styles.css')
async def styles_css() -> Response:
    return FileResponse(settings.frontend_dir / 'styles.css')


@app.get('/healthz')
async def healthz() -> dict:
    return {'status': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()}


@app.get('/readyz')
async def readyz() -> JSONResponse:
    db_ready = repositories.connection_ready()
    storage_status = _storage_ready()
    queue_status = _queue_ready()
    key_vault_status = _key_vault_ready()
    pending = _pending_migrations()
    ready = bool(db_ready and storage_status['ready'] and queue_status['ready'] and key_vault_status['ready'] and not pending)
    payload = {
        'ready': ready,
        'db': {'ready': db_ready},
        'storage': storage_status,
        'queue': queue_status,
        'key_vault': key_vault_status,
        'pending_migrations': pending,
    }
    return JSONResponse(status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@app.post('/api/auth/login')
async def login(payload: LoginRequest, response: Response, request: Request) -> dict:
    _rate_limit('auth_login', f"ip:{_client_ip(request) or 'unknown'}", 20, 300)
    user = repositories.get_user_by_email(payload.email)
    if not user or not user.get('password_hash') or not verify_password(payload.password, str(user['password_hash'])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials.')
    roles = list(user.get('assigned_roles') or [])
    if 'platform_admin' not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Local password login is reserved for platform administrators.')
    session_id = repositories.create_session(
        int(user['user_id']),
        int(user['tenant_id']),
        jwt_id='bootstrap',
        refresh_token_hash='bootstrap',
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_days),
        device_fingerprint=request.headers.get('user-agent'),
    )
    tokens = issue_token_bundle(int(user['user_id']), int(user['tenant_id']), roles, session_id)
    repositories.update_session_refresh(session_id, tokens.refresh_jti, hashlib.sha256(tokens.refresh_token.encode('utf-8')).hexdigest(), tokens.refresh_expires_at)
    attach_auth_cookies(response, tokens)
    repositories.log_audit_event(int(user['tenant_id']), int(user['user_id']), 'auth.local_login', 'user', str(user['user_id']), {'email': payload.email})
    return {
        'user': {
            'user_id': int(user['user_id']),
            'tenant_id': int(user['tenant_id']),
            'email': user['email'],
            'full_name': user.get('full_name'),
            'roles': roles,
        }
    }


@app.post('/api/auth/sso/start')
async def sso_start(payload: SSOStartRequest, response: Response) -> dict:
    domain = payload.email.split('@', 1)[1].lower()
    tenant = repositories.get_tenant_by_domain(domain)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No tenant SSO configuration was found for that domain.')
    oidc_config = repositories.get_oidc_config_for_tenant(int(tenant['tenant_id']))
    if not oidc_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Tenant OIDC configuration is missing.')
    metadata = discover_oidc_metadata(str(oidc_config['discovery_url']))
    nonce, signed_state = issue_sso_state(int(tenant['tenant_id']), payload.redirect_path)
    auth_url = build_sso_authorization_url(
        metadata,
        client_id=str(oidc_config['client_id']),
        redirect_uri=str(oidc_config['redirect_uri']),
        state=signed_state,
        nonce=nonce,
        scope=str(oidc_config.get('scopes') or 'openid profile email'),
    )
    response.set_cookie(SSO_STATE_COOKIE_NAME, signed_state, httponly=True, secure=settings.cookie_secure, samesite='lax', max_age=600, path='/')
    return {'authorization_url': auth_url, 'tenant_id': int(tenant['tenant_id'])}


@app.get('/api/auth/sso/callback')
async def sso_callback(code: str, state: str, request: Request) -> Response:
    cookie_state = request.cookies.get(SSO_STATE_COOKIE_NAME)
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid SSO state.')
    decoded_state = decode_sso_state(state)
    tenant_id = int(decoded_state['tenant_id'])
    oidc_config = repositories.get_oidc_config_for_tenant(tenant_id)
    if not oidc_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Tenant OIDC configuration is missing.')
    metadata = discover_oidc_metadata(str(oidc_config['discovery_url']))
    token_response = exchange_oidc_code(metadata, str(oidc_config['client_id']), str(oidc_config['client_secret']), code, str(oidc_config['redirect_uri']))
    claims = decode_oidc_id_token(str(token_response['id_token']), metadata, str(oidc_config['client_id']))
    email = str(claims.get('email') or claims.get('preferred_username') or '')
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='OIDC provider did not return an email address.')
    roles = principal_roles_from_claims(['recruiter'], claims.get('roles') or claims.get('groups'))
    user = repositories.ensure_oidc_user(tenant_id, email, str(claims.get('name') or email), roles=roles, is_verified=True)
    response = RedirectResponse(decoded_state.get('redirect_path') or '/recruiter-platform.html', status_code=status.HTTP_302_FOUND)
    session_id = repositories.create_session(int(user['user_id']), tenant_id, 'oidc', 'oidc', datetime.utcnow() + timedelta(days=settings.refresh_token_days), request.headers.get('user-agent'))
    tokens = issue_token_bundle(int(user['user_id']), tenant_id, roles, session_id)
    repositories.update_session_refresh(session_id, tokens.refresh_jti, hashlib.sha256(tokens.refresh_token.encode('utf-8')).hexdigest(), tokens.refresh_expires_at)
    attach_auth_cookies(response, tokens)
    response.delete_cookie(SSO_STATE_COOKIE_NAME, path='/')
    repositories.log_audit_event(tenant_id, int(user['user_id']), 'auth.sso_login', 'user', str(user['user_id']), {'email': email, 'issuer': metadata.issuer})
    return response


@app.post('/api/auth/logout')
async def logout(request: Request, response: Response) -> dict:
    principal = await _resolve_principal(request, required=False)
    if principal:
        repositories.revoke_session(principal.session_id)
        repositories.log_audit_event(principal.tenant_id, principal.user_id, 'auth.logout', 'session', str(principal.session_id), {})
    clear_auth_cookies(response)
    return {'status': 'logged_out'}


@app.get('/api/me')
async def me(principal: Principal = Depends(get_current_principal)) -> dict:
    return {
        'user_id': principal.user_id,
        'tenant_id': principal.tenant_id,
        'email': principal.email,
        'full_name': principal.full_name,
        'roles': principal.roles,
    }

@app.post('/api/batches')
async def create_batch(
    jd_file: UploadFile = File(...),
    resumes: list[UploadFile] = File(...),
    jd_title: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'recruiter')),
) -> dict:
    _rate_limit('batch_create', f'tenant:{principal.tenant_id}', 30, 60)
    _ensure_tenant_can_submit(principal.tenant_id)
    if not resumes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='At least one resume is required.')
    bu_id = repositories.get_default_business_unit_for_tenant(principal.tenant_id)
    if not bu_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='No business unit is configured for this tenant.')
    if idempotency_key:
        existing = repositories.find_batch_by_idempotency(bu_id, idempotency_key)
        if existing:
            return {
                'batch': repositories.get_batch_summary(int(existing['batch_id']), principal.tenant_id),
                'jobs': repositories.list_batch_jobs(int(existing['batch_id']), principal.tenant_id),
                'idempotent_replay': True,
            }

    storage = get_storage_backend(settings)
    queue = get_queue_backend(settings)
    batch_guid = __import__('uuid').uuid4().hex

    jd_upload = await read_and_validate_upload(jd_file, 'jd', settings)
    jd_object_key = build_object_key(principal.tenant_id, batch_guid, 'job_descriptions', jd_upload.safe_filename)
    jd_stored = storage.store_bytes(jd_object_key, jd_upload.data, jd_upload.content_type, quarantine=False)
    jd_object_id = repositories.create_object_record(
        tenant_id=principal.tenant_id,
        batch_id=None,
        job_id=None,
        purpose='job_description',
        backend=jd_stored.backend,
        object_key=jd_stored.object_key,
        original_filename=jd_upload.original_filename,
        content_type=jd_stored.content_type,
        size_bytes=jd_stored.size_bytes,
        checksum_sha256=hashlib.sha256(jd_upload.data).hexdigest(),
        created_by_user_id=principal.user_id,
        quarantine=False,
    )
    job_description_id = repositories.create_job_description_record(bu_id, jd_title or Path(jd_upload.safe_filename).stem, jd_upload.parsed_json or {}, source_object_id=jd_object_id)
    batch_id = repositories.create_batch_record(bu_id, principal.user_id, batch_guid, job_description_id, idempotency_key)
    repositories.update_object_binding(jd_object_id, batch_id=batch_id, purpose='job_description')

    created_jobs = []
    for resume_file in resumes:
        upload = await read_and_validate_upload(resume_file, 'resume', settings)
        scan_outcome = scan_upload(upload, settings)
        quarantine = scan_outcome.status != 'passed'
        object_key = build_object_key(principal.tenant_id, batch_guid, 'resumes', upload.safe_filename)
        stored = storage.store_bytes(object_key, upload.data, upload.content_type, quarantine=quarantine)
        object_id = repositories.create_object_record(
            tenant_id=principal.tenant_id,
            batch_id=batch_id,
            job_id=None,
            purpose='resume_upload',
            backend=stored.backend,
            object_key=stored.object_key,
            original_filename=upload.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=hashlib.sha256(upload.data).hexdigest(),
            created_by_user_id=principal.user_id,
            quarantine=quarantine,
        )
        job_id = repositories.create_job_record(
            batch_id=batch_id,
            jd_id=job_description_id,
            requester_user_id=principal.user_id,
            resume_filename=upload.original_filename,
            resume_file_id=object_id,
            scan_status=scan_outcome.status,
            idempotency_key=f'{batch_guid}:{sanitize_filename(upload.original_filename)}',
        )
        repositories.update_object_binding(object_id, batch_id=batch_id, job_id=job_id, purpose='resume_upload', quarantine=quarantine)
        repositories.record_virus_scan(object_id, scan_outcome.engine, scan_outcome.status, scan_outcome.details)
        if scan_outcome.status == 'passed':
            queue.enqueue(job_id)
        elif scan_outcome.status == 'blocked':
            repositories.update_job_state(job_id, status='failed', stage='scan_pending', progress=100, error='Upload blocked by malware scan.', scan_status='blocked', completed=True)
        created_jobs.append({'job_id': job_id, 'filename': upload.original_filename, 'scan_status': scan_outcome.status})

    repositories.update_batch_submitted_count(batch_id)
    repositories.refresh_batch_status(batch_id)
    repositories.log_audit_event(principal.tenant_id, principal.user_id, 'batch.created', 'batch', str(batch_id), {'batch_guid': batch_guid, 'job_count': len(created_jobs)})
    return {
        'batch': repositories.get_batch_summary(batch_id, principal.tenant_id),
        'jobs': repositories.list_batch_jobs(batch_id, principal.tenant_id),
    }


@app.get('/api/batches/{batch_id}')
async def get_batch(batch_id: int, principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer'))) -> dict:
    batch = repositories.get_batch_summary(batch_id, principal.tenant_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Batch not found.')
    return {'batch': batch, 'jobs': repositories.list_batch_jobs(batch_id, principal.tenant_id)}


@app.get('/api/jobs/{job_id}')
async def get_job(job_id: int, principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer'))) -> dict:
    job = repositories.get_job_detail(job_id, principal.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found.')
    return job


@app.get('/api/results/{job_id}')
async def get_result(job_id: int, principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer'))) -> dict:
    result = repositories.get_result_for_job(job_id, principal.tenant_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Result not found.')
    return result


@app.get('/api/admin/users')
async def admin_users(principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin'))):
    return {'users': repositories.list_tenant_users(principal.tenant_id)}


@app.get('/api/admin/roles')
async def admin_roles(_: Principal = Depends(require_roles('platform_admin', 'tenant_admin'))):
    return {'roles': repositories.list_role_templates()}


@app.get('/api/admin/subscription')
async def admin_subscription(principal: Principal = Depends(require_roles('platform_admin', 'billing_admin', 'tenant_admin'))):
    return {'subscription': repositories.get_subscription_for_tenant(principal.tenant_id)}


@app.get('/api/admin/usage')
async def admin_usage(principal: Principal = Depends(require_roles('platform_admin', 'billing_admin', 'tenant_admin'))):
    return {'usage_events': repositories.list_usage_events(principal.tenant_id)}


@app.get('/api/admin/invoices')
async def admin_invoices(principal: Principal = Depends(require_roles('platform_admin', 'billing_admin', 'tenant_admin'))):
    return {'invoices': repositories.list_invoices_for_tenant(principal.tenant_id)}


@app.get('/api/admin/entitlements')
async def admin_entitlements(principal: Principal = Depends(require_roles('platform_admin', 'billing_admin', 'tenant_admin'))):
    return {'entitlements': repositories.list_entitlements_for_tenant(principal.tenant_id)}


@app.post('/api/admin/files/{object_id}/scan-result')
async def admin_scan_result(object_id: int, payload: ScanResultRequest, principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin'))):
    object_record = repositories.get_object_record(object_id, principal.tenant_id)
    if not object_record or not object_record.get('job_id'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Object not found for this tenant.')
    repositories.apply_scan_result(int(object_record['job_id']), object_id, payload.status, payload.engine, payload.details)
    if payload.status == 'passed':
        get_queue_backend(settings).enqueue(int(object_record['job_id']))
    repositories.log_audit_event(principal.tenant_id, principal.user_id, 'scan.result_updated', 'object', str(object_id), {'status': payload.status, 'engine': payload.engine})
    return {'object_id': object_id, 'job_id': int(object_record['job_id']), 'scan_status': payload.status}


@app.get('/api/admin/monitor')
async def admin_monitor(_: Principal = Depends(require_roles('platform_admin'))):
    return repositories.get_monitor_snapshot()


@app.get('/api/files/{object_id}')
async def download_file(object_id: int, principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer'))):
    object_record = repositories.get_object_record(object_id, principal.tenant_id)
    if not object_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found.')
    if object_record.get('quarantine_flag') and object_record.get('purpose') != 'report':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Quarantined uploads cannot be downloaded.')
    if object_record.get('purpose') != 'report' and not set(principal.roles).intersection({'platform_admin', 'tenant_admin'}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only administrators can download non-report files.')
    storage = get_storage_backend(settings)
    payload = storage.read_bytes(str(object_record['object_key']), quarantine=bool(object_record.get('quarantine_flag')))
    filename = quote(str(object_record.get('original_filename') or f'file-{object_id}'))
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type=str(object_record.get('content_type') or 'application/octet-stream'), headers=headers)


@app.post('/api/webhooks/stripe')
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    try:
        import stripe
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(payload, request.headers.get('stripe-signature', ''), settings.stripe_webhook_secret)
        else:
            event = json.loads(payload.decode('utf-8') or '{}')
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Invalid Stripe payload: {exc}') from exc
    event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', 'unknown')
    event_object = (event.get('data', {}) or {}).get('object', {}) if isinstance(event, dict) else {}
    metadata = event_object.get('metadata', {}) if isinstance(event_object, dict) else {}
    tenant_id_raw = metadata.get('tenant_id')
    if tenant_id_raw:
        repositories.record_billing_event(int(tenant_id_raw), str(event_type), event if isinstance(event, dict) else {'type': event_type})
    return {'received': True, 'event_type': event_type, 'tenant_id': tenant_id_raw}


@app.get('/api/history')
async def batch_history(principal: Principal = Depends(require_roles('platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer'))):
    return {'history': repositories.get_batch_history(principal.tenant_id)}


@app.get('/login.html')
async def login_page() -> Response:
    target = settings.frontend_dir / 'login.html'
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Page not found.')
    return FileResponse(target)


for page_name in (
    'recruiter-platform.html',
    'recruiter-results.html',
    'screening-results.html',
    'bulk-processing.html',
    'settings.html',
    'history.html',
    'database-monitor.html',
):
    route_path = '/' + page_name

    async def _serve_page(page: str = page_name, _: Principal = Depends(get_current_principal)):
        target = settings.frontend_dir / page
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Page not found.')
        return FileResponse(target)

    app.add_api_route(route_path, _serve_page, methods=['GET'])


# ── Bulk Processing Endpoints (DocStrange Integration) ────────────────

RESUMES_DIR = ROOT_DIR / "DocStrange extraction and parsing" / "resumes"
JD_DIR = ROOT_DIR / "Scoring_Agent" / "uploads" / "jd"
PARSED_DIR = ROOT_DIR / "Scoring_Agent" / "uploads" / "parsed resumes"

@app.post("/api/upload")
async def bulk_upload(type: str, files: list[UploadFile] = File(...)):
    """Handle uploads for resumes and JDs."""
    if type == "resume":
        target_dir = RESUMES_DIR
    elif type == "jd":
        target_dir = JD_DIR
    else:
        raise HTTPException(status_code=400, detail="Invalid upload type.")

    target_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0
    for file in files:
        if not file.filename: continue
        content = await file.read()
        # For JDs, ensure we handle the filename correctly if needed
        # The user mentioned Scoring_Agent/uploads/jd as the path
        file_path = target_dir / file.filename
        file_path.write_bytes(content)
        saved_count += 1
    
    return {"status": "success", "count": saved_count}

@app.post("/api/process")
async def trigger_process():
    """Trigger the DocStrange extraction pipeline."""
    import sys
    import importlib.util

    docstrange_dir = ROOT_DIR / "DocStrange extraction and parsing"
    if str(docstrange_dir) not in sys.path:
        sys.path.append(str(docstrange_dir))

    # Import run_bulk_extraction from main.py
    main_path = docstrange_dir / "main.py"
    spec = importlib.util.spec_from_file_location("docstrange_main", str(main_path))
    if not spec or not spec.loader:
        raise HTTPException(status_code=500, detail="Could not load DocStrange main module.")
    
    docstrange_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(docstrange_main)
    
    # Run in background or wait? Frontend is calling this and waiting for a response
    # to redirect. DocStrange is relatively fast, but for large batches it might time out.
    # For now, let's run it and return the result.
    result = docstrange_main.run_bulk_extraction()
    return result

@app.get("/api/jobs")
async def get_processing_jobs():
    """Return status of processing jobs based on file existence."""
    jobs = []
    if not RESUMES_DIR.exists():
        return []
    
    resumes = list(RESUMES_DIR.glob("*.*"))
    for idx, path in enumerate(resumes):
        stem = path.stem
        parsed_path = PARSED_DIR / f"{stem}.json"
        
        status = "Queued"
        progress = 0
        step = "Pending"
        score = None
        
        if parsed_path.exists():
            status = "Completed"
            progress = 100
            step = "Extraction Done"
            # Try to get score if available (though DocStrange doesn't score)
            try:
                with open(parsed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Score might be added later by Scoring_Agent
                    score = data.get("score") 
            except: pass

        jobs.append({
            "id": f"JOB-{idx+1:03d}",
            "filename": path.name,
            "status": status,
            "progress": progress,
            "step": step,
            "score": score
        })
    return jobs
