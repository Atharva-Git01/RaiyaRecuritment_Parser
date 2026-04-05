from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.auth import hash_password
from app.config import get_settings
from app.saas_db import get_db_connection, test_connection

PLATFORM_ROLES = ['platform_admin', 'tenant_admin', 'billing_admin', 'recruiter', 'viewer']


def _loads(value: Any, default: Any) -> Any:
    if value in (None, '', b''):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _fetchone(query: str, params: tuple = (), dictionary: bool = True) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        cursor.execute(query, params)
        return cursor.fetchone()


def _fetchall(query: str, params: tuple = (), dictionary: bool = True) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        cursor.execute(query, params)
        return cursor.fetchall()


def _execute(query: str, params: tuple = ()) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def bootstrap_defaults() -> Dict[str, int]:
    settings = get_settings()
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT tenant_id FROM tenants WHERE tenant_name = %s LIMIT 1', (settings.default_tenant_name,))
        tenant = cursor.fetchone()
        if tenant:
            tenant_id = tenant['tenant_id']
        else:
            cursor.execute('INSERT INTO tenants (tenant_name, status, created_at) VALUES (%s, %s, CURRENT_TIMESTAMP)', (settings.default_tenant_name, 'active'))
            tenant_id = cursor.lastrowid

        cursor.execute('SELECT bu_id FROM business_units WHERE tenant_id = %s AND bu_name = %s LIMIT 1', (tenant_id, settings.default_business_unit_name))
        business_unit = cursor.fetchone()
        if business_unit:
            bu_id = business_unit['bu_id']
        else:
            cursor.execute('INSERT INTO business_units (tenant_id, bu_name, created_at) VALUES (%s, %s, CURRENT_TIMESTAMP)', (tenant_id, settings.default_business_unit_name))
            bu_id = cursor.lastrowid

        if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
            cursor.execute('SELECT user_id, password_hash FROM global_users WHERE email = %s LIMIT 1', (settings.bootstrap_admin_email,))
            user = cursor.fetchone()
            password_hash = hash_password(settings.bootstrap_admin_password)
            if user:
                user_id = user['user_id']
                cursor.execute('UPDATE global_users SET full_name = %s, password_hash = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s', (settings.bootstrap_admin_name, password_hash, 'active', user_id))
            else:
                cursor.execute(
                    'INSERT INTO global_users (email, full_name, password_hash, status, is_verified, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
                    (settings.bootstrap_admin_email, settings.bootstrap_admin_name, password_hash, 'active', True),
                )
                user_id = cursor.lastrowid
            cursor.execute('SELECT id FROM user_tenants WHERE tenant_id = %s AND user_id = %s LIMIT 1', (tenant_id, user_id))
            membership = cursor.fetchone()
            roles_json = _dumps(['platform_admin', 'tenant_admin', 'billing_admin', 'recruiter'])
            if membership:
                cursor.execute('UPDATE user_tenants SET assigned_roles = %s WHERE id = %s', (roles_json, membership['id']))
            else:
                cursor.execute('INSERT INTO user_tenants (tenant_id, user_id, assigned_roles, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, user_id, roles_json))
        conn.commit()
        return {'tenant_id': tenant_id, 'bu_id': bu_id}


def get_default_business_unit_for_tenant(tenant_id: int) -> Optional[int]:
    row = _fetchone('SELECT bu_id FROM business_units WHERE tenant_id = %s ORDER BY bu_id ASC LIMIT 1', (tenant_id,))
    return row['bu_id'] if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        '''
        SELECT gu.*, ut.tenant_id, ut.assigned_roles, t.tenant_name
        FROM global_users gu
        LEFT JOIN user_tenants ut ON ut.user_id = gu.user_id
        LEFT JOIN tenants t ON t.tenant_id = ut.tenant_id
        WHERE LOWER(gu.email) = LOWER(%s)
        ORDER BY ut.id ASC
        LIMIT 1
        ''',
        (email,),
    )
    if not row:
        return None
    row['assigned_roles'] = _loads(row.get('assigned_roles'), [])
    return row


