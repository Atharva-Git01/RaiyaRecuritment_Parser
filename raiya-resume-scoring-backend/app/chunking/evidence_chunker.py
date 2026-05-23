"""
RAIYA Evidence Chunker — Chunk EVD_{ts}_{uuid}.json for pgvector upsert.
"""

from typing import List, Dict, Any
from langchain_text_splitters import RecursiveJsonSplitter
from app.chunking.json_splitter import split_json_to_chunks
from app.core.config import settings


def chunk_evd_json(evd_doc: dict) -> List[Dict[str, Any]]:
    """
    Chunk EVD documents for pgvector upsert.
    Strategy: one chunk per section_evidence entry + 1 summary chunk.
    """
    splitter = RecursiveJsonSplitter(max_chunk_size=settings.JSON_SPLITTER_EVD_MAX_CHUNK)
    evidence_id = evd_doc.get("evidence_id", "EVD_unknown")
    all_chunks = []

    # Per-section chunks from rule_based evidence
    raw_sources = evd_doc.get("raw_sources", {})
    rbe = raw_sources.get("rule_based_evidence", {})
    for section_ev in rbe.get("section_evidences", []):
        section_name = section_ev.get("section_name", "unknown")
        chunk_data = {
            "evidence_id": evidence_id,
            "section_name": section_name,
            "verdict": section_ev.get("verdict"),
            "ai_score": section_ev.get("ai_score"),
            "ground_truth": section_ev.get("ground_truth_score"),
            "score_delta": section_ev.get("score_delta"),
            "coverage_pct": section_ev.get("coverage_pct"),
            "applied_rules": [r["rule_id"] for r in section_ev.get("applied_rules", []) if r.get("fired")],
            "criteria_evaluated": section_ev.get("criteria_evaluated", [])[:5]
        }
        chunks = split_json_to_chunks(
            data=chunk_data, splitter=splitter,
            dimension_tag=section_name, source="rag_evidence"
        )
        for c in chunks:
            c["evidence_id"] = evidence_id
            c["source_type"] = "rule_based"
            c["section_name"] = section_name
        all_chunks.extend(chunks)

    # Summary chunk
    summary_data = {
        "evidence_id": evidence_id,
        "job_title": evd_doc.get("job_title"),
        "summary": evd_doc.get("summary", {}),
        "keywords": evd_doc.get("keywords", []),
        "text_blob": str(evd_doc.get("text_blob", ""))[:400]
    }
    summary_chunks = split_json_to_chunks(
        data=summary_data, splitter=splitter,
        dimension_tag="summary", source="rag_evidence"
    )
    for c in summary_chunks:
        c["evidence_id"] = evidence_id
        c["source_type"] = "historical"
        c["section_name"] = "summary"
    all_chunks.extend(summary_chunks)

    return all_chunks
