from __future__ import annotations

import shutil
import socket
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from app import repositories
from app.config import ensure_runtime_directories, get_settings
from app.migrations import ensure_runtime_ready
from app.pipeline.contracts import PipelineExecutionError
from app.pipeline.stages import ResumePipeline
from app.queue_backends import get_queue_backend
from app.storage_backends import get_storage_backend


def _worker_id() -> str:
    return f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def _job_output_dirs(job_id: int) -> Dict[str, Path]:
    settings = get_settings()
    root = settings.local_storage_root / 'jobs' / str(job_id)
    tmp_dir = root / 'tmp'
    results_dir = root / 'results'
    reports_dir = root / 'reports'
    for directory in (tmp_dir, results_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return {'tmp': tmp_dir, 'results': results_dir, 'reports': reports_dir}


def _cleanup_job_dirs(job_id: int) -> None:
    root = get_settings().local_storage_root / 'jobs' / str(job_id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def _persist_report(job_bundle: Dict[str, object], local_report_path: Optional[str], storage) -> tuple[Optional[int], Optional[str]]:
    if not local_report_path:
        return None, None
    report_path = Path(local_report_path)
    if not report_path.exists():
        return None, None
    tenant_id = int(job_bundle['tenant_id'])
    batch_guid = str(job_bundle['batch_guid'])
    object_key = f"tenants/{tenant_id}/batches/{batch_guid}/reports/{uuid.uuid4().hex}{report_path.suffix.lower() or '.pdf'}"
    stored = storage.store_file(object_key, report_path, 'application/pdf', quarantine=False)
    object_id = repositories.create_object_record(
        tenant_id=tenant_id,
        batch_id=int(job_bundle['batch_id']),
        job_id=int(job_bundle['job_id']),
        purpose='report',
        backend=stored.backend,
        object_key=stored.object_key,
        original_filename=report_path.name,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        checksum_sha256='',
        created_by_user_id=job_bundle.get('requester_user_id'),
        quarantine=False,
    )
    return object_id, f"/api/files/{object_id}"


def process_job(job_row: Dict[str, object], worker_id: str, queue, storage) -> None:
    job_id = int(job_row['job_id'])
    attempts = int(job_row.get('attempts') or 0)
    settings = get_settings()
    materialized_resume: Optional[Path] = None
    output_dirs: Optional[Dict[str, Path]] = None
    job_bundle: Optional[Dict[str, object]] = None
    try:
        repositories.update_job_state(job_id, status='running', stage='preprocessing', progress=5, worker_id=worker_id, heartbeat=True)
        job_bundle = repositories.get_job_bundle(job_id)
        if not job_bundle:
            raise RuntimeError(f'Job {job_id} could not be loaded from the database.')

        object_id = int(job_bundle['resume_file_id'])
        object_record = repositories.get_object_record(object_id, tenant_id=int(job_bundle['tenant_id']))
        if not object_record:
            raise RuntimeError(f'Resume object {object_id} was not found.')

        materialized_resume = storage.materialize(
            str(object_record['object_key']),
            suffix=Path(str(job_bundle.get('resume_filename') or 'resume.pdf')).suffix or '.pdf',
            quarantine=bool(object_record.get('quarantine_flag')),
        )
        output_dirs = _job_output_dirs(job_id)
        pipeline = ResumePipeline()
        repositories.update_job_state(job_id, status='running', stage='preprocessing', progress=15, worker_id=worker_id, heartbeat=True)
        result = pipeline.run(
            resume_path=materialized_resume,
            jd=job_bundle.get('jd_data') or {},
            output_dirs=output_dirs,
            job_id=job_id,
            batch_id=int(job_bundle['batch_id']),
        )
        repositories.update_job_state(job_id, status=result['status'], stage=result['stage'], progress=95, warnings=result['warnings'], worker_id=worker_id, heartbeat=True)
        report_object_id, report_url = _persist_report(job_bundle, result.get('report_url'), storage)
        repositories.save_job_result(
            job_id=job_id,
            batch_id=int(job_bundle['batch_id']),
            tenant_id=int(job_bundle['tenant_id']),
            parsed_json=result.get('parsed_resume') or {},
            validated_json=result.get('validated_resume') or {},
            local_score=result.get('local_score') or {},
            ai_score=result.get('ai_score'),
            rag_audit=result.get('rag_audit'),
            explanation=result.get('explanation') or {},
            warnings=result.get('warnings') or [],
            report_url=report_url,
            report_object_id=report_object_id,
            status=result['status'],
            stage=result['stage'],
            processed_at=result.get('processed_at'),
        )
        repositories.update_job_state(job_id, status=result['status'], stage=result['stage'], progress=100, warnings=result.get('warnings') or [], worker_id=worker_id, heartbeat=True, completed=True)
        repositories.emit_usage_event(int(job_bundle['tenant_id']), int(job_bundle['batch_id']), job_id, 'resume_processed', quantity=1, details={'status': result['status']})
        ai_score = result.get('ai_score') or {}
        if ai_score.get('status') == 'completed':
            repositories.emit_usage_event(int(job_bundle['tenant_id']), int(job_bundle['batch_id']), job_id, 'ai_enrichment_completed', quantity=1, details={'status': 'completed'})
        repositories.refresh_batch_status(int(job_bundle['batch_id']))
    except PipelineExecutionError as exc:
        warnings = exc.artifacts.warnings
        error_text = str(exc)
        if attempts >= settings.max_job_attempts:
            repositories.mark_job_failed(job_id, error_text, warnings=warnings, stage=exc.artifacts.stage or 'failed')
            if job_bundle:
                repositories.refresh_batch_status(int(job_bundle['batch_id']))
        else:
            queue.reschedule(job_id, error_text, settings.retry_backoff_seconds * max(attempts, 1))
            repositories.update_job_state(job_id, warnings=warnings, worker_id=worker_id)
    except Exception as exc:
        error_text = str(exc)
        if attempts >= settings.max_job_attempts:
            repositories.mark_job_failed(job_id, error_text, warnings=[], stage='failed')
            if job_bundle:
                repositories.refresh_batch_status(int(job_bundle['batch_id']))
        else:
            queue.reschedule(job_id, error_text, settings.retry_backoff_seconds * max(attempts, 1))
    finally:
        if materialized_resume and materialized_resume.exists():
            shutil.rmtree(materialized_resume.parent, ignore_errors=True)
        if output_dirs:
            _cleanup_job_dirs(job_id)


def run_forever() -> None:
    ensure_runtime_ready()
    ensure_runtime_directories()
    settings = get_settings()
    storage = get_storage_backend(settings)
    queue = get_queue_backend(settings)
    worker_id = _worker_id()
    while True:
        repositories.recover_orphaned_jobs(settings.orphaned_job_seconds)
        job_row = queue.claim_next(worker_id)
        if not job_row:
            time.sleep(settings.poll_interval_seconds)
            continue
        process_job(job_row, worker_id, queue, storage)


if __name__ == '__main__':
    run_forever()
