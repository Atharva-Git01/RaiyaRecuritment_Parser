from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PIPELINE_SEQUENCE = (
    'received',
    'scan_pending',
    'queued',
    'preprocessing',
    'scoring',
    'enriching',
    'reporting',
    'completed',
    'completed_with_warnings',
    'failed',
)


@dataclass
class PipelineWarning:
    code: str
    message: str
    stage: str
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'code': self.code,
            'message': self.message,
            'stage': self.stage,
        }
        if self.detail:
            payload['detail'] = self.detail
        return payload


@dataclass
class PipelineContext:
    resume_path: Path
    job_id: Optional[int] = None
    batch_id: Optional[int] = None
    jd: Optional[Dict[str, Any]] = None
    tmp_dir: Optional[Path] = None
    results_dir: Optional[Path] = None
    reports_dir: Optional[Path] = None


@dataclass
class PipelineArtifacts:
    raw_text: str = ''
    normalized_text: str = ''
    parsed_json: Dict[str, Any] = field(default_factory=dict)
    validated_json: Dict[str, Any] = field(default_factory=dict)
    scoring_ready: Dict[str, Any] = field(default_factory=dict)
    local_score: Dict[str, Any] = field(default_factory=dict)
    ai_score: Optional[Dict[str, Any]] = None
    rag_audit: Optional[Dict[str, Any]] = None
    explanation: Dict[str, Any] = field(default_factory=dict)
    pdf_report: Optional[str] = None
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    status: str = 'queued'
    stage: str = 'queued'
    processed_at: Optional[str] = None

    def add_warning(self, code: str, message: str, stage: str, detail: Optional[str] = None) -> None:
        self.warnings.append(PipelineWarning(code=code, message=message, stage=stage, detail=detail).to_dict())

    def finalize(self) -> None:
        self.processed_at = datetime.now(timezone.utc).isoformat()
        if self.status not in {'failed', 'completed', 'completed_with_warnings'}:
            self.status = 'completed_with_warnings' if self.warnings else 'completed'
        if self.status in {'completed', 'completed_with_warnings'}:
            self.stage = self.status

    def to_result_dict(self, job_id: Optional[int] = None, batch_id: Optional[int] = None) -> Dict[str, Any]:
        explanation = self.explanation or {}
        return {
            'job_id': job_id,
            'batch_id': batch_id,
            'status': self.status,
            'stage': self.stage,
            'warnings': list(self.warnings),
            'raw_text': self.raw_text,
            'normalized_text': self.normalized_text,
            'parsed_resume': self.parsed_json,
            'validated_resume': self.validated_json,
            'scoring_ready': self.scoring_ready,
            'local_score': self.local_score,
            'ai_score': self.ai_score,
            'rag_audit': self.rag_audit,
            'recruiter_summary': explanation.get('recruiter_text_summary', ''),
            'candidate_feedback': explanation.get('candidate_feedback', ''),
            'structured_explanation': explanation.get('structured_explanation', {}),
            'explanation': explanation,
            'report_url': self.pdf_report,
            'pdf_report': self.pdf_report,
            'processed_at': self.processed_at,
            'parsed': self.parsed_json,
            'validated': self.validated_json,
        }


class PipelineExecutionError(RuntimeError):
    def __init__(self, message: str, artifacts: PipelineArtifacts):
        super().__init__(message)
        self.artifacts = artifacts
