"""
RAIYA Interview Email Schemas — Pipeline 4: Interview Notification.

Emails are sent ONLY to the HR recruiter (batch creator) with a consolidated
ranked report of top candidates eligible for interview.
Candidates do NOT receive direct emails from the system.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime


# ── Candidate Info (for inclusion in HR email) ───────────────────────

class InterviewCandidate(BaseModel):
    """A top-ranked candidate included in the HR interview notification."""
    rank: int
    candidate_name: str
    candidate_email: Optional[str] = None
    final_score: float
    recommendation: Literal[
        "excellent", "good", "average", "poor", "rejected"
    ]
    # Key section scores for HR quick-reference
    skills_score: float = 0.0
    experience_score: float = 0.0
    technologies_score: float = 0.0
    qualification_score: float = 0.0
    # Validation flags
    is_valid: bool = True
    hallucinations_detected: bool = False
    # Brief strengths summary (generated from explanation_gen)
    strengths_summary: Optional[str] = None


# ── Email Request / Config ───────────────────────────────────────────

class InterviewEmailRequest(BaseModel):
    """Request to trigger interview notification email to HR."""
    batch_id: str
    # Override defaults
    score_threshold: Optional[float] = None       # default: settings.INTERVIEW_SCORE_THRESHOLD
    max_candidates: Optional[int] = None          # default: settings.INTERVIEW_MAX_CANDIDATES
    # Optional custom message from admin
    custom_message: Optional[str] = None
    # Override HR email (defaults to batch creator)
    hr_email_override: Optional[EmailStr] = None


class EmailTemplateConfig(BaseModel):
    """Configuration for the interview notification email template."""
    company_name: str = "RAIYA Recruitment"
    company_logo_url: Optional[str] = None
    interview_instructions: str = (
        "Please review the candidates below and schedule interviews "
        "at your earliest convenience."
    )
    scheduling_link: Optional[str] = None          # e.g. Calendly link
    include_score_breakdown: bool = True           # show section scores in HR email
    include_validation_flags: bool = True          # show validity indicators


# ── Per-Candidate Send Result ────────────────────────────────────────

class InterviewEmailResult(BaseModel):
    """Result of sending the interview notification to HR."""
    hr_email: str
    hr_name: str
    batch_id: str
    job_title: str
    candidates_included: int
    status: Literal["sent", "failed", "queued"]
    smtp_response: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


# ── Batch Response ───────────────────────────────────────────────────

class InterviewEmailBatchResponse(BaseModel):
    """Response after processing interview email notification for a batch."""
    batch_id: str
    job_title: str
    hr_email: str
    total_candidates_qualified: int
    candidates_included_in_email: int
    score_threshold_used: float
    email_result: InterviewEmailResult
    candidates: List[InterviewCandidate] = Field(default_factory=list)


# ── Email History Record ─────────────────────────────────────────────

class InterviewEmailHistoryEntry(BaseModel):
    """A historical record of an interview notification email sent."""
    id: str
    batch_id: str
    job_title: str
    hr_email: str
    hr_name: str
    candidates_count: int
    status: str
    sent_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class InterviewEmailStatusResponse(BaseModel):
    """Status response for email history of a batch."""
    batch_id: str
    total_emails_sent: int
    history: List[InterviewEmailHistoryEntry] = Field(default_factory=list)
