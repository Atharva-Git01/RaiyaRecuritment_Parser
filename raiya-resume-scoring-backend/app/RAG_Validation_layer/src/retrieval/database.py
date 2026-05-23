"""
RAG Evidence Database — pgvector (PostgreSQL 16) based storage.
Replaces Pinecone with pgvector for all vector operations.
"""

import json
import os
from typing import List, Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import create_engine, text

from src.config import settings
from src.logging_config import logger


def _chunk_rule_based_evidence(evidence: dict) -> list[dict]:
    """Split rule-based evidence into one chunk per section + overall summary."""
    header = (
        f"Job: {evidence.get('job_title', 'N/A')} "
        f"(ID: {evidence.get('job_id', 'N/A')})\n"
        f"Evidence ID: {evidence.get('evidence_id', 'N/A')}\n"
        f"Timestamp: {evidence.get('timestamp', 'N/A')}"
    )
    chunks: list[dict] = []
    for sec in evidence.get("section_evidences", []):
        sec_name = sec.get("section_name", "unknown")
        lines = [header, "",
            f"Section: {sec_name} (weight={sec.get('section_weight', 0)}, rule={sec.get('rule_type', 'N/A')})",
            f"  AI Score: {sec.get('ai_score', 'N/A')} | GT: {sec.get('ground_truth_score', 'N/A')} | Delta: {sec.get('score_delta', 'N/A')}",
            f"  Coverage: {sec.get('coverage_pct', 0)}% ({sec.get('matched_count', 0)}/{sec.get('total_criteria', 0)})",
            f"  Verdict: {sec.get('verdict', 'N/A')}"]
        for crit in sec.get("criteria_evaluated", []):
            status = "MATCHED" if crit.get("matched") else "MISSED"
            lines.append(f"    [{status}] {crit.get('criterion', '')} (w={crit.get('criterion_weight', 0)}): {crit.get('evidence', '')}")
        chunks.append({"section_name": sec_name, "text": "\n".join(lines)})
    summary = evidence.get("overall_summary", {})
    if summary:
        lines = [header, "", "Overall Summary:",
            f"  Sections: {summary.get('total_sections', 'N/A')}",
            f"  Over: {summary.get('sections_with_overestimation', 0)} | Under: {summary.get('sections_with_underestimation', 0)} | Accurate: {summary.get('sections_accurate', 0)}",
            f"  AI: {summary.get('ai_final_score', 'N/A')} | Rule: {summary.get('rule_based_final_score', 'N/A')} | Delta: {summary.get('delta', 'N/A')}"]
        chunks.append({"section_name": "overall_summary", "text": "\n".join(lines)})
    return chunks


def _chunk_historical_evidence(evidence: dict) -> list[dict]:
    """Split historical evidence into one chunk per scoring section + summary."""
    header = (
        f"Job: {evidence.get('job_title', 'N/A')} (ID: {evidence.get('job_id', 'N/A')})\n"
        f"Evidence ID: {evidence.get('evidence_id', 'N/A')}\nTimestamp: {evidence.get('timestamp', 'N/A')}")
    raw = evidence.get("raw_sources", {})
    det = raw.get("deterministic_validator_output", {})
    math_report = raw.get("mathematical_validator_report", {})
    section_results = det.get("section_results", {})
    section_accuracy = math_report.get("section_accuracy", {})
    gt_scores = math_report.get("ground_truth_scores", {})
    ai_scores = math_report.get("ai_scores", {})
    chunks: list[dict] = []
    for sec_name, sec_data in section_results.items():
        lines = [header, "", f"Section: {sec_name}", f"  Valid: {sec_data.get('valid', 'N/A')}"]
        acc = section_accuracy.get(sec_name)
        gt = gt_scores.get(sec_name)
        ai = ai_scores.get(sec_name)
        if acc is not None: lines.append(f"  Accuracy: {acc}%")
        if gt is not None and ai is not None: lines.append(f"  AI: {ai} | GT: {gt} | Delta: {round(ai - gt, 2)}")
        sem = sec_data.get("resume_semantic_metrics")
        if sem:
            lines.append(f"  Coverage: {sem.get('weighted_coverage', 'N/A')}% | Overlap: {sem.get('token_overlap', 'N/A')}")
            for m in sem.get("matched_skills", []):
                lines.append(f"    [MATCH] {m.get('jd_item', '')} -> {m.get('resume_match', '')} (sim={m.get('similarity', 'N/A')})")
        for err in sec_data.get("errors", []): lines.append(f"  [ERROR] {err}")
        chunks.append({"section_name": sec_name, "text": "\n".join(lines)})
    summary = evidence.get("summary", {})
    global_metrics = math_report.get("global_metrics", {})
    lines = [header, "", "Overall Summary:",
        f"  Det Valid: {summary.get('deterministic_valid', 'N/A')}",
        f"  Coverage: {summary.get('overall_coverage', 'N/A')}%",
        f"  Math Accuracy: {summary.get('math_accuracy', 'N/A')}%",
        f"  Verdict: {summary.get('final_verdict', 'N/A')}"]
    if global_metrics:
        lines.append(f"  GT: {global_metrics.get('ground_truth_final_score', 'N/A')} | AI: {global_metrics.get('ai_final_score', 'N/A')}")
    chunks.append({"section_name": "overall_summary", "text": "\n".join(lines)})
    return chunks


