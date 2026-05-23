"""
RAIYA Embedding Schemas — Pydantic models for pgvector embedding tables.

Maps reference_json_schema/:
  - jd_weight_embedding_schema.json     → JDEmbeddingRecord
  - resume_embeddings_schema.json       → ResumeEmbeddingRecord
  - evidence_embeddings_schema.json     → EvidenceEmbeddingRecord

Each schema covers: table record, chunker output, and search result row.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


# ── Shared ───────────────────────────────────────────────────────────

class ChunkerOutputRecord(BaseModel):
    """Common output record produced by split_json_to_chunks()."""
    text: str                                    # serialised JSON string
    dimension: str                               # section name or special tag
    source: str                                  # 'jd', 'resume', or 'rule_based'
    chunk_index: int = Field(..., ge=0)          # 0-based index
    chunk_hash: str                              # SHA-256 hex of text


# ── JD Embeddings ────────────────────────────────────────────────────

JD_DIMENSION_VALUES = Literal[
    "technologies", "skills", "tools", "certifications",
    "experience", "qualification", "position",
    "relevant_experience", "responsibilities", "salary", "domain_fit",
]


class JDEmbeddingRecord(BaseModel):
    """Row in the jd_embeddings pgvector table."""
    id: Optional[int] = None                     # SERIAL, auto-generated
    jd_id: str                                   # jd_content_hash from Phase 14
    chunk_index: int = Field(..., ge=0)
    dimension: str                               # one of JD_DIMENSION_VALUES
    chunk_text: str                              # serialised JSON
    chunk_hash: str                              # SHA-256 hex
    metadata: Optional[Dict[str, Any]] = None    # JSONB metadata
    # embedding vector is not stored in Pydantic — handled by pgvector_client


class JDEmbeddingSearchResult(BaseModel):
    """Row returned by pgvector_client.search_jd_embeddings()."""
    jd_id: str
    chunk_index: int
    dimension: str
    chunk_text: str
    chunk_hash: str
    metadata: Optional[Dict[str, Any]] = None
    similarity: float = Field(..., ge=0.0, le=1.0)


class JDEmbeddingChunkerOutput(ChunkerOutputRecord):
    """JD chunker output — extends base with JD-specific source."""
    source: str = "jd"


# ── Resume Embeddings ───────────────────────────────────────────────

RESUME_DIMENSION_VALUES = Literal[
    "technical_skills", "tool_fit", "experience_fit",
    "education_fit", "certification_fit", "domain_fit",
    "salary", "identity",
]

RESUME_DIMENSION_TO_SECTION = {
    "technical_skills": ["skills", "technologies"],
    "tool_fit": ["tools"],
    "experience_fit": ["experience", "relevant_experience"],
    "education_fit": ["education"],
    "certification_fit": ["certifications"],
    "domain_fit": ["projects", "summary"],
    "salary": ["salary_expectation"],
    "identity": ["name", "email", "contact"],
}


class ResumeEmbeddingRecord(BaseModel):
    """Row in the resume_embeddings pgvector table."""
    id: Optional[int] = None                     # SERIAL, auto-generated
    resume_file_id: str                          # resume document identifier
    chunk_index: int = Field(..., ge=0)
    dimension: str                               # one of RESUME_DIMENSION_VALUES
    chunk_text: str
    chunk_hash: str
    metadata: Optional[Dict[str, Any]] = None


class ResumeEmbeddingSearchResult(BaseModel):
    """Row returned by pgvector_client.search_resume_embeddings()."""
    resume_file_id: str
    chunk_index: int
    dimension: str
    chunk_text: str
    chunk_hash: str
    metadata: Optional[Dict[str, Any]] = None
    similarity: float = Field(..., ge=0.0, le=1.0)


class ResumeEmbeddingChunkerOutput(ChunkerOutputRecord):
    """Resume chunker output — extends base with resume-specific source."""
    source: str = "resume"


# ── Evidence Embeddings ──────────────────────────────────────────────

EVIDENCE_SOURCE_TYPE = Literal["rule_based", "historical"]

EVIDENCE_SECTION_VALUES = Literal[
    "technologies", "skills", "tools", "certifications",
    "experience", "qualification", "position",
    "relevant_experience", "responsibilities", "salary", "summary",
]

EVIDENCE_RULE_IDS = Literal[
    "R001_LOW_COVERAGE",
    "R002_OVERESTIMATION",
    "R003_DENSE_BM25_DIVERGENCE",
    "R004_NO_EXACT_HIGH_HYBRID",
    "R005_MANDATORY_UNMATCHED",
]


class EvidenceEmbeddingRecord(BaseModel):
    """Row in the rag_evidence_embeddings pgvector table."""
    id: Optional[int] = None                     # SERIAL, auto-generated
    evidence_id: str                             # EVD_{jd_id[:8]}
    source_type: str                             # 'rule_based' or 'historical'
    section_name: str                            # section or 'summary'
    chunk_text: str
    chunk_hash: str
    metadata: Optional[Dict[str, Any]] = None


class EvidenceEmbeddingSearchResult(BaseModel):
    """Row returned by pgvector_client.search_evidence_embeddings()."""
    evidence_id: str
    source_type: str
    section_name: str
    chunk_text: str
    chunk_hash: str
    metadata: Optional[Dict[str, Any]] = None
    similarity: float = Field(..., ge=0.0, le=1.0)


class EvidenceEmbeddingChunkerOutput(ChunkerOutputRecord):
    """Evidence chunker output — extends base with evidence-specific fields."""
    evidence_id: str                             # propagated from evidence document
    source_type: str                             # 'rule_based' or 'historical'
    section_name: str                            # section this chunk covers


# ── Label Multiplier Reference Table ─────────────────────────────────

LABEL_MULTIPLIER_TABLE: Dict[str, float] = {
    "mandatory_core_skill": 1.00,
    "critical_requirement": 0.95,
    "important_skill": 0.80,
    "preferred_skill": 0.70,
    "supporting_skill": 0.55,
    "nice_to_have": 0.35,
    "irrelevant": 0.00,
}


# ── Coverage Metric Reference ───────────────────────────────────────

class LabelWeightedCoverageMetric(BaseModel):
    """Reference model for the label_weighted_coverage metric used in evidence chunks."""
    name: str = "label_weighted_coverage"
    formula: str = "(Σ matched_multiplier) / (Σ total_multiplier_budget) × 100"
    fallback: str = "Falls back to hybrid_score × 100 for legacy plain-number criteria"
    value_range: str = "0–100"
