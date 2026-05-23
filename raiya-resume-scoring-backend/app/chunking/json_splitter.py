"""
RAIYA JSON Splitter — RecursiveJsonSplitter base wrapper.
"""

import json
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveJsonSplitter
from app.core.hashing import hash_content
from app.core.config import settings


# Global splitter instances for different max chunk sizes
RESUME_SPLITTER = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_RESUME_MAX_CHUNK)
JD_SPLITTER = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_JD_MAX_CHUNK)
EVIDENCE_SPLITTER = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_EVD_MAX_CHUNK)


def split_json_to_chunks(
    data: dict,
    splitter: RecursiveJsonSplitter,
    dimension_tag: str,
    source: str
) -> List[Dict[str, Any]]:
    """
    Split a JSON dict into chunks using RecursiveJsonSplitter.
    Each chunk is tagged with dimension and source for pgvector metadata.
    """
    json_chunks = splitter.split_json(json_data=data)

    chunks = []
    for i, chunk_dict in enumerate(json_chunks):
        chunk_text = json.dumps(chunk_dict, separators=(",", ":"), sort_keys=True)
        chunks.append({
            "text": chunk_text,
            "dimension": dimension_tag,
            "source": source,
            "chunk_index": i,
            "chunk_hash": hash_content(chunk_text)
        })
    return chunks
