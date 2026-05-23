"""
RAIYA JD Chunker — Criteria-aware JD chunking.
"""

from typing import List, Dict, Any
from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks
from app.core.config import settings


def chunk_jd_json(jd_normalized: dict, jd_weights: dict) -> List[Dict[str, Any]]:
    """
    Criteria-aware JD chunking.
    Each scoring section (with its criteria) is split as an independent sub-JSON.
    """
    splitter = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_JD_MAX_CHUNK)
    all_chunks = []

    scoring = jd_weights.get("scoring", {})
    for section_name, section_data in scoring.items():
        if not isinstance(section_data, dict):
            continue
        jd_items = _get_jd_items_for_section(section_name, jd_normalized)
        chunk_data = {
            "section": section_name,
            "weight": section_data.get("weight", 0),
            "criteria": section_data.get("criteria", {}),
            "jd_items": jd_items
        }
        chunks = split_json_to_chunks(
            data=chunk_data, splitter=splitter,
            dimension_tag=section_name, source="jd"
        )
        all_chunks.extend(chunks)

    # Add job information as a domain_fit chunk
    job_info = {
        "job_title": jd_normalized.get("job_title", ""),
        "position": jd_normalized.get("position", ""),
        "job_description": str(jd_normalized.get("job_description", ""))[:500],
        "responsibilities": jd_normalized.get("responsibilities", [])[:5]
    }
    all_chunks.extend(split_json_to_chunks(
        data=job_info, splitter=splitter,
        dimension_tag="domain_fit", source="jd"
    ))
    return all_chunks


def _get_jd_items_for_section(section: str, jd: dict) -> List[str]:
    mapping = {
        "technologies": jd.get("technologies", []),
        "skills": jd.get("skills", []),
        "tools": jd.get("tools", []),
        "certifications": jd.get("certifications", []),
        "responsibilities": jd.get("responsibilities", [])[:8],
    }
    return mapping.get(section, [])
