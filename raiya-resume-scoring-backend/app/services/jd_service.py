"""
RAIYA JD Service — JD upload, extraction, weight assignment, HiTL verification.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import JobDescription
from app.core.hashing import hash_file, hash_json
from app.core.logging_config import get_logger

logger = get_logger("JDService")

# JD PDFs are persisted under storage/jd/<file_hash>.pdf so the orchestrator
# (batch_service.run_batch -> _load_jd_bytes) can re-load them when fanning
# out per-resume graph invocations across a batch.
_JD_STORAGE_DIR = Path("storage") / "jd"


async def create_jd_from_upload(
    session: AsyncSession,
    file_bytes: bytes,
    file_name: str,
    org_id: str,
    uploaded_by: str,
) -> JobDescription:
    """Create a JD record from uploaded file. Persists bytes to storage/jd/<hash>.pdf."""
    file_hash = hash_file(file_bytes)

    # Persist bytes so batch_service.run_batch can load them later.
    _JD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (_JD_STORAGE_DIR / f"{file_hash}.pdf").write_bytes(file_bytes)

    jd = JobDescription(
        org_id=uuid.UUID(org_id),
        uploaded_by=uuid.UUID(uploaded_by),
        file_name=file_name,
        file_hash=file_hash,
        content_hash=file_hash,  # Updated after extraction
        status="uploaded",
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    logger.info(f"JD created: {jd.id} from {file_name}")
    return jd


async def create_jd_from_manual(
    session: AsyncSession,
    jd_data: Dict[str, Any],
    weights_data: Dict[str, Any],
    org_id: str,
    uploaded_by: str,
) -> JobDescription:
    """Create a JD record from manually entered data."""
    content_hash = hash_json(jd_data)
    weights_hash = hash_json(weights_data)

    jd = JobDescription(
        org_id=uuid.UUID(org_id),
        uploaded_by=uuid.UUID(uploaded_by),
        file_name="manual_entry",
        file_hash=content_hash,
        content_hash=content_hash,
        extracted_json=jd_data,
        extraction_hash=content_hash,
        normalized_json=jd_data,
        normalized_hash=content_hash,
        weights_json=weights_data,
        weights_hash_pre_hitl=weights_hash,
        weights_hash=weights_hash,
        hitl_verified=True,
        hitl_verified_at=datetime.now(timezone.utc),
        hitl_verified_by=uuid.UUID(uploaded_by),
        status="verified",
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    logger.info(f"Manual JD created: {jd.id}")
    return jd


async def update_jd_weights(
    session: AsyncSession,
    jd_id: str,
    weights_data: Dict[str, Any],
    verified_by: str,
) -> JobDescription:
    """Update JD weights after HiTL verification."""
    result = await session.execute(
        select(JobDescription).where(JobDescription.id == uuid.UUID(jd_id))
    )
    jd = result.scalar_one_or_none()
    if not jd:
        raise ValueError(f"JD not found: {jd_id}")

    weights_hash = hash_json(weights_data)
    jd.weights_json = weights_data
    jd.weights_hash = weights_hash
    jd.hitl_verified = True
    jd.hitl_verified_at = datetime.now(timezone.utc)
    jd.hitl_verified_by = uuid.UUID(verified_by)
    jd.status = "verified"

    await session.commit()
    await session.refresh(jd)
    logger.info(f"JD weights updated: {jd_id}")
    return jd


async def get_jd(session: AsyncSession, jd_id: str) -> Optional[JobDescription]:
    """Get JD by ID."""
    result = await session.execute(
        select(JobDescription).where(JobDescription.id == uuid.UUID(jd_id))
    )
    return result.scalar_one_or_none()


async def persist_weight_assignment(
    session: AsyncSession,
    jd_id: str,
    weights_data: Dict[str, Any],
    raw_weight_metadata: Dict[str, Any],
    normalization_factor: float,
    validation_passed: bool,
) -> JobDescription:
    """
    Persist 14-phase enterprise weight assignment results with full audit metadata.

    Stores:
    - weights_json: Full enterprise schema (rich criteria format)
    - weight_strategy: "ontology_label_criteria_average_normalized"
    - weight_generation_metadata: Per-section audit (raw_weight, criteria_count,
        section_importance_factor, normalization_factor)
    - normalization_factor: TotalRawWeight used as Phase 12 divisor
    - total_raw_weight: Sum of adjusted raw weights before normalization

    Called by assign_weights_node after the LangGraph sub-graph completes.
    """
    result = await session.execute(
        select(JobDescription).where(JobDescription.id == uuid.UUID(jd_id))
    )
    jd = result.scalar_one_or_none()
    if not jd:
        raise ValueError(f"JD not found: {jd_id}")

    weights_hash = hash_json(weights_data)
    # total_raw is the sum of adjusted raw weights (Phase 11 output)
    total_raw = sum(
        m.get("raw_weight", 0) for m in raw_weight_metadata.values()
    )

    jd.weights_json = weights_data
    jd.weights_hash_pre_hitl = weights_hash
    jd.weights_hash = weights_hash
    jd.weight_strategy = "ontology_label_criteria_average_normalized"
    jd.weight_generation_metadata = raw_weight_metadata
    jd.normalization_factor = normalization_factor
    jd.total_raw_weight = total_raw
    jd.status = "weights_assigned"

    await session.commit()
    await session.refresh(jd)
    logger.info(
        "Weight assignment persisted: jd=%s strategy=ontology_label_criteria_average_normalized valid=%s",
        jd_id, validation_passed,
    )
    return jd


async def list_jds(session: AsyncSession, org_id: str):
    """List all JDs for an organization."""
    result = await session.execute(
        select(JobDescription).where(JobDescription.org_id == uuid.UUID(org_id))
        .order_by(JobDescription.created_at.desc())
    )
    return result.scalars().all()
