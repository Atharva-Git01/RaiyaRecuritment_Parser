"""
RAIYA Pipeline 1 Node — Extract Resume.
Uses docstrange from resume_extraction_normalization module for PDF extraction,
then validates via the Pydantic schema from the same module.

Imports:
  - resume_extraction_normalization.modules.hashing (sha256_bytes)
  - resume_extraction_normalization.modules.resume_schema_validation (validate_resume)
  - resume_extraction_normalization.main (RESUME_EXTRACTION_SCHEMA)
"""

import sys
from pathlib import Path
from typing import Dict, Any

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.ocr_tool import extract_pdf_with_ocr
from app.core.hashing import hash_file, hash_json
from app.core.logging_config import get_logger

logger = get_logger("ExtractResumeNode")

# ── Import resume validation from existing module ────────────────────
_BACKEND_ROOT = Path(__file__).resolve().parents[4]  # raiya-resume-scoring-backend/
_RESUME_MODULE = _BACKEND_ROOT / "resume_extraction_normalization"
if str(_RESUME_MODULE) not in sys.path:
    sys.path.insert(0, str(_RESUME_MODULE))

try:
    from modules.resume_schema_validation import validate_resume, ValidatedResumeSchema
    _HAS_RESUME_VALIDATOR = True
    logger.info("Resume schema validator loaded from resume_extraction_normalization")
except ImportError as e:
    _HAS_RESUME_VALIDATOR = False
    logger.warning(f"Resume schema validator not available: {e}")


async def extract_resume_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Pipeline 1 Step 1: Extract resume PDF using Nanonets OCR.
    Then validate using resume_extraction_normalization Pydantic schemas.

    Input: resume_file_bytes
    Output: resume_parsed (resume_pdf_extraction_schema), resume_content_hash
    """
    file_bytes = state.get("resume_file_bytes")
    if not file_bytes:
        return {
            "errors": state.get("errors", []) + ["No resume file bytes provided"],
        }

    file_hash = hash_file(file_bytes)

    try:
        # Step 1: OCR extraction
        extracted = await extract_pdf_with_ocr(
            file_bytes=file_bytes,
            file_hash=file_hash,
            document_type="resume",
        )

        # Step 2: Schema validation via resume_extraction_normalization
        if _HAS_RESUME_VALIDATOR:
            validated_resume, report = validate_resume(extracted)
            if validated_resume:
                extracted = validated_resume.model_dump(exclude_none=True)
                logger.info(
                    f"Resume validation PASSED: "
                    f"{report.populated_fields}/{report.total_fields} fields"
                )
            else:
                logger.warning(
                    f"Resume validation FAILED, using raw extraction: "
                    f"{report.errors[:3]}"
                )

        content_hash = hash_json(extracted)

        # Add pipeline metadata
        if "pipeline_metadata" not in extracted:
            extracted["pipeline_metadata"] = {}
        extracted["pipeline_metadata"]["resume_content_hash"] = content_hash

        logger.info(f"Resume extracted: {content_hash[:20]}...")

        return {
            "resume_file_hash": file_hash,
            "resume_parsed": extracted,
            "resume_content_hash": content_hash,
            "agent_state": "VALIDATING_INPUT",
        }
    except Exception as e:
        logger.error(f"Resume extraction failed: {e}")
        return {
            "errors": state.get("errors", []) + [f"Resume extraction failed: {str(e)}"],
            "agent_state": "FAILED",
        }
