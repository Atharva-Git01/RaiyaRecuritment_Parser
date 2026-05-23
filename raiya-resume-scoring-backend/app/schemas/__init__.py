from app.schemas.resume import ResumeExtractionSchema
from app.schemas.jd import JDExtractionSchema
from app.schemas.jd_weights import JDWeightsSchema
from app.schemas.extracted_rules import ExtractedSectionRule
from app.schemas.deterministic_output import DeterministicValidatorOutput
from app.schemas.mathematical_report import MathematicalValidatorReport
from app.schemas.rule_based_evidence import RuleBasedEvidenceSchema
from app.schemas.final_result import FinalResultScoringAgent
from app.schemas.final_validation_report import FinalValidationReport
from app.schemas.reasoning import ReasoningOutput

# Embedding schemas (maps 3 pgvector table reference schemas)
from app.schemas.embedding_schemas import (
    JDEmbeddingRecord, JDEmbeddingSearchResult,
    ResumeEmbeddingRecord, ResumeEmbeddingSearchResult,
    EvidenceEmbeddingRecord, EvidenceEmbeddingSearchResult,
    ChunkerOutputRecord,
)

# Pipeline 4 — Interview email notification schemas
from app.schemas.interview_email import (
    InterviewEmailRequest, InterviewCandidate,
    InterviewEmailResult, InterviewEmailBatchResponse,
    EmailTemplateConfig,
)
