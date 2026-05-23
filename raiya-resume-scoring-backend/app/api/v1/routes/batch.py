"""
RAIYA Batch Routes — Batch creation, resume upload, results, processing.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.services.batch_service import (
    create_batch,
    add_resume_to_batch,
    get_batch_status,
    get_batch_results,
    run_batch,
)

router = APIRouter(prefix="/batch", tags=["Batch Processing"])


@router.post("/create")
async def create_scoring_batch(
    jd_id: str,
    org_id: str,
    created_by: str,
    name: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new scoring batch."""
    batch = await create_batch(db, jd_id, org_id, created_by, name)
    return {
        "batch_id": str(batch.id),
        "name": batch.name,
        "status": batch.status,
    }


@router.post("/{batch_id}/upload-resumes")
async def upload_resumes(
    batch_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload resumes to a batch."""
    uploaded = []
    for file in files:
        file_bytes = await file.read()
        resume = await add_resume_to_batch(db, batch_id, file_bytes, file.filename)
        uploaded.append({
            "file_id": str(resume.file_id),
            "file_name": resume.file_name,
            "file_hash": resume.file_hash,
        })
    return {"batch_id": batch_id, "uploaded": len(uploaded), "resumes": uploaded}


@router.post("/{batch_id}/start")
async def start_batch_processing(
    batch_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start processing a batch through the LangGraph scoring pipeline.

    Returns immediately after queuing a background task; clients poll
    `/batch/{batch_id}/status` for progress.
    """
    status_data = await get_batch_status(db, batch_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Batch not found")

    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="LangGraph pipeline not initialised — check the app lifespan.",
        )

    pipeline_context = getattr(request.app.state, "pipeline_context", None) or {}
    background_tasks.add_task(run_batch, batch_id, graph, pipeline_context)

    return {
        "batch_id": batch_id,
        "status": "processing",
        "message": "Batch processing queued",
        "total_resumes": status_data["total_resumes"],
    }


@router.get("/{batch_id}/status")
async def batch_status(batch_id: str, db: AsyncSession = Depends(get_db)):
    """Get batch processing status."""
    status_data = await get_batch_status(db, batch_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Batch not found")
    return status_data


@router.get("/{batch_id}/results")
async def batch_results(batch_id: str, db: AsyncSession = Depends(get_db)):
    """Get batch results with ranked candidates."""
    status_data = await get_batch_status(db, batch_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Batch not found")

    results = await get_batch_results(db, batch_id)
    return {
        "batch": status_data,
        "results": results,
        "total_count": len(results),
    }
