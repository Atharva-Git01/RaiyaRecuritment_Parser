"""
RAIYA Search Tool — Hybrid search per section (Dense BGE + BM25 + Exact + RRF).
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional

from app.agents.tools.embed_tool import embed_single
from app.db.redis_client import cache_get, cache_set, CacheKeys
from app.db.pgvector_client import search_resume_embeddings
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("SearchTool")

RRF_K = settings.DETERMINISTIC_RRF_K
DENSE_WEIGHT = settings.DENSE_WEIGHT_IN_DETERMINISTIC
BM25_WEIGHT = settings.BM25_WEIGHT_IN_DETERMINISTIC


async def hybrid_search_per_section(
    resume_file_id: str,
    jd_weights: Dict[str, Any],
    resume_parsed: Dict[str, Any],
    session: Any,
    resume_hash: str = "",
    jd_hash: str = "",
    weights_hash: str = "",
) -> Dict[str, Dict[str, float]]:
    """
    Perform hybrid search for each JD scoring section.
    Combines Dense (BGE cosine via pgvector) + BM25 (in-memory) + exact match.
    Results fused with RRF.
    
    Returns:
        Dict[section_name → {dense, bm25, exact, hybrid, weight}]
    """
    scoring = jd_weights.get("scoring", {})
    section_results = {}

    for section_name, section_data in scoring.items():
        # ── Check cache ──────────────────────────────────────
        cache_key = CacheKeys.search(resume_hash, jd_hash, weights_hash, section_name)
        cached = await cache_get(cache_key)
        if cached:
            section_results[section_name] = json.loads(cached)
            continue

        criteria = section_data.get("criteria", {})
        jd_items = list(criteria.keys()) if criteria else []
        weight = section_data.get("weight", 0)

        if not jd_items or weight == 0:
            section_results[section_name] = {
                "dense": 0.0, "bm25": 0.0, "exact": 0.0,
                "hybrid_score": 0.0, "weight": weight,
            }
            continue

        # Get resume items for this section
        resume_items = _get_resume_items_for_section(section_name, resume_parsed)

        if not resume_items:
            section_results[section_name] = {
                "dense": 0.0, "bm25": 0.0, "exact": 0.0,
                "hybrid_score": 0.0, "weight": weight,
            }
            continue

        # ── Dense search via pgvector ────────────────────────
        jd_query = " ".join(jd_items[:10])
        query_emb = embed_single(jd_query)
        dimension = _section_to_dimension(section_name)

        dense_results = await search_resume_embeddings(
            session, query_emb, resume_file_id=resume_file_id,
            dimension=dimension, top_k=5,
        )
        dense_score = max([r["similarity"] for r in dense_results], default=0.0)

        # ── BM25 in-memory ───────────────────────────────────
        bm25_score = _compute_bm25_score(jd_items, resume_items)

        # ── Exact match ──────────────────────────────────────
        exact_score = _compute_exact_match(jd_items, resume_items)

        # ── RRF fusion ───────────────────────────────────────
        hybrid = (
            DENSE_WEIGHT * dense_score +
            BM25_WEIGHT * bm25_score +
            0.0 * exact_score  # exact match is a bonus check
        )
        # Boost if exact matches exist
        if exact_score > 0:
            hybrid = min(1.0, hybrid + exact_score * 0.1)

        result = {
            "dense": round(dense_score, 4),
            "bm25": round(bm25_score, 4),
            "exact": round(exact_score, 4),
            "hybrid_score": round(hybrid, 4),
            "weight": weight,
        }
        section_results[section_name] = result

        # Cache
        await cache_set(cache_key, result, ttl_key="search")

    logger.info(f"Hybrid search complete for {len(section_results)} sections")
    return section_results


def _get_resume_items_for_section(section: str, resume: Dict[str, Any]) -> List[str]:
    """Extract resume items relevant to a JD section."""
    FIELD_MAP = {
        "skills": ["skills"],
        "technologies": ["technologies", "skills"],
        "tools": ["tools"],
        "experience": ["experience"],
        "relevant_experience": ["experience"],
        "qualification": ["education"],
        "certifications": ["certifications"],
        "responsibilities": ["experience", "projects"],
        "position": ["experience"],
        "salary": ["salary_expectation"],
    }
    fields = FIELD_MAP.get(section, [section])
    items = []
    for field in fields:
        val = resume.get(field)
        if isinstance(val, list):
            for entry in val:
                if isinstance(entry, str):
                    items.append(entry)
                elif isinstance(entry, dict):
                    for k in ("title", "name", "description", "degree", "institution", "company"):
                        v = entry.get(k, "")
                        if v:
                            items.append(str(v))
                    resps = entry.get("responsibilities", [])
                    items.extend([str(r) for r in resps if r])
        elif isinstance(val, str) and val:
            items.append(val)
        elif isinstance(val, dict):
            items.extend([str(v) for v in val.values() if v])
    return [i.strip() for i in items if i.strip()]


def _section_to_dimension(section: str) -> str:
    """Map section name to pgvector dimension tag."""
    MAP = {
        "skills": "technical_skills",
        "technologies": "technical_skills",
        "tools": "tool_fit",
        "experience": "experience_fit",
        "relevant_experience": "experience_fit",
        "qualification": "education_fit",
        "certifications": "certification_fit",
        "responsibilities": "domain_fit",
        "position": "experience_fit",
        "salary": "salary",
    }
    return MAP.get(section, "general")


def _compute_bm25_score(jd_items: List[str], resume_items: List[str]) -> float:
    """Simple BM25-like scoring."""
    if not jd_items or not resume_items:
        return 0.0
    try:
        from rank_bm25 import BM25Okapi
        tokenized = [r.lower().split() for r in resume_items]
        bm25 = BM25Okapi(tokenized)
        query = " ".join(jd_items).lower().split()
        scores = bm25.get_scores(query)
        max_score = float(max(scores)) if len(scores) > 0 else 0.0
        # Normalize to [0, 1]
        return min(1.0, max_score / (max_score + 1.0)) if max_score > 0 else 0.0
    except Exception:
        return 0.0


def _compute_exact_match(jd_items: List[str], resume_items: List[str]) -> float:
    """Compute exact substring match ratio."""
    if not jd_items:
        return 0.0
    resume_text = " ".join(resume_items).lower()
    matched = sum(1 for item in jd_items if item.lower() in resume_text)
    return matched / len(jd_items)
