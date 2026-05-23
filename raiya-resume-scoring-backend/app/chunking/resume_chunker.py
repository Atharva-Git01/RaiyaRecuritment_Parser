"""
RAIYA Resume Chunker — Section-aware chunking using RecursiveJsonSplitter.
"""

from typing import List, Dict, Any
from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks
from app.core.config import settings


SECTION_DIMENSION_MAP = {
    "skills":               "technical_skills",
    "technologies":         "technical_skills",
    "tools":                "tool_fit",
    "experience":           "experience_fit",
    "education":            "education_fit",
    "certifications":       "certification_fit",
    "projects":             "domain_fit",
    "candidate_achievements": "domain_fit",
    "salary_expectation":   "salary",
}


def chunk_resume_json(resume_parsed: dict) -> List[Dict[str, Any]]:
    """
    Section-aware chunking using RecursiveJsonSplitter.
    Each top-level section is split independently to preserve semantic boundaries.
    """
    splitter = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_RESUME_MAX_CHUNK)
    all_chunks = []

    for section_key, dimension in SECTION_DIMENSION_MAP.items():
        section_data = resume_parsed.get(section_key)
        if not section_data:
            continue

        if isinstance(section_data, (list, dict)):
            data_to_split = {section_key: section_data}
        else:
            data_to_split = {section_key: str(section_data)}

        chunks = split_json_to_chunks(
            data=data_to_split,
            splitter=splitter,
            dimension_tag=dimension,
            source="resume"
        )
        all_chunks.extend(chunks)

    # Always add pipeline_metadata as a small identity chunk
    meta = resume_parsed.get("pipeline_metadata", {})
    if meta:
        identity = {
            "name": resume_parsed.get("name", ""),
            "email": resume_parsed.get("email", ""),
            "pipeline_metadata": meta
        }
        all_chunks.extend(split_json_to_chunks(
            data=identity, splitter=splitter,
            dimension_tag="identity", source="resume"
        ))

    return all_chunks
