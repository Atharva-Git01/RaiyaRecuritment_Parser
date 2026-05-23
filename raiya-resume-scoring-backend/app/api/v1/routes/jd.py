"""
RAIYA JD Routes — JD upload, manual creation, weight management.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.db.database import get_db
from app.services.jd_service import create_jd_from_upload, create_jd_from_manual, update_jd_weights, get_jd, list_jds
from app.guardrails_config.weight_guards import validate_jd_weights

router = APIRouter(prefix="/jd", tags=["Job Descriptions"])


@router.post("/upload")
async def upload_jd(
    file: UploadFile = File(...),
    org_id: str = Form(...),
    uploaded_by: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a JD PDF for extraction."""
    file_bytes = await file.read()
    jd = await create_jd_from_upload(db, file_bytes, file.filename, org_id, uploaded_by)
    return {
        "id": str(jd.id),
        "file_name": jd.file_name,
        "file_hash": jd.file_hash,
        "status": jd.status,
    }


@router.post("/create")
async def create_jd_manual(
    jd_data: dict,
    weights_data: dict,
    org_id: str,
    uploaded_by: str,
    db: AsyncSession = Depends(get_db),
):
    """Create a JD from manual entry with weights."""
    # Validate weights
    valid, errors = validate_jd_weights(weights_data)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    jd = await create_jd_from_manual(db, jd_data, weights_data, org_id, uploaded_by)
    return {
        "id": str(jd.id),
        "status": jd.status,
        "weights_hash": jd.weights_hash,
        "hitl_verified": jd.hitl_verified,
    }


@router.put("/{jd_id}/weights")
async def update_weights(
    jd_id: str,
    weights_data: dict,
    verified_by: str,
    db: AsyncSession = Depends(get_db),
):
    """Update JD weights after HiTL verification."""
    valid, errors = validate_jd_weights(weights_data)
    if not valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        jd = await update_jd_weights(db, jd_id, weights_data, verified_by)
        return {
            "id": str(jd.id),
            "weights_hash": jd.weights_hash,
            "hitl_verified": jd.hitl_verified,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{jd_id}")
async def get_jd_detail(jd_id: str, db: AsyncSession = Depends(get_db)):
    """Get JD details."""
    jd = await get_jd(db, jd_id)
    if not jd:
        raise HTTPException(status_code=404, detail="JD not found")
    return {
        "id": str(jd.id),
        "file_name": jd.file_name,
        "status": jd.status,
        "extracted_json": jd.extracted_json,
        "weights_json": jd.weights_json,
        "hitl_verified": jd.hitl_verified,
        "created_at": jd.created_at.isoformat() if jd.created_at else "",
    }


@router.get("/")
async def list_job_descriptions(org_id: str, db: AsyncSession = Depends(get_db)):
    """List all JDs for an organization."""
    jds = await list_jds(db, org_id)
    return [
        {
            "id": str(jd.id),
            "file_name": jd.file_name,
            "status": jd.status,
            "hitl_verified": jd.hitl_verified,
            "created_at": jd.created_at.isoformat() if jd.created_at else "",
        }
        for jd in jds
    ]
