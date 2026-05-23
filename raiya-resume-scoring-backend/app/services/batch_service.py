"""
RAIYA Batch Service — Batch creation, resume processing, result retrieval,
and the per-batch LangGraph orchestrator (`run_batch`).

`run_batch` is the bridge between FastAPI and LangGraph: it fans out one
graph invocation per resume (each with its own `thread_id`), gathers the
results, then optionally triggers the Pipeline 4 HR email service.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.core.config import settings
from app.models.batch import Batch, MatchResult
from app.models.document import Resume, JobDescription
from app.core.hashing import hash_file, hash_json
from app.core.logging_config import get_logger

logger = get_logger("BatchService")

# Resume PDFs are persisted under storage/resumes/<file_hash>.pdf so the
# orchestrator can re-load them for graph invocation.
_RESUME_STORAGE_DIR = Path("storage") / "resumes"
_JD_STORAGE_DIR = Path("storage") / "jd"


async def create_batch(
    session: AsyncSession,
    jd_id: str,
    org_id: str,
    created_by: str,
    name: Optional[str] = None,
) -> Batch:
    """Create a new scoring batch."""
    batch = Batch(
        jd_id=uuid.UUID(jd_id),
        org_id=uuid.UUID(org_id),
        created_by=uuid.UUID(created_by),
        name=name or f"Batch-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        status="queued",
    )
    session.add(batch)
    await session.commit()
    await session.refresh(batch)
    logger.info(f"Batch created: {batch.id}")
    return batch


async def add_resume_to_batch(
    session: AsyncSession,
    batch_id: str,
    file_bytes: bytes,
    file_name: str,
) -> Resume:
    """Add a resume to a batch. Persists bytes to storage/resumes/<hash>.pdf."""
    file_hash = hash_file(file_bytes)

    # Persist bytes so run_batch can re-load them when invoking the graph.
    _RESUME_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (_RESUME_STORAGE_DIR / f"{file_hash}.pdf").write_bytes(file_bytes)

    resume = Resume(
        batch_id=uuid.UUID(batch_id),
        file_name=file_name,
        file_hash=file_hash,
        content_hash=file_hash,  # Updated after extraction
        status="uploaded",
    )
    session.add(resume)

    # Update batch count
    result = await session.execute(
        select(Batch).where(Batch.id == uuid.UUID(batch_id))
    )
    batch = result.scalar_one_or_none()
    if batch:
        batch.total_resumes = (batch.total_resumes or 0) + 1

    await session.commit()
    await session.refresh(resume)
    logger.info(f"Resume added to batch {batch_id}: {resume.file_id}")
    return resume


async def get_batch_status(session: AsyncSession, batch_id: str) -> Optional[Dict[str, Any]]:
    """Get batch status with counts."""
    result = await session.execute(
        select(Batch).where(Batch.id == uuid.UUID(batch_id))
    )
    batch = result.scalar_one_or_none()
    if not batch:
        return None

    return {
        "id": str(batch.id),
        "name": batch.name,
        "jd_id": str(batch.jd_id),
        "total_resumes": batch.total_resumes,
        "completed": batch.completed,
        "failed": batch.failed,
        "status": batch.status,
        "created_at": batch.created_at.isoformat() if batch.created_at else "",
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


async def get_batch_results(
    session: AsyncSession,
    batch_id: str,
) -> List[Dict[str, Any]]:
    """Get all match results for a batch, ranked by score."""
    result = await session.execute(
        select(MatchResult)
        .where(MatchResult.batch_id == uuid.UUID(batch_id))
        .order_by(MatchResult.final_score.desc().nullslast())
    )
    results = result.scalars().all()

    output = []
    for i, mr in enumerate(results, 1):
        # Get resume for candidate info
        resume_result = await session.execute(
            select(Resume).where(Resume.file_id == mr.resume_file_id)
        )
        resume = resume_result.scalar_one_or_none()

        section_scores = {}
        if mr.final_result_json and isinstance(mr.final_result_json, dict):
            agent_result = mr.final_result_json.get("result", {})
            for key in ("skills_score", "experience_score", "relevant_experience_score",
                        "technologies_score", "qualification_score", "tools_score",
                        "certifications_score", "responsibilities_score", "position_score",
                        "salary_score"):
                section_scores[key.replace("_score", "")] = agent_result.get(key, 0)

        output.append({
            "id": str(mr.id),
            "resume_file_id": str(mr.resume_file_id),
            "candidate_name": resume.candidate_name if resume else "Unknown",
            "candidate_email": resume.candidate_email if resume else "",
            "final_score": mr.final_score,
            "recommendation": mr.recommendation,
            "is_valid": mr.is_valid,
            "hallucinations_detected": mr.hallucinations_detected,
            "math_accuracy": mr.math_accuracy,
            "rank": i,
            "guardrails_applied": mr.guardrails_applied,
            "section_scores": section_scores,
            "scoring_trace": mr.final_result_json.get("result", {}).get("scoring_trace") if mr.final_result_json else None,
            "created_at": mr.created_at.isoformat() if mr.created_at else "",
        })

    return output


# ── Per-batch LangGraph orchestrator ─────────────────────────────────

def _load_resume_bytes(file_hash: str) -> Optional[bytes]:
    """Load persisted resume PDF bytes by file_hash. Returns None if missing."""
    path = _RESUME_STORAGE_DIR / f"{file_hash}.pdf"
    if not path.is_file():
        return None
    return path.read_bytes()


def _load_jd_bytes(file_hash: str) -> Optional[bytes]:
    """Load persisted JD PDF bytes by file_hash. Returns None if missing."""
    path = _JD_STORAGE_DIR / f"{file_hash}.pdf"
    if not path.is_file():
        return None
    return path.read_bytes()


async def _run_single_resume(
    graph,
    context: Dict[str, Any],
    *,
    batch_id: str,
    jd_id: str,
    jd_file_bytes: bytes,
    jd_weights: Optional[Dict[str, Any]],
    hitl_verified: bool,
    resume_file_id: str,
    resume_file_bytes: bytes,
) -> Dict[str, Any]:
    """
    Invoke the LangGraph pipeline for a single resume.

    Each invocation gets its own `thread_id` (= session_id), so per-resume
    checkpoint history stays isolated.
    """
    session_id = f"{batch_id}:{resume_file_id}"
    initial_state: Dict[str, Any] = {
        "batch_id": batch_id,
        "resume_file_id": resume_file_id,
        "jd_id": jd_id,
        "session_id": session_id,
        "jd_file_bytes": jd_file_bytes,
        "resume_file_bytes": resume_file_bytes,
        # If JD weights are already approved at the batch level, short-circuit
        # the JD-side HITL gate so the per-resume run can proceed.
        "hitl_verified": hitl_verified,
    }
    if jd_weights:
        initial_state["jd_weights"] = jd_weights

    config = {"configurable": {"thread_id": session_id}}
    try:
        result = await graph.ainvoke(initial_state, context=context, config=config)
        logger.info(
            "run_batch: resume %s scored final_score=%s",
            resume_file_id,
            (result or {}).get("final_score"),
        )
        return {"resume_file_id": resume_file_id, "status": "completed", "result": result}
    except Exception as exc:
        logger.exception("run_batch: resume %s failed", resume_file_id)
        return {"resume_file_id": resume_file_id, "status": "failed", "error": str(exc)}


async def run_batch(
    batch_id: str,
    graph,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Orchestrate a full batch through the LangGraph pipeline.

    Steps:
      1. Load the batch + its JD bytes + pre-approved weights (if any).
      2. Load all resumes in the batch.
      3. Fan out per-resume `graph.ainvoke(...)` (bounded by MAX_BATCH_SIZE).
      4. Update batch counters and status.
      5. If `settings.AUTO_SEND_INTERVIEW_EMAILS`, trigger
         `email_service.send_interview_emails(batch_id)` once after gather.

    `context` is the LangGraph `Runtime[PipelineContext]` payload — pass
    `app.state.pipeline_context` from the calling route.
    """
    from app.db.database import AsyncSessionLocal
    from app.services import email_service

    batch_uuid = uuid.UUID(batch_id)
    context = context or {}

    async with AsyncSessionLocal() as session:
        batch = (
            await session.execute(select(Batch).where(Batch.id == batch_uuid))
        ).scalar_one_or_none()
        if batch is None:
            logger.warning("run_batch: batch %s not found", batch_id)
            return {"status": "not_found", "batch_id": batch_id}

        if not batch.jd_id:
            logger.error("run_batch: batch %s has no JD", batch_id)
            return {"status": "failed", "error": "missing_jd", "batch_id": batch_id}

        jd = (
            await session.execute(select(JobDescription).where(JobDescription.id == batch.jd_id))
        ).scalar_one_or_none()
        if jd is None:
            return {"status": "failed", "error": "jd_not_found", "batch_id": batch_id}

        jd_file_bytes = _load_jd_bytes(jd.file_hash) if jd.file_hash else None
        if not jd_file_bytes:
            logger.error(
                "run_batch: JD bytes missing for batch %s (expected storage/jd/%s.pdf)",
                batch_id,
                jd.file_hash,
            )
            return {"status": "failed", "error": "jd_bytes_missing", "batch_id": batch_id}

        jd_weights = jd.weights_json if jd.hitl_verified else None
        hitl_verified = bool(jd.hitl_verified)

        resumes = (
            await session.execute(
                select(Resume).where(Resume.batch_id == batch_uuid)
            )
        ).scalars().all()

        # Mark batch as processing.
        await session.execute(
            update(Batch).where(Batch.id == batch_uuid).values(status="processing")
        )
        await session.commit()

    if not resumes:
        logger.info("run_batch: batch %s has no resumes", batch_id)
        return {"status": "empty", "batch_id": batch_id, "completed": 0, "failed": 0}

    # Bound concurrency to MAX_BATCH_SIZE so a misconfigured batch doesn't
    # exhaust the LLM / OCR rate limits.
    max_concurrency = max(1, min(getattr(settings, "MAX_BATCH_SIZE", 200), len(resumes)))
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(resume: Resume):
        resume_bytes = _load_resume_bytes(resume.file_hash)
        if not resume_bytes:
            logger.warning(
                "run_batch: resume bytes missing for %s (hash=%s) — skipping",
                resume.file_id,
                resume.file_hash,
            )
            return {
                "resume_file_id": str(resume.file_id),
                "status": "skipped",
                "error": "bytes_missing",
            }
        async with semaphore:
            return await _run_single_resume(
                graph,
                context,
                batch_id=batch_id,
                jd_id=str(batch.jd_id),
                jd_file_bytes=jd_file_bytes,
                jd_weights=jd_weights,
                hitl_verified=hitl_verified,
                resume_file_id=str(resume.file_id),
                resume_file_bytes=resume_bytes,
            )

    results = await asyncio.gather(*(_bounded(r) for r in resumes))

    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] in ("failed", "skipped"))

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Batch)
            .where(Batch.id == batch_uuid)
            .values(
                completed=completed,
                failed=failed,
                status="completed" if failed == 0 else ("partial" if completed > 0 else "failed"),
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    # Pipeline 4 — batch-level email dispatch.
    email_outcome: Optional[Dict[str, Any]] = None
    if getattr(settings, "AUTO_SEND_INTERVIEW_EMAILS", False) and completed > 0:
        try:
            email_outcome = await email_service.send_interview_emails(batch_id)
        except Exception as exc:
            logger.exception("run_batch: Pipeline 4 email dispatch failed")
            email_outcome = {"status": "failed", "error": str(exc)}

    return {
        "batch_id": batch_id,
        "completed": completed,
        "failed": failed,
        "total": len(resumes),
        "email_outcome": email_outcome,
        "results": results,
    }
