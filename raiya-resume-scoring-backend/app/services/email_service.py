"""
RAIYA Email Service — Async SMTP email sending for Pipeline 4.

Sends interview notification emails to HR recruiters only.
Uses aiosmtplib for non-blocking SMTP, Jinja2 for HTML templates.

Pipeline 4 is *not* a LangGraph node — it is a batch-level operation
invoked by `batch_service.run_batch` after all per-resume graph runs
complete, or manually via `POST /api/v1/email/send-interview-invitations`.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("EmailService")

# ── Template Engine ─────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "email_templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


# ── Core Send Function ──────────────────────────────────────────────

async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a single email via async SMTP.

    Returns:
        {"status": "sent"|"failed", "smtp_response": str, "error": str|None}
    """
    from_email = from_email or getattr(settings, "SMTP_FROM_EMAIL", "noreply@raiya.ai")
    from_name = from_name or getattr(settings, "SMTP_FROM_NAME", "RAIYA Recruitment")
    smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_username = getattr(settings, "SMTP_USERNAME", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")
    use_tls = getattr(settings, "SMTP_USE_TLS", True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = from_email

    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))

    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            smtp = aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                use_tls=False,
                start_tls=use_tls,
            )
            await smtp.connect()
            if smtp_username and smtp_password:
                await smtp.login(smtp_username, smtp_password)
            response = await smtp.send_message(msg)
            await smtp.quit()

            logger.info(f"Email sent to {to_email}: {response}")
            return {
                "status": "sent",
                "smtp_response": str(response),
                "error": None,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            last_error = str(e)
            logger.warning(
                f"Email send attempt {attempt + 1}/{max_retries + 1} failed: {e}"
            )
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    logger.error(f"Email to {to_email} failed after {max_retries + 1} attempts: {last_error}")
    return {
        "status": "failed",
        "smtp_response": "",
        "error": last_error,
        "sent_at": None,
    }


# ── Interview Notification (to HR only) ─────────────────────────────

async def send_interview_notification_to_hr(
    hr_email: str,
    hr_name: str,
    job_title: str,
    candidates: List[Dict[str, Any]],
    batch_id: str,
) -> Dict[str, Any]:
    """
    Send a consolidated interview notification email to the HR recruiter.

    The email contains:
    - Job title and batch information
    - Ranked list of top candidates with scores
    - Candidate contact details for HR to reach out
    - Recommendation tiers
    - Action items for HR

    Candidates do NOT receive any direct email from the system.
    """
    # Sort candidates by score descending
    sorted_candidates = sorted(
        candidates, key=lambda c: c.get("final_score", 0), reverse=True
    )

    # Render HTML template
    try:
        template = _jinja_env.get_template("interview_invitation.html.j2")
        html_body = template.render(
            hr_name=hr_name,
            job_title=job_title,
            batch_id=batch_id,
            candidates=sorted_candidates,
            total_candidates=len(sorted_candidates),
            generated_at=datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
            company_name=getattr(settings, "SMTP_FROM_NAME", "RAIYA Recruitment"),
            score_threshold=getattr(settings, "INTERVIEW_SCORE_THRESHOLD", 70.0),
        )
    except Exception as e:
        logger.error(f"Template render failed: {e}")
        # Fallback to plain HTML
        html_body = _build_fallback_html(
            hr_name, job_title, sorted_candidates, batch_id
        )

    subject = (
        f"[RAIYA] Interview Candidates Ready — {job_title} "
        f"({len(sorted_candidates)} candidate{'s' if len(sorted_candidates) != 1 else ''})"
    )

    result = await send_email(
        to_email=hr_email,
        subject=subject,
        html_body=html_body,
    )

    return {
        **result,
        "hr_email": hr_email,
        "hr_name": hr_name,
        "batch_id": batch_id,
        "job_title": job_title,
        "candidates_included": len(sorted_candidates),
    }


def _build_fallback_html(
    hr_name: str,
    job_title: str,
    candidates: List[Dict[str, Any]],
    batch_id: str,
) -> str:
    """Fallback HTML when Jinja2 template is not available."""
    rows = ""
    for i, c in enumerate(candidates, 1):
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{i}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{c.get('candidate_name', 'N/A')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{c.get('candidate_email', 'N/A')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;font-weight:bold;">{c.get('final_score', 0):.1f}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{c.get('recommendation', 'N/A').title()}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;">
        <h2 style="color:#2563eb;">🎯 Interview Candidates Ready</h2>
        <p>Hello {hr_name},</p>
        <p>The AI screening for <strong>{job_title}</strong> (Batch: {batch_id[:8]}...) is complete.
           Below are the top-ranked candidates recommended for interview:</p>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <thead>
                <tr style="background:#f8fafc;">
                    <th style="padding:8px;text-align:left;">Rank</th>
                    <th style="padding:8px;text-align:left;">Candidate</th>
                    <th style="padding:8px;text-align:left;">Email</th>
                    <th style="padding:8px;text-align:left;">Score</th>
                    <th style="padding:8px;text-align:left;">Rating</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p><strong>Next Steps:</strong> Please review the candidates above and schedule
           interviews at your earliest convenience.</p>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
        <p style="color:#6b7280;font-size:12px;">
            This email was generated by RAIYA AI-Powered Resume Screening.
            Candidates have NOT been contacted directly.
        </p>
    </body>
    </html>
    """


def _recommendation_tier(score: float) -> str:
    """Map a final score to a recommendation tier label."""
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "average"
    if score >= 40:
        return "poor"
    return "rejected"


# ── Batch-level wrapper (the public Pipeline 4 entry point) ──────────

async def send_interview_emails(batch_id: str) -> Dict[str, Any]:
    """
    Send a single consolidated HR notification email for a completed batch.

    This is the canonical Pipeline 4 entry point. It is *not* a LangGraph node:
    it runs after all per-resume graphs in the batch finish (called by
    `batch_service.run_batch`, or manually via the email API route).

    Behaviour:
      - Aggregate `MatchResult.final_score` >= `INTERVIEW_SCORE_THRESHOLD`
        across the batch, take top `INTERVIEW_MAX_CANDIDATES`.
      - If no candidate qualifies, log an `InterviewInvitation` with
        status='skipped' and return early (no SMTP call).
      - Resolve HR via `batches.created_by -> users.email`. If unresolvable,
        log status='failed' and return.
      - Render the Jinja2 template and call `send_interview_notification_to_hr`.
      - Persist outcome to `interview_invitations`.

    Idempotency: callers (the route, the orchestrator) are responsible for
    deciding whether to call this twice for the same batch. The function
    will happily send a second email if invoked twice — see the API route
    for the idempotency guard that checks for existing 'sent' rows.
    """
    # Lazy imports to avoid circulars at module load time.
    from app.db.database import AsyncSessionLocal
    from app.models.batch import Batch, MatchResult
    from app.models.document import Resume, JobDescription
    from app.models.interview import InterviewInvitation
    from app.models.user import User

    score_threshold = getattr(settings, "INTERVIEW_SCORE_THRESHOLD", 70.0)
    max_candidates = getattr(settings, "INTERVIEW_MAX_CANDIDATES", 5)

    async with AsyncSessionLocal() as session:
        # 1. Load batch
        batch_uuid = uuid.UUID(batch_id)
        batch = (
            await session.execute(select(Batch).where(Batch.id == batch_uuid))
        ).scalar_one_or_none()
        if batch is None:
            logger.warning("send_interview_emails: batch %s not found", batch_id)
            return {"status": "failed", "error": "batch_not_found", "batch_id": batch_id}

        # 2. Resolve HR recruiter
        hr_email: Optional[str] = None
        hr_name: str = "HR Recruiter"
        if batch.created_by:
            user = (
                await session.execute(select(User).where(User.id == batch.created_by))
            ).scalar_one_or_none()
            if user:
                hr_email = user.email
                hr_name = user.full_name or hr_name

        if not hr_email:
            logger.warning(
                "send_interview_emails: HR recruiter unresolved for batch %s — skipping",
                batch_id,
            )
            invitation = InterviewInvitation(
                batch_id=batch_uuid,
                hr_email="",
                hr_name=hr_name,
                job_title="Unknown",
                candidates_count=0,
                status="failed",
                error_message="hr_unresolved",
            )
            session.add(invitation)
            await session.commit()
            return {"status": "failed", "error": "hr_unresolved", "batch_id": batch_id}

        # 3. Job title (from JD weights_json if available)
        job_title = "Unknown Position"
        if batch.jd_id:
            jd = (
                await session.execute(select(JobDescription).where(JobDescription.id == batch.jd_id))
            ).scalar_one_or_none()
            if jd and jd.weights_json:
                job_title = jd.weights_json.get("job_title", job_title)

        # 4. Top-N candidates
        rows = (
            await session.execute(
                select(MatchResult)
                .where(MatchResult.batch_id == batch_uuid)
                .where(MatchResult.final_score >= score_threshold)
                .order_by(MatchResult.final_score.desc())
                .limit(max_candidates)
            )
        ).scalars().all()

        if not rows:
            logger.info(
                "send_interview_emails: no candidates >= %.1f for batch %s — skipping send",
                score_threshold,
                batch_id,
            )
            invitation = InterviewInvitation(
                batch_id=batch_uuid,
                hr_email=hr_email,
                hr_name=hr_name,
                job_title=job_title,
                candidates_count=0,
                status="skipped",
                error_message="no_qualified_candidates",
            )
            session.add(invitation)
            await session.commit()
            return {
                "status": "skipped",
                "reason": "no_qualified_candidates",
                "batch_id": batch_id,
                "score_threshold": score_threshold,
            }

        candidates: List[Dict[str, Any]] = []
        for rank, mr in enumerate(rows, 1):
            resume = (
                await session.execute(select(Resume).where(Resume.file_id == mr.resume_file_id))
            ).scalar_one_or_none()
            agent_result = (mr.final_result_json or {}).get("result", {})
            candidates.append({
                "rank": rank,
                "candidate_name": resume.candidate_name if resume else "Unknown",
                "candidate_email": resume.candidate_email if resume else "",
                "final_score": float(mr.final_score or 0),
                "recommendation": _recommendation_tier(mr.final_score or 0),
                "skills_score": agent_result.get("skills_score", 0),
                "experience_score": agent_result.get("experience_score", 0),
                "technologies_score": agent_result.get("technologies_score", 0),
                "qualification_score": agent_result.get("qualification_score", 0),
                "is_valid": bool(mr.is_valid),
                "hallucinations_detected": bool(mr.hallucinations_detected),
            })

        # 5. SMTP send (delegates to existing per-email function)
        email_result = await send_interview_notification_to_hr(
            hr_email=hr_email,
            hr_name=hr_name,
            job_title=job_title,
            candidates=candidates,
            batch_id=batch_id,
        )

        # 6. Persist outcome
        invitation = InterviewInvitation(
            batch_id=batch_uuid,
            hr_email=hr_email,
            hr_name=hr_name,
            job_title=job_title,
            candidates_count=len(candidates),
            email_subject=f"[RAIYA] Interview Candidates — {job_title}",
            status=email_result.get("status", "failed"),
            smtp_response=str(email_result.get("smtp_response", "")),
            error_message=email_result.get("error"),
            candidates_json=candidates,
            sent_at=datetime.now(timezone.utc) if email_result.get("status") == "sent" else None,
        )
        session.add(invitation)
        await session.commit()

    return {
        **email_result,
        "batch_id": batch_id,
        "candidates_count": len(candidates),
        "score_threshold": score_threshold,
    }