def _ensure_pgvector_tables(engine) -> None:
    """Ensure pgvector extension and evidence tables exist."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {settings.PGVECTOR_EVIDENCE_TABLE} (
                id SERIAL PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'rule_based',
                section_name TEXT NOT NULL DEFAULT 'general',
                chunk_text TEXT NOT NULL,
                embedding vector({settings.EMBEDDING_DIMS}),
                chunk_hash TEXT,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.commit()
    logger.info("pgvector evidence tables ensured")


def run_database_update():
    """Load latest evidence, chunk, embed, and upsert into pgvector."""
    _HIST_DIR = settings.HISTORICAL_DIR
    _RULE_DIR = settings.OUTPUT_DIR
    db_url = settings.SYNC_DATABASE_URL
    if not db_url:
        logger.error("SYNC_DATABASE_URL not configured"); return
    engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    _ensure_pgvector_tables(engine)
    all_evidence = []
    for edir, src_type in [(_HIST_DIR, "historical"), (_RULE_DIR, "rule_based")]:
        if not os.path.isdir(str(edir)): continue
        for fname in os.listdir(str(edir)):
            if fname.endswith(".json") and fname != "pageindex.json":
                all_evidence.append((os.path.join(str(edir), fname), src_type))
    if not all_evidence:
        logger.warning("No evidence files found."); return
    all_evidence.sort(key=lambda x: os.path.basename(x[0]), reverse=True)
    latest_file, source_type = all_evidence[0]
    with open(latest_file, "r", encoding="utf-8") as f:
        evidence = json.load(f)
    evidence_id = evidence.get("evidence_id")
    logger.info(f"Processing evidence: {evidence_id} from {latest_file}")
    if source_type == "rule_based" and evidence.get("section_evidences") is not None:
        section_chunks = _chunk_rule_based_evidence(evidence)
    elif source_type == "historical" and evidence.get("raw_sources"):
        section_chunks = _chunk_historical_evidence(evidence)
    else:
        logger.error(f"Unrecognised format: {latest_file}"); return
    if not section_chunks:
        logger.error(f"No sections to chunk: {latest_file}"); return
    chunks = [sc["text"] for sc in section_chunks]
    section_names = [sc["section_name"] for sc in section_chunks]
    logger.info(f"Split into {len(chunks)} chunks: {section_names}")
    embeddings_model = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    embeddings = embeddings_model.embed_documents(chunks)
    base_meta = {"job_id": evidence.get("job_id"), "job_title": evidence.get("job_title"),
                 "timestamp": evidence.get("timestamp"), "source_type": source_type}
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM {settings.PGVECTOR_EVIDENCE_TABLE} WHERE evidence_id = :eid"),
                     {"eid": evidence_id})
        for i, (chunk_text, emb, sec_name) in enumerate(zip(chunks, embeddings, section_names)):
            meta = {**base_meta, "chunk_index": i, "section_name": sec_name}
            conn.execute(text(f"""
                INSERT INTO {settings.PGVECTOR_EVIDENCE_TABLE}
                (evidence_id, source_type, section_name, chunk_text, embedding, metadata)
                VALUES (:eid, :stype, :sname, :txt, :emb, :meta)
            """), {"eid": evidence_id, "stype": source_type, "sname": sec_name,
                   "txt": chunk_text, "emb": str(emb), "meta": json.dumps(meta)})
        conn.commit()
    logger.info(f"Stored {len(chunks)} chunks for {evidence_id} in pgvector")


if __name__ == "__main__":
    run_database_update()
