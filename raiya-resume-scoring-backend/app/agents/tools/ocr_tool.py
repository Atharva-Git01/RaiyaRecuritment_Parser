"""
RAIYA OCR Tool — Nanonets DocStrange OCR integration.
Extracts structured JSON from PDF documents. No raw_text storage.
"""

import httpx
import json
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.hashing import hash_file
from app.db.redis_client import cache_get, cache_set, CacheKeys
from app.core.logging_config import get_logger

logger = get_logger("OCRTool")


async def extract_pdf_with_ocr(
    file_bytes: bytes,
    file_hash: Optional[str] = None,
    document_type: str = "resume",
) -> Dict[str, Any]:
    """
    Extract structured JSON from a PDF using Nanonets DocStrange OCR.
    
    Args:
        file_bytes: Raw PDF bytes
        file_hash: Pre-computed SHA-256 hash (optional)
        document_type: 'resume' or 'jd'
    
    Returns:
        Structured JSON extraction result.
    """
    if not file_hash:
        file_hash = hash_file(file_bytes)

    # ── Check Redis cache ────────────────────────────────────────
    cache_key = CacheKeys.ocr(file_hash)
    cached = await cache_get(cache_key)
    if cached:
        logger.info(f"OCR cache HIT: {file_hash[:20]}...")
        return json.loads(cached)

    # ── Call Nanonets DocStrange ──────────────────────────────────
    logger.info(f"OCR extraction starting for {document_type}: {file_hash[:20]}...")

    try:
        # DocStrange API call
        from docstrange import DocStrange
        
        client = DocStrange(api_key=settings.NANONETS_DOCSTRANGE_API_KEY)
        result = client.parse(file_bytes, output_format="json")
        
        if isinstance(result, str):
            extracted = json.loads(result)
        elif isinstance(result, dict):
            extracted = result
        else:
            extracted = {"raw_output": str(result)}

    except ImportError:
        logger.warning("DocStrange not installed, using fallback extraction")
        extracted = _fallback_extraction(file_bytes, document_type)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        # Fallback extraction for development
        extracted = _fallback_extraction(file_bytes, document_type)

    # ── Cache result ─────────────────────────────────────────────
    await cache_set(cache_key, extracted, ttl_key="ocr")
    logger.info(f"OCR extraction complete for {document_type}")

    return extracted


def _fallback_extraction(file_bytes: bytes, document_type: str) -> Dict[str, Any]:
    """Fallback extraction when OCR service is unavailable."""
    if document_type == "resume":
        return {
            "pipeline_metadata": {
                "resume_content_hash": "",
                "source": "fallback_extraction",
            },
            "name": "Extraction Pending",
            "email": "",
            "skills": [],
            "experience": [],
            "projects": [],
            "education": [],
            "certifications": [],
            "tools": [],
            "technologies": [],
            "candidate_achievements": [],
        }
    else:
        return {
            "pipeline_metadata": {
                "jd_content_hash": "",
                "source": "fallback_extraction",
            },
            "job_information": {
                "job_title": "Extraction Pending",
            },
            "experience_requirements": {},
            "education_requirements": {},
            "skills_and_technologies": {},
            "job_details": {},
        }
