"""
RAIYA Email API Routes — Interview email notification endpoints.

All emails go ONLY to the HR recruiter. Candidates are never contacted directly.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging_config import get_logger
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.batch import Batch, MatchResult
from app.models.document import Resume
from app.models.user import User
from app.models.interview import InterviewInvitation
from app.schemas.interview_email import (
    InterviewEmailRequest,
    InterviewEmailBatchResponse,
    InterviewEmailStatusResponse,
    InterviewEmailHistoryEntry,
    InterviewCandidate,
)
from app.services.email_service import send_interview_notification_to_hr
from app.core.config import settings

logger = get_logger("EmailRoutes")

router = APIRouter(prefix="/email", tags=["Email — Interview Notifications"])


@router.post(
    "/send-interview-invitations",
    response_model=InterviewEmailBatchResponse,
    summary="Send interview notification to HR",
    description=(
        "Manually trigger an interview notification email to the HR recruiter "
        "for a specific batch. Email contains a ranked list of top candidates. "
        "Candidates are NOT contacted directly."
    ),
)
async def send_interview_invitations(
    request: InterviewEmailRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send interview notification email to the HR recruiter for a batch."""
    batch_id = request.batch_id

    # Validate batch exists
    batch_result = await session.execute(
        select(Batch).where(Batch.id == uuid.UUID(batch_id))
    )
    batch = batch_result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Resolve HR info
    hr_email = request.hr_email_override
    hr_name = "HR Recruiter"
    if not hr_email and batch.created_by:
        user_result = await session.execute(
            select(User).where(User.id == batch.created_by)
        )
        user = user_result.scalar_one_or_none()
        if user:
            hr_email = user.email
            hr_name = user.full_name

    if not hr_email:
        raise HTTPException(
            status_code=400,
            detail="Could not determine HR email. Provide hr_email_override.",
        )

    # Get match results
    score_threshold = request.score_threshold or getattr(
        settings, "INTERVIEW_SCORE_THRESHOLD", 70.0
    )
    max_candidates = request.max_candidates or getattr(
        settings, "INTERVIEW_MAX_CANDIDATES", 5
    )

    results = await session.execute(
        select(MatchResult)
        .where(MatchResult.batch_id == uuid.UUID(batch_id))
        .where(MatchResult.final_score >= score_threshold)
        .order_by(MatchResult.final_score.desc())
        .limit(max_candidates)
    )
    match_results = results.scalars().all()

    if not match_results:
        raise HTTPException(
            status_code=404,
            detail=f"No candidates found with score >= {score_threshold}",
        )

    # Build candidate list
    candidates = []
    for i, mr in enumerate(match_results, 1):
        resume_result = await session.execute(
            select(Resume).where(Resume.file_id == mr.resume_file_id)
        )
        resume = resume_result.scalar_one_or_none()
        agent_result = (mr.final_result_json or {}).get("result", {})

        candidates.append(InterviewCandidate(
            rank=i,
            candidate_name=resume.candidate_name if resume else "Unknown",
            candidate_email=resume.candidate_email if resume else None,
            final_score=mr.final_score or 0,
            recommendation=_get_recommendation(mr.final_score or 0),
            skills_score=agent_result.get("skills_score", 0),
            experience_score=agent_result.get("experience_score", 0),
            technologies_score=agent_result.get("technologies_score", 0),
            qualification_score=agent_result.get("qualification_score", 0),
            is_valid=mr.is_valid or False,
            hallucinations_detected=mr.hallucinations_detected or False,
        ))

    # Get job title from JD
    from app.models.document import JobDescription
    jd_result = await session.execute(
        select(JobDescription).where(JobDescription.id == batch.jd_id)
    )
    jd = jd_result.scalar_one_or_none()
    job_title = "Unknown Position"
    if jd and jd.weights_json:
        job_title = jd.weights_json.get("job_title", "Unknown Position")

    # Send email to HR
    candidate_dicts = [c.model_dump() for c in candidates]
    email_result = await send_interview_notification_to_hr(
        hr_email=hr_email,
        hr_name=hr_name,
        job_title=job_title,
        candidates=candidate_dicts,
        batch_id=batch_id,
    )

    # Log the invitation
    invitation = InterviewInvitation(
        batch_id=uuid.UUID(batch_id),
        hr_email=hr_email,
        hr_name=hr_name,
        job_title=job_title,
        candidates_count=len(candidates),
        email_subject=f"[RAIYA] Interview Candidates — {job_title}",
        status=email_result.get("status", "failed"),
        smtp_response=email_result.get("smtp_response", ""),
        candidates_json=[c.model_dump() for c in candidates],
    )
    session.add(invitation)
    await session.commit()

    return InterviewEmailBatchResponse(
        batch_id=batch_id,
        job_title=job_title,
        hr_email=hr_email,
        total_candidates_qualified=len(match_results),
        candidates_included_in_email=len(candidates),
        score_threshold_used=score_threshold,
        email_result=email_result,
        candidates=candidates,
    )


@router.get(
    "/{batch_id}/status",
    response_model=InterviewEmailStatusResponse,
    summary="Get email notification status for a batch",
)
async def get_email_status(
    batch_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the interview email notification history for a batch."""
    result = await session.execute(
        select(InterviewInvitation)
        .where(InterviewInvitation.batch_id == uuid.UUID(batch_id))
        .order_by(InterviewInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    history = [
        InterviewEmailHistoryEntry(
            id=str(inv.id),
            batch_id=str(inv.batch_id),
            job_title=inv.job_title or "",
            hr_email=inv.hr_email or "",
            hr_name=inv.hr_name or "",
            candidates_count=inv.candidates_count or 0,
            status=inv.status or "unknown",
            sent_at=inv.sent_at.isoformat() if inv.sent_at else None,
            created_at=inv.created_at.isoformat() if inv.created_at else "",
        )
        for inv in invitations
    ]

    return InterviewEmailStatusResponse(
        batch_id=batch_id,
        total_emails_sent=sum(1 for h in history if h.status == "sent"),
        history=history,
    )


def _get_recommendation(score: float) -> str:
    if score >= 85:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 55:
        return "average"
    elif score >= 40:
        return "poor"
    return "rejected"
