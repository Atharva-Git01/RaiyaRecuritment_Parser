"""
RAIYA Pipeline 2 Node — Extract JD.
Uses DocStrange standard extract_data() — no custom JSON schema imposed.

Architecture:
    JD PDF → DocStrange extract_data() → Flat JSON → pipeline_metadata injection
    The flat JSON is passed directly to jd_normalize.py (Pipeline 2, Phase 2–3).
"""

from langgraph.runtime import Runtime

from app.agents import PipelineContext, PipelineState
from app.agents.tools.ocr_tool import extract_pdf_with_ocr
from app.core.hashing import hash_file, hash_json
from app.core.logging_config import get_logger

logger = get_logger("ExtractJDNode")


async def extract_jd_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Extract JD PDF using DocStrange standard flat JSON output.
    No custom schema — extract_data() returns native structured entities.
    """
    file_bytes = state.get("jd_file_bytes")
    if not file_bytes:
        return {"errors": state.get("errors", []) + ["No JD file bytes"]}

    file_hash = hash_file(file_bytes)
    try:
        extracted = await extract_pdf_with_ocr(file_bytes, file_hash, "jd")
        content_hash = hash_json(extracted)
        if "pipeline_metadata" not in extracted:
            extracted["pipeline_metadata"] = {}
        extracted["pipeline_metadata"]["jd_content_hash"] = content_hash
        extracted["pipeline_metadata"]["extraction_method"] = "docstrange_standard"

        return {
            "jd_file_hash": file_hash,
            "jd_extracted": extracted,
            "jd_content_hash": content_hash,
            "agent_state": "VALIDATING_INPUT",
        }
    except Exception as e:
        logger.error(f"JD extraction failed: {e}")
        return {
            "errors": state.get("errors", []) + [str(e)],
            "agent_state": "FAILED",
        }