def get_user_by_id(user_id: int, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if tenant_id is None:
        query = '''
            SELECT gu.*, ut.tenant_id, ut.assigned_roles, t.tenant_name
            FROM global_users gu
            LEFT JOIN user_tenants ut ON ut.user_id = gu.user_id
            LEFT JOIN tenants t ON t.tenant_id = ut.tenant_id
            WHERE gu.user_id = %s
            ORDER BY ut.id ASC
            LIMIT 1
        '''
        params = (user_id,)
    else:
        query = '''
            SELECT gu.*, ut.tenant_id, ut.assigned_roles, t.tenant_name
            FROM global_users gu
            JOIN user_tenants ut ON ut.user_id = gu.user_id AND ut.tenant_id = %s
            JOIN tenants t ON t.tenant_id = ut.tenant_id
            WHERE gu.user_id = %s
            LIMIT 1
        '''
        params = (tenant_id, user_id)
    row = _fetchone(query, params)
    if not row:
        return None
    row['assigned_roles'] = _loads(row.get('assigned_roles'), [])
    return row


def ensure_oidc_user(tenant_id: int, email: str, full_name: str, roles: Optional[List[str]] = None, is_verified: bool = True) -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM global_users WHERE email = %s LIMIT 1', (email,))
        user = cursor.fetchone()
        if user:
            user_id = user['user_id']
            cursor.execute('UPDATE global_users SET full_name = %s, status = %s, is_verified = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s', (full_name, 'active', is_verified, user_id))
        else:
            cursor.execute('INSERT INTO global_users (email, full_name, status, is_verified, created_at, updated_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (email, full_name, 'active', is_verified))
            user_id = cursor.lastrowid
        assigned_roles = roles or ['recruiter']
        cursor.execute('SELECT id FROM user_tenants WHERE tenant_id = %s AND user_id = %s LIMIT 1', (tenant_id, user_id))
        membership = cursor.fetchone()
        if membership:
            cursor.execute('UPDATE user_tenants SET assigned_roles = %s WHERE id = %s', (_dumps(assigned_roles), membership['id']))
        else:
            cursor.execute('INSERT INTO user_tenants (tenant_id, user_id, assigned_roles, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, user_id, _dumps(assigned_roles)))
        conn.commit()
    return get_user_by_id(int(user_id), tenant_id)


def list_tenant_users(tenant_id: int) -> List[Dict[str, Any]]:
    rows = _fetchall('SELECT gu.user_id, gu.email, gu.full_name, gu.status, gu.is_verified, ut.assigned_roles FROM global_users gu JOIN user_tenants ut ON ut.user_id = gu.user_id WHERE ut.tenant_id = %s ORDER BY gu.email ASC', (tenant_id,))
    for row in rows:
        row['assigned_roles'] = _loads(row.get('assigned_roles'), [])
    return rows


def list_role_templates() -> List[str]:
    return list(PLATFORM_ROLES)


def create_session(user_id: int, tenant_id: int, jwt_id: str, refresh_token_hash: str, expires_at: datetime, device_fingerprint: str | None = None) -> int:
    return _execute('INSERT INTO sessions (user_id, tenant_id, jwt_id, refresh_token_hash, expires_at, device_fingerprint, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (user_id, tenant_id, jwt_id, refresh_token_hash, expires_at, device_fingerprint))


def get_session(session_id: int) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM sessions WHERE session_id = %s LIMIT 1', (session_id,))


def update_session_refresh(session_id: int, jwt_id: str, refresh_token_hash: str, expires_at: datetime) -> None:
    _execute('UPDATE sessions SET jwt_id = %s, refresh_token_hash = %s, expires_at = %s, updated_at = CURRENT_TIMESTAMP, revoked_at = NULL WHERE session_id = %s', (jwt_id, refresh_token_hash, expires_at, session_id))


def revoke_session(session_id: int) -> None:
    _execute('UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE session_id = %s', (session_id,))


def get_session_for_refresh(session_id: int) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM sessions WHERE session_id = %s LIMIT 1', (session_id,))


def check_rate_limit(scope_key: str, subject_key: str, limit_count: int, window_seconds: int) -> Dict[str, Any]:
    now = datetime.utcnow()
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM rate_limits WHERE scope_key = %s AND subject_key = %s LIMIT 1', (scope_key, subject_key))
        row = cursor.fetchone()
        if not row:
            cursor.execute('INSERT INTO rate_limits (scope_key, subject_key, limit_count, window_started_at, request_count, updated_at) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)', (scope_key, subject_key, limit_count, now, 1))
            conn.commit()
            return {'allowed': True, 'remaining': max(limit_count - 1, 0), 'reset_at': now + timedelta(seconds=window_seconds)}
        window_started_at = row['window_started_at'] or now
        elapsed = (now - window_started_at).total_seconds()
        if elapsed >= window_seconds:
            cursor.execute('UPDATE rate_limits SET limit_count = %s, window_started_at = %s, request_count = %s, updated_at = CURRENT_TIMESTAMP WHERE rate_limit_id = %s', (limit_count, now, 1, row['rate_limit_id']))
            conn.commit()
            return {'allowed': True, 'remaining': max(limit_count - 1, 0), 'reset_at': now + timedelta(seconds=window_seconds)}
        request_count = int(row.get('request_count') or 0)
        if request_count >= limit_count:
            return {'allowed': False, 'remaining': 0, 'reset_at': window_started_at + timedelta(seconds=window_seconds)}
        cursor.execute('UPDATE rate_limits SET request_count = request_count + 1, updated_at = CURRENT_TIMESTAMP WHERE rate_limit_id = %s', (row['rate_limit_id'],))
        conn.commit()
        return {'allowed': True, 'remaining': max(limit_count - request_count - 1, 0), 'reset_at': window_started_at + timedelta(seconds=window_seconds)}


def log_request(tenant_id: Optional[int], user_id: Optional[int], request_id: str, method: str, path: str, status_code: int, duration_ms: float, ip_address: Optional[str], user_agent: Optional[str]) -> None:
    try:
        _execute('INSERT INTO request_logs (tenant_id, user_id, request_id, method, path, status_code, duration_ms, ip_address, user_agent, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, user_id, request_id, method, path, status_code, duration_ms, ip_address, user_agent))
    except Exception:
        pass


def log_audit_event(tenant_id: Optional[int], actor_user_id: Optional[int], event_type: str, target_type: Optional[str], target_id: Optional[str], payload: Dict[str, Any]) -> int:
    return _execute('INSERT INTO audit_events (tenant_id, actor_user_id, event_type, target_type, target_id, payload_json, created_at) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, actor_user_id, event_type, target_type, target_id, _dumps(payload)))


def record_billing_event(tenant_id: int, event_type: str, event_data: Dict[str, Any]) -> int:
    return _execute('INSERT INTO billing_events (tenant_id, event_type, event_data, timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, event_type, _dumps(event_data)))


def get_tenant_by_domain(domain: str) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM tenant_domains WHERE LOWER(domain_name) = LOWER(%s) AND status = %s LIMIT 1', (domain, 'active'))


def get_oidc_config_for_tenant(tenant_id: int) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM tenant_oidc_configs WHERE tenant_id = %s AND status = %s LIMIT 1', (tenant_id, 'active'))

def create_job_description_record(bu_id: int, jd_title: str, jd_data: Dict[str, Any], source_object_id: Optional[int] = None) -> int:
    return _execute('INSERT INTO job_descriptions (bu_id, jd_title, jd_data_json, source_object_id, created_at, updated_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (bu_id, jd_title, _dumps(jd_data), source_object_id))


def find_batch_by_idempotency(bu_id: int, idempotency_key: str) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM batches WHERE bu_id = %s AND idempotency_key = %s LIMIT 1', (bu_id, idempotency_key))


def create_batch_record(bu_id: int, uploader_user_id: int, batch_guid: str, job_description_id: int, idempotency_key: Optional[str]) -> int:
    return _execute('INSERT INTO batches (bu_id, uploader_user_id, status, batch_guid, job_description_id, idempotency_key, submitted_count, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (bu_id, uploader_user_id, 'queued', batch_guid, job_description_id, idempotency_key, 0))


def create_job_record(batch_id: int, jd_id: int, requester_user_id: int, resume_filename: str, resume_file_id: int, scan_status: str, idempotency_key: Optional[str] = None) -> int:
    initial_status = 'scan_pending' if scan_status == 'pending' else ('failed' if scan_status == 'blocked' else 'received')
    return _execute('INSERT INTO jobs (batch_id, jd_id, requester_user_id, resume_filename, resume_file_id, status, stage, progress, attempts, idempotency_key, scan_status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)', (batch_id, jd_id, requester_user_id, resume_filename, resume_file_id, initial_status, initial_status, 0, 0, idempotency_key, scan_status))


def update_batch_submitted_count(batch_id: int) -> None:
    _execute('UPDATE batches SET submitted_count = (SELECT COUNT(*) FROM jobs WHERE batch_id = %s), updated_at = CURRENT_TIMESTAMP WHERE batch_id = %s', (batch_id, batch_id))


def update_job_state(job_id: int, status: Optional[str] = None, stage: Optional[str] = None, progress: Optional[int] = None, warnings: Optional[List[Dict[str, Any]]] = None, error: Optional[str] = None, worker_id: Optional[str] = None, completed: bool = False, scan_status: Optional[str] = None, heartbeat: bool = False) -> None:
    assignments: List[str] = ['updated_at = CURRENT_TIMESTAMP']
    params: List[Any] = []
    if status is not None:
        assignments.append('status = %s')
        params.append(status)
    if stage is not None:
        assignments.append('stage = %s')
        params.append(stage)
    if progress is not None:
        assignments.append('progress = %s')
        params.append(progress)
    if warnings is not None:
        assignments.append('warnings_json = %s')
        params.append(_dumps(warnings))
    if error is not None:
        assignments.append('last_error = %s')
        params.append(error)
    if worker_id is not None:
        assignments.append('worker_id = %s')
        params.append(worker_id)
    if scan_status is not None:
        assignments.append('scan_status = %s')
        params.append(scan_status)
    if heartbeat:
        assignments.append('heartbeat_at = CURRENT_TIMESTAMP')
    if completed:
        assignments.append('completed_at = CURRENT_TIMESTAMP')
    params.append(job_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE job_id = %s", tuple(params))
        conn.commit()


def claim_next_job(worker_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM jobs WHERE status IN (\'queued\', \'retrying\') AND scan_status = \'passed\' AND (available_at IS NULL OR available_at <= CURRENT_TIMESTAMP) ORDER BY created_at ASC LIMIT 1 FOR UPDATE')
        row = cursor.fetchone()
        if not row:
            conn.commit()
            return None
        cursor.execute('UPDATE jobs SET status = %s, stage = %s, worker_id = %s, attempts = COALESCE(attempts, 0) + 1, started_at = COALESCE(started_at, CURRENT_TIMESTAMP), heartbeat_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE job_id = %s', ('running', 'preprocessing', worker_id, row['job_id']))
        conn.commit()
        row['status'] = 'running'
        row['stage'] = 'preprocessing'
        row['worker_id'] = worker_id
        row['attempts'] = int(row.get('attempts') or 0) + 1
        return row


def claim_specific_job(job_id: int, worker_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM jobs WHERE job_id = %s FOR UPDATE', (job_id,))
        row = cursor.fetchone()
        if not row or row.get('status') not in ('queued', 'retrying') or row.get('scan_status') != 'passed':
            conn.commit()
            return None
        cursor.execute('UPDATE jobs SET status = %s, stage = %s, worker_id = %s, attempts = COALESCE(attempts, 0) + 1, started_at = COALESCE(started_at, CURRENT_TIMESTAMP), heartbeat_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE job_id = %s', ('running', 'preprocessing', worker_id, job_id))
        conn.commit()
        row['status'] = 'running'
        row['stage'] = 'preprocessing'
        row['worker_id'] = worker_id
        row['attempts'] = int(row.get('attempts') or 0) + 1
        return row


def reschedule_job(job_id: int, error: str, delay_seconds: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE jobs SET status = %s, stage = %s, last_error = %s, available_at = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s SECOND), updated_at = CURRENT_TIMESTAMP WHERE job_id = %s', ('retrying', 'queued', error, delay_seconds, job_id))
        conn.commit()


def recover_orphaned_jobs(orphaned_seconds: int) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE jobs SET status = \"retrying\", stage = \"queued\", last_error = \"Recovered orphaned running job\", updated_at = CURRENT_TIMESTAMP WHERE status = \"running\" AND heartbeat_at IS NOT NULL AND heartbeat_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s SECOND)', (orphaned_seconds,))
        count = cursor.rowcount
        conn.commit()
        return count


def mark_job_failed(job_id: int, error: str, warnings: Optional[List[Dict[str, Any]]] = None, stage: str = 'failed') -> None:
    update_job_state(job_id, status='failed', stage=stage, progress=100, warnings=warnings or [], error=error, completed=True)


def create_object_record(tenant_id: int, purpose: str, backend: str, object_key: str, original_filename: str, content_type: str, size_bytes: int, checksum_sha256: str, created_by_user_id: Optional[int], batch_id: Optional[int] = None, job_id: Optional[int] = None, quarantine: bool = False) -> int:
    return _execute('INSERT INTO object_storage_metadata (tenant_id, batch_id, job_id, purpose, backend, object_key, original_filename, content_type, size_bytes, checksum_sha256, created_by_user_id, quarantine_flag, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)', (tenant_id, batch_id, job_id, purpose, backend, object_key, original_filename, content_type, size_bytes, checksum_sha256, created_by_user_id, quarantine))


def update_object_binding(object_id: int, batch_id: Optional[int] = None, job_id: Optional[int] = None, purpose: Optional[str] = None, quarantine: Optional[bool] = None) -> None:
    assignments: List[str] = []
    params: List[Any] = []
    if batch_id is not None:
        assignments.append('batch_id = %s')
        params.append(batch_id)
    if job_id is not None:
        assignments.append('job_id = %s')
        params.append(job_id)
    if purpose is not None:
        assignments.append('purpose = %s')
        params.append(purpose)
    if quarantine is not None:
        assignments.append('quarantine_flag = %s')
        params.append(quarantine)
    if not assignments:
        return
    params.append(object_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE object_storage_metadata SET {', '.join(assignments)} WHERE object_id = %s", tuple(params))
        conn.commit()


def get_object_record(object_id: int, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if tenant_id is None:
        return _fetchone('SELECT * FROM object_storage_metadata WHERE object_id = %s LIMIT 1', (object_id,))
    return _fetchone('SELECT * FROM object_storage_metadata WHERE object_id = %s AND tenant_id = %s LIMIT 1', (object_id, tenant_id))


def record_virus_scan(object_id: int, engine: str, status: str, details: Dict[str, Any]) -> int:
    return _execute('INSERT INTO virus_scan_results (object_id, engine, status, details_json, scanned_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)', (object_id, engine, status, _dumps(details)))


def get_job_bundle(job_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone('SELECT j.*, b.batch_guid, b.idempotency_key AS batch_idempotency_key, b.bu_id, bu.tenant_id, jd.jd_title, jd.jd_data_json FROM jobs j JOIN batches b ON b.batch_id = j.batch_id JOIN business_units bu ON bu.bu_id = b.bu_id JOIN job_descriptions jd ON jd.jd_id = j.jd_id WHERE j.job_id = %s LIMIT 1', (job_id,))
    if not row:
        return None
    row['jd_data'] = _loads(row.get('jd_data_json'), {})
    row['warnings'] = _loads(row.get('warnings_json'), [])
    return row

def dead_letter_job(job_id: int, reason: str) -> int:
    return _execute('INSERT INTO dead_letter_queue (job_id, reason, failed_at) VALUES (%s, %s, CURRENT_TIMESTAMP)', (job_id, reason))


def mark_job_failed(job_id: int, error: str, warnings: Optional[List[Dict[str, Any]]] = None, stage: str = 'failed') -> None:
    update_job_state(job_id, status='failed', stage=stage, progress=100, warnings=warnings or [], error=error, completed=True)
    try:
        dead_letter_job(job_id, error)
    except Exception:
        pass


def apply_scan_result(job_id: int, object_id: int, scan_status: str, engine: str, details: Dict[str, Any]) -> None:
    record_virus_scan(object_id, engine, scan_status, details)
    if scan_status == 'passed':
        update_job_state(job_id, status='queued', stage='queued', progress=0, scan_status='passed')
    elif scan_status == 'blocked':
        update_job_state(job_id, status='failed', stage='scan_pending', progress=100, scan_status='blocked', error='Upload blocked by malware scan.', completed=True)
    else:
        update_job_state(job_id, status='scan_pending', stage='scan_pending', progress=0, scan_status=scan_status)


def _billable_usage_for_job(job_id: int) -> Dict[str, int]:
    rows = _fetchall('SELECT meter_type, SUM(quantity) AS quantity FROM usage_events WHERE job_id = %s GROUP BY meter_type', (job_id,))
    return {str(row['meter_type']): int(row.get('quantity') or 0) for row in rows}


def _billable_usage_for_batch(batch_id: int) -> Dict[str, int]:
    rows = _fetchall('SELECT meter_type, SUM(quantity) AS quantity FROM usage_events WHERE batch_id = %s GROUP BY meter_type', (batch_id,))
    return {str(row['meter_type']): int(row.get('quantity') or 0) for row in rows}


def save_job_result(
    *,
    job_id: int,
    batch_id: int,
    tenant_id: int,
    parsed_json: Dict[str, Any],
    validated_json: Dict[str, Any],
    local_score: Dict[str, Any],
    ai_score: Optional[Dict[str, Any]],
    rag_audit: Optional[Dict[str, Any]],
    explanation: Dict[str, Any],
    warnings: List[Dict[str, Any]],
    report_url: Optional[str],
    report_object_id: Optional[int],
    status: str,
    stage: str,
    processed_at: Optional[str],
) -> int:
    structured_explanation = explanation.get('structured_explanation', {}) if isinstance(explanation, dict) else {}
    summary_scores = {
        'local_score': local_score,
        'ai_score': ai_score,
        'rag_audit': rag_audit,
        'final_score': (local_score or {}).get('final_score'),
    }
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO resume_results (
                job_id, batch_id, tenant_id,
                parsed_resume_json, validated_resume_json,
                scores_json, local_score_json, ai_score_json, rag_audit_json,
                explanation_json, structured_explanation_json,
                warnings_json, result_status, result_stage,
                report_url, report_object_id, processed_at, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                batch_id = VALUES(batch_id),
                tenant_id = VALUES(tenant_id),
                parsed_resume_json = VALUES(parsed_resume_json),
                validated_resume_json = VALUES(validated_resume_json),
                scores_json = VALUES(scores_json),
                local_score_json = VALUES(local_score_json),
                ai_score_json = VALUES(ai_score_json),
                rag_audit_json = VALUES(rag_audit_json),
                explanation_json = VALUES(explanation_json),
                structured_explanation_json = VALUES(structured_explanation_json),
                warnings_json = VALUES(warnings_json),
                result_status = VALUES(result_status),
                result_stage = VALUES(result_stage),
                report_url = VALUES(report_url),
                report_object_id = VALUES(report_object_id),
                processed_at = VALUES(processed_at),
                updated_at = CURRENT_TIMESTAMP
            ''',
            (
                job_id,
                batch_id,
                tenant_id,
                _dumps(parsed_json),
                _dumps(validated_json),
                _dumps(summary_scores),
                _dumps(local_score),
                _dumps(ai_score or {}),
                _dumps(rag_audit or {}),
                _dumps(explanation),
                _dumps(structured_explanation),
                _dumps(warnings),
                status,
                stage,
                report_url,
                report_object_id,
                processed_at,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)


def emit_usage_event(tenant_id: int, batch_id: int, job_id: int, meter_type: str, quantity: int = 1, details: Optional[Dict[str, Any]] = None) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO usage_events (tenant_id, batch_id, job_id, meter_type, quantity, details_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE quantity = quantity
            ''',
            (tenant_id, batch_id, job_id, meter_type, quantity, _dumps(details or {})),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)


def list_usage_events(tenant_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    rows = _fetchall('SELECT * FROM usage_events WHERE tenant_id = %s ORDER BY created_at DESC LIMIT %s', (tenant_id, limit))
    for row in rows:
        row['details_json'] = _loads(row.get('details_json'), {})
    return rows


def get_subscription_for_tenant(tenant_id: int) -> Optional[Dict[str, Any]]:
    return _fetchone('SELECT * FROM subscriptions WHERE tenant_id = %s ORDER BY subscription_id DESC LIMIT 1', (tenant_id,))


def list_invoices_for_tenant(tenant_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    return _fetchall('SELECT * FROM invoices WHERE tenant_id = %s ORDER BY issued_at DESC, invoice_id DESC LIMIT %s', (tenant_id, limit))


def list_entitlements_for_tenant(tenant_id: int) -> List[Dict[str, Any]]:
    rows = _fetchall(
        '''
        SELECT se.*, s.service_code, s.service_name, s.service_category
        FROM service_entitlements se
        JOIN services s ON s.service_id = se.service_id
        WHERE se.tenant_id = %s
        ORDER BY s.service_code ASC
        ''',
        (tenant_id,),
    )
    for row in rows:
        row['effective_entitlement'] = _loads(row.get('effective_entitlement'), {})
    return rows


def refresh_batch_status(batch_id: int) -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT
                COUNT(*) AS total_jobs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_jobs,
                SUM(CASE WHEN status IN ('completed', 'completed_with_warnings') THEN 1 ELSE 0 END) AS completed_jobs,
                SUM(CASE WHEN status = 'completed_with_warnings' THEN 1 ELSE 0 END) AS warning_jobs,
                SUM(CASE WHEN status IN ('received', 'scan_pending', 'queued', 'retrying', 'running') THEN 1 ELSE 0 END) AS active_jobs
            FROM jobs
            WHERE batch_id = %s
            ''',
            (batch_id,),
        )
        counts = cursor.fetchone() or {}
        total_jobs = int(counts.get('total_jobs') or 0)
        failed_jobs = int(counts.get('failed_jobs') or 0)
        completed_jobs = int(counts.get('completed_jobs') or 0)
        warning_jobs = int(counts.get('warning_jobs') or 0)
        active_jobs = int(counts.get('active_jobs') or 0)

        if total_jobs == 0:
            status_value = 'received'
        elif active_jobs > 0:
            status_value = 'processing'
        elif failed_jobs == total_jobs:
            status_value = 'failed'
        elif failed_jobs > 0 or warning_jobs > 0:
            status_value = 'completed_with_warnings'
        else:
            status_value = 'completed'

        cursor.execute(
            'UPDATE batches SET status = %s, completed_count = %s, failed_count = %s, updated_at = CURRENT_TIMESTAMP WHERE batch_id = %s',
            (status_value, completed_jobs, failed_jobs, batch_id),
        )
        conn.commit()
        return {
            'batch_id': batch_id,
            'status': status_value,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'warning_jobs': warning_jobs,
            'active_jobs': active_jobs,
        }

def get_batch_summary(batch_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        '''
        SELECT b.*, jd.jd_title, bu.tenant_id
        FROM batches b
        JOIN business_units bu ON bu.bu_id = b.bu_id
        LEFT JOIN job_descriptions jd ON jd.jd_id = b.job_description_id
        WHERE b.batch_id = %s AND bu.tenant_id = %s
        LIMIT 1
        ''',
        (batch_id, tenant_id),
    )
    if not row:
        return None
    row.update(refresh_batch_status(batch_id))
    row['billable_usage'] = _billable_usage_for_batch(batch_id)
    return row


def list_batch_jobs(batch_id: int, tenant_id: int) -> List[Dict[str, Any]]:
    rows = _fetchall(
        '''
        SELECT j.*, bu.tenant_id
        FROM jobs j
        JOIN batches b ON b.batch_id = j.batch_id
        JOIN business_units bu ON bu.bu_id = b.bu_id
        WHERE j.batch_id = %s AND bu.tenant_id = %s
        ORDER BY j.job_id ASC
        ''',
        (batch_id, tenant_id),
    )
    for row in rows:
        row['warnings'] = _loads(row.get('warnings_json'), [])
        row['billable_usage'] = _billable_usage_for_job(int(row['job_id']))
    return rows


def list_jobs_for_tenant(tenant_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    rows = _fetchall(
        '''
        SELECT j.*
        FROM jobs j
        JOIN batches b ON b.batch_id = j.batch_id
        JOIN business_units bu ON bu.bu_id = b.bu_id
        WHERE bu.tenant_id = %s
        ORDER BY j.created_at DESC, j.job_id DESC
        LIMIT %s
        ''',
        (tenant_id, limit),
    )
    for row in rows:
        row['warnings'] = _loads(row.get('warnings_json'), [])
        row['billable_usage'] = _billable_usage_for_job(int(row['job_id']))
    return rows


def get_job_detail(job_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        '''
        SELECT j.*, b.batch_guid, b.batch_id, bu.tenant_id, jd.jd_title
        FROM jobs j
        JOIN batches b ON b.batch_id = j.batch_id
        JOIN business_units bu ON bu.bu_id = b.bu_id
        LEFT JOIN job_descriptions jd ON jd.jd_id = j.jd_id
        WHERE j.job_id = %s AND bu.tenant_id = %s
        LIMIT 1
        ''',
        (job_id, tenant_id),
    )
    if not row:
        return None
    row['warnings'] = _loads(row.get('warnings_json'), [])
    row['billable_usage'] = _billable_usage_for_job(job_id)
    return row


def _format_result_row(row: Dict[str, Any]) -> Dict[str, Any]:
    parsed_resume = _loads(row.get('parsed_resume_json'), {})
    validated_resume = _loads(row.get('validated_resume_json'), {})
    local_score = _loads(row.get('local_score_json'), {})
    ai_score = _loads(row.get('ai_score_json'), {})
    rag_audit = _loads(row.get('rag_audit_json'), {})
    explanation = _loads(row.get('explanation_json'), {})
    structured_explanation = _loads(row.get('structured_explanation_json'), explanation.get('structured_explanation', {}))
    warnings = _loads(row.get('warnings_json'), [])
    return {
        'result_id': row.get('result_id'),
        'job_id': row.get('job_id'),
        'batch_id': row.get('batch_id'),
        'tenant_id': row.get('tenant_id'),
        'status': row.get('result_status') or row.get('status'),
        'stage': row.get('result_stage') or row.get('stage'),
        'warnings': warnings,
        'parsed_resume': parsed_resume,
        'validated_resume': validated_resume,
        'local_score': local_score,
        'ai_score': ai_score if ai_score else None,
        'rag_audit': rag_audit if rag_audit else None,
        'recruiter_summary': explanation.get('recruiter_text_summary', ''),
        'candidate_feedback': explanation.get('candidate_feedback', ''),
        'structured_explanation': structured_explanation,
        'report_url': row.get('report_url'),
        'report_object_id': row.get('report_object_id'),
        'processed_at': row.get('processed_at'),
        'billable_usage': _billable_usage_for_job(int(row['job_id'])),
    }


def get_result_for_job(job_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
    row = _fetchone(
        '''
        SELECT rr.*, j.status, j.stage
        FROM resume_results rr
        JOIN jobs j ON j.job_id = rr.job_id
        JOIN batches b ON b.batch_id = j.batch_id
        JOIN business_units bu ON bu.bu_id = b.bu_id
        WHERE rr.job_id = %s AND bu.tenant_id = %s
        LIMIT 1
        ''',
        (job_id, tenant_id),
    )
    if not row:
        return None
    return _format_result_row(row)


def list_results_for_tenant(tenant_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    rows = _fetchall(
        '''
        SELECT rr.*
        FROM resume_results rr
        JOIN jobs j ON j.job_id = rr.job_id
        JOIN batches b ON b.batch_id = j.batch_id
        JOIN business_units bu ON bu.bu_id = b.bu_id
        WHERE bu.tenant_id = %s
        ORDER BY rr.processed_at DESC, rr.result_id DESC
        LIMIT %s
        ''',
        (tenant_id, limit),
    )
    return [_format_result_row(row) for row in rows]


def get_batch_history(tenant_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    rows = _fetchall(
        '''
        SELECT b.*, jd.jd_title, COUNT(j.job_id) AS total_jobs
        FROM batches b
        JOIN business_units bu ON bu.bu_id = b.bu_id
        LEFT JOIN job_descriptions jd ON jd.jd_id = b.job_description_id
        LEFT JOIN jobs j ON j.batch_id = b.batch_id
        WHERE bu.tenant_id = %s
        GROUP BY b.batch_id, jd.jd_title
        ORDER BY b.created_at DESC, b.batch_id DESC
        LIMIT %s
        ''',
        (tenant_id, limit),
    )
    for row in rows:
        row['billable_usage'] = _billable_usage_for_batch(int(row['batch_id']))
    return rows


def get_monitor_snapshot() -> Dict[str, Any]:
    return {
        'tenants': _fetchall('SELECT * FROM tenants ORDER BY tenant_id ASC'),
        'users': _fetchall('SELECT user_id, email, full_name, status, created_at FROM global_users ORDER BY user_id ASC'),
        'batches': _fetchall('SELECT * FROM batches ORDER BY batch_id DESC LIMIT 200'),
        'jobs': _fetchall('SELECT * FROM jobs ORDER BY job_id DESC LIMIT 500'),
        'results': _fetchall('SELECT result_id, job_id, batch_id, tenant_id, result_status, processed_at FROM resume_results ORDER BY result_id DESC LIMIT 200'),
        'usage_events': _fetchall('SELECT * FROM usage_events ORDER BY usage_event_id DESC LIMIT 200'),
        'billing_events': _fetchall('SELECT * FROM billing_events ORDER BY billing_event_id DESC LIMIT 200'),
    }


def connection_ready() -> bool:
    return bool(test_connection())


def save_job_result(
    *,
    job_id: int,
    batch_id: int,
    tenant_id: int,
    parsed_json: Dict[str, Any],
    validated_json: Dict[str, Any],
    local_score: Dict[str, Any],
    ai_score: Optional[Dict[str, Any]],
    rag_audit: Optional[Dict[str, Any]],
    explanation: Dict[str, Any],
    warnings: List[Dict[str, Any]],
    report_url: Optional[str],
    report_object_id: Optional[int],
    status: str,
    stage: str,
    processed_at: Optional[str],
) -> int:
    structured_explanation = explanation.get('structured_explanation', {}) if isinstance(explanation, dict) else {}
    summary_scores = {
        'local_score': local_score,
        'ai_score': ai_score,
        'rag_audit': rag_audit,
        'final_score': (local_score or {}).get('final_score'),
    }
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT result_id FROM resume_results WHERE job_id = %s LIMIT 1', (job_id,))
        existing = cursor.fetchone()
        if existing:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE resume_results
                SET batch_id = %s,
                    tenant_id = %s,
                    parsed_resume_json = %s,
                    validated_resume_json = %s,
                    scores_json = %s,
                    local_score_json = %s,
                    ai_score_json = %s,
                    rag_audit_json = %s,
                    explanation_json = %s,
                    structured_explanation_json = %s,
                    warnings_json = %s,
                    result_status = %s,
                    result_stage = %s,
                    report_url = %s,
                    report_object_id = %s,
                    processed_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE result_id = %s
                ''',
                (
                    batch_id,
                    tenant_id,
                    _dumps(parsed_json),
                    _dumps(validated_json),
                    _dumps(summary_scores),
                    _dumps(local_score),
                    _dumps(ai_score or {}),
                    _dumps(rag_audit or {}),
                    _dumps(explanation),
                    _dumps(structured_explanation),
                    _dumps(warnings),
                    status,
                    stage,
                    report_url,
                    report_object_id,
                    processed_at,
                    existing['result_id'],
                ),
            )
            conn.commit()
            return int(existing['result_id'])
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO resume_results (
                job_id, batch_id, tenant_id,
                parsed_resume_json, validated_resume_json,
                scores_json, local_score_json, ai_score_json, rag_audit_json,
                explanation_json, structured_explanation_json,
                warnings_json, result_status, result_stage,
                report_url, report_object_id, processed_at, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (
                job_id,
                batch_id,
                tenant_id,
                _dumps(parsed_json),
                _dumps(validated_json),
                _dumps(summary_scores),
                _dumps(local_score),
                _dumps(ai_score or {}),
                _dumps(rag_audit or {}),
                _dumps(explanation),
                _dumps(structured_explanation),
                _dumps(warnings),
                status,
                stage,
                report_url,
                report_object_id,
                processed_at,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)


def emit_usage_event(tenant_id: int, batch_id: int, job_id: int, meter_type: str, quantity: int = 1, details: Optional[Dict[str, Any]] = None) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT usage_event_id FROM usage_events WHERE job_id = %s AND meter_type = %s LIMIT 1', (job_id, meter_type))
        existing = cursor.fetchone()
        if existing:
            return int(existing['usage_event_id'])
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO usage_events (tenant_id, batch_id, job_id, meter_type, quantity, details_json, created_at) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)',
            (tenant_id, batch_id, job_id, meter_type, quantity, _dumps(details or {})),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)
