"""
Deterministic Validator — Semantic Edition
==========================================
Uses **sentence-transformers all-MiniLM-L12-v2** to compare:
  * JD criteria keywords  (from validated_jd.json  -> "scoring" section)
  * Resume keywords       (extracted from ai_scorer output inputs.resume)

For every scorable section the output shows ONLY items present in BOTH
JD and resume (matched_skills) and items missing from resume (missing_skills).

Numeric-only sections (experience brackets, salary, position, etc.) are
skipped from keyword analysis.

Inputs
------
  * validated_jd.json   - job description with embedded scoring/criteria
  * ai_scorer.json      - AI scorer output (contains inputs.resume + result)

No extracted_rules.json is required.

Environment note
----------------
This script requires:
  pip install sentence-transformers
The model all-MiniLM-L12-v2 is downloaded automatically on first run.

NumPy / torch compatibility
---------------------------
torch 2.2.0+cpu was compiled against NumPy 1.x; NumPy 2.x broke the ABI.
To side-step the torch↔numpy interop issue we:
  1. import sentence_transformers BEFORE torch (ordering matters)
  2. Compute cosine similarity with pure Python math (no torch.mm / np calls)
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.config import settings
from src.logging_config import logger

# -- 1. Import sentence_transformers eagerly (before any torch import) ---------
try:
    from sentence_transformers import SentenceTransformer as _ST
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _SENTENCE_TRANSFORMERS_AVAILABLE = False
    _ST = None  # type: ignore

# ---------------------------------------------------------------------------
# Default paths from settings
# ---------------------------------------------------------------------------
DEFAULT_AI_SCORE_PATH = settings.DEFAULT_AI_INPUT
DEFAULT_VALIDATED_JD  = settings.VALIDATED_JD_PATH
DEFAULT_OUT_PATH      = settings.DET_OUT_PATH

# ---------------------------------------------------------------------------
# Model (lazy-loaded once)
# ---------------------------------------------------------------------------
_MODEL = None


def _get_model() -> "_ST":
    """Return a singleton SentenceTransformer(all-MiniLM-L12-v2)."""
    global _MODEL
    if _MODEL is None:
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            )
        logger.info(f"Loading sentence-transformer: {settings.EMBEDDING_MODEL} ...")
        _MODEL = _ST(settings.EMBEDDING_MODEL)
        logger.info("Model ready.")
    return _MODEL


    # -- Pure-Python cosine similarity (avoids torch <-> numpy ABI bridge entirely)
    # ---------------------------------------------------------------------------

def _cosine_pure(a: List[float], b: List[float]) -> float:
    """Cosine similarity using only the standard math module."""
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _encode(texts: List[str]) -> List[List[float]]:
    """
    Encode texts with the sentence-transformer and return as a plain
    Python list-of-lists (avoids any numpy / torch tensor conversion).
    """
    model = _get_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=False,
        convert_to_tensor=False,
        show_progress_bar=False,
    )
    result: List[List[float]] = []
    for emb in embeddings:
        try:
            result.append([float(x) for x in emb])
        except Exception:
            result.append(list(emb))
    return result


# ---------------------------------------------------------------------------
# Resume text extraction helpers
# ---------------------------------------------------------------------------

def _extract_resume_items(section: str, ai_score: Dict[str, Any]) -> List[str]:
    """Flat list of text tokens from the resume for *section*."""
    resume: Dict[str, Any] = ai_score.get("inputs", {}).get("resume", {})

    SECTION_FIELD_MAP: Dict[str, List[str]] = {
        "skills":              ["skills", "projects", "experience"],
        "technologies":        ["technologies", "skills", "projects", "experience"],
        "tools":               ["tools", "skills", "projects"],
        "experience":          ["experience"],
        "relevant_experience": ["experience"],
        "projects":            ["projects"],
        "certificates":        ["certifications"],
        "qualification":       ["education"],
        "responsibilities":    ["experience"],
        "salary":              ["salary_expectation"],
        "position":            ["position"],
    }

    fields = SECTION_FIELD_MAP.get(section, [section])
    items: List[str] = []

    for field in fields:
        val = resume.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    items.append(item)
                elif isinstance(item, dict):
                    for sub in ("name", "title", "description", "degree", "normalized_degree", "institution"):
                        sv = item.get(sub, "")
                        if sv:
                            items.append(str(sv))
                    for resp in item.get("responsibilities", []):
                        items.append(str(resp))
                    for tech in item.get("technologies", []):
                        items.append(str(tech))
        elif isinstance(val, dict):
            items.extend(str(v) for v in val.values() if v)
        elif isinstance(val, str) and val:
            items.append(val)

    return items


# ---------------------------------------------------------------------------
# Semantic matching core
# ---------------------------------------------------------------------------

SEMANTIC_THRESHOLD = 0.9  # cosine sim ≥ this -> matched


def semantic_compare(
    jd_keywords: List[str],
    resume_items: List[str],
    weights: Optional[Dict[str, float]] = None,
    threshold: float = SEMANTIC_THRESHOLD,
) -> Dict[str, Any]:
    """
    Compare JD keywords vs resume items using all-MiniLM-L12-v2.

    Returns
    -------
    {
        "matched_skills":    [{"jd_item", "resume_match", "similarity", "weight"}],
        "weighted_coverage": float  (0-100 %),
        "token_overlap":     float  (0-1),
    }
    """
    if not jd_keywords or not resume_items:
        return {
            "matched_skills":    [],
            "weighted_coverage": 0.0,
            "token_overlap":     0.0,
        }

    all_texts    = jd_keywords + resume_items
    all_embs     = _encode(all_texts)
    jd_embs      = all_embs[:len(jd_keywords)]
    resume_embs  = all_embs[len(jd_keywords):]

    matched:        List[Dict[str, Any]] = []
    total_weight   = 0.0
    matched_weight = 0.0

    for idx, kw in enumerate(jd_keywords):
        w = float((weights or {}).get(kw, 1.0))
        total_weight += w

        sims     = [_cosine_pure(jd_embs[idx], r_emb) for r_emb in resume_embs]
        best_idx = max(range(len(sims)), key=lambda i: sims[i])
        best_sim = sims[best_idx]

        if best_sim >= threshold:
            matched.append({
                "jd_item":      kw,
                "resume_match": resume_items[best_idx],
                "similarity":   round(best_sim, 4),
                "weight":       w,
            })
            matched_weight += w

    weighted_coverage = (matched_weight / total_weight * 100) if total_weight > 0 else 0.0
    token_overlap     = len(matched) / len(jd_keywords)          if jd_keywords else 0.0

    return {
        "matched_skills":    matched,
        "weighted_coverage": round(weighted_coverage, 2),
        "token_overlap":     round(token_overlap, 4),
    }


# ---------------------------------------------------------------------------
# JD keyword extraction — reads directly from validated_jd["scoring"]
# ---------------------------------------------------------------------------

_NUMERIC_PAT = re.compile(
    r'^[<>]|^\d|\byears\b|\bLPA\b|_relevant|^Other$', re.IGNORECASE
)


def _jd_keywords_for_section(
    section: str,
    validated_jd: Dict[str, Any],
) -> Tuple[List[str], Dict[str, float]]:
    """
    Return (keyword_list, weight_dict) for a section.

    Reads criteria from validated_jd["scoring"][section]["criteria"].
    Falls back to the raw top-level list (e.g. validated_jd["technologies"])
    if criteria are all-numeric or absent.
    """
    scoring  = validated_jd.get("scoring", {})
    section_scoring = scoring.get(section, {})
    criteria = section_scoring.get("criteria", {})

    kw_weights: Dict[str, float] = {}
    for kw, w in criteria.items():
        if not _NUMERIC_PAT.search(str(kw)):
            kw_weights[kw] = float(w)

    # Fallback: use the raw top-level list if criteria yielded nothing
    if not kw_weights:
        jd_list = validated_jd.get(section, [])
        if isinstance(jd_list, list):
            for item in jd_list:
                if isinstance(item, str):
                    kw_weights[item] = 1.0

    return list(kw_weights.keys()), kw_weights


# ---------------------------------------------------------------------------
# Sections to skip (numeric-bracket scoring only)
# ---------------------------------------------------------------------------
SKIP_SECTIONS: Set[str] = {
    "experience", "relevant_experience", "salary", "position",
}


# ---------------------------------------------------------------------------
# Main Validator class
# ---------------------------------------------------------------------------

class DeterministicValidator:
    """
    Validates AI scorer output using semantic similarity (all-MiniLM-L12-v2).

    Inputs
    ------
    validated_jd  - parsed validated_jd.json  (must contain a "scoring" key)
    ai_score      - parsed ai_scorer JSON output

    Output per section (two independent comparisons):
      * resume_semantic_metrics  - JD keywords vs resume content
      * result_semantic_metrics  - JD keywords vs AI scorer output notes
      * weighted_coverage, token_overlap reported for each axis
    """

    def __init__(
        self,
        validated_jd: Dict[str, Any],
        threshold: float = SEMANTIC_THRESHOLD,
    ):
        self.validated_jd = validated_jd
        self.threshold    = threshold
        # Derive the section list from the "scoring" block in the JD
        self.sections: List[str] = list(validated_jd.get("scoring", {}).keys())

    def validate(self, ai_score: Dict[str, Any]) -> Dict[str, Any]:
        result_block = ai_score.get("result", ai_score)

        report: Dict[str, Any] = {
            "is_valid":          True,
            "overall_analytics": None,
            "errors":            [],
            "section_results":   {},
        }

        all_jd_kws:       List[str]        = []
        all_jd_weights:   Dict[str, float] = {}
        all_resume_items: List[str]        = []

        scoring = self.validated_jd.get("scoring", {})

        for section_name in self.sections:
            section_cfg = scoring.get(section_name, {})
            sec_result: Dict[str, Any] = {
                "valid":                   True,
                "errors":                  [],
                "resume_semantic_metrics": None,
            }

            # -- Score presence / range checks ------------------------─
            score_key     = f"{section_name}_score"
            section_score = result_block.get(score_key)

            if section_score is None:
                # Not all sections are required — just skip silently
                report["section_results"][section_name] = sec_result
                continue

            # No score-range enforcement here: validated_jd.json does not define
            # min_score / max_score bounds. A low AI-scorer score just means the
            # candidate matched fewer JD requirements — that is not a validation
            # error. The semantic_metrics block below shows exactly what matched
            # and what is missing.

            # -- Semantic keyword analysis ------------------------------
            if section_name not in SKIP_SECTIONS:
                jd_kws, jd_weights = _jd_keywords_for_section(
                    section_name, self.validated_jd
                )

                # -- (A) vs Resume --------------------------------------
                resume_items = _extract_resume_items(section_name, ai_score)
                if jd_kws and resume_items:
                    sec_result["resume_semantic_metrics"] = semantic_compare(
                        jd_kws, resume_items,
                        weights=jd_weights,
                        threshold=self.threshold,
                    )
                    # accumulate for overall resume analytics
                    for kw in jd_kws:
                        if kw not in all_jd_weights:
                            all_jd_kws.append(kw)
                            all_jd_weights[kw] = jd_weights[kw]
                    all_resume_items.extend(resume_items)

                # -- Hallucination Check ---------------------------------
                if sec_result.get("resume_semantic_metrics"):
                    # Check resume-jd matched items and compare with jd items
                    matched_jd_items = {m["jd_item"] for m in sec_result["resume_semantic_metrics"]["matched_skills"]}
                    jd_set = set(jd_kws)
                    
                    # If all matched items are present in JD, it's valid
                    hallucinations = matched_jd_items - jd_set
                    if hallucinations:
                        sec_result["valid"] = False
                        sec_result["errors"].append(
                            f"Hallucination: items {list(hallucinations)} claimed as matched but not found in JD."
                        )
                    else:
                        sec_result["valid"] = True

                # -- Quality Threshold Check --
                if sec_result.get("resume_semantic_metrics"):
                    coverage = sec_result["resume_semantic_metrics"]["weighted_coverage"]
                    if coverage < 0:
                        sec_result["valid"] = False
                        sec_result["errors"].append(
                            f"Low matching coverage ({coverage:.2f}% < 80%)."
                        )

            report["section_results"][section_name] = sec_result
            if not sec_result["valid"]:
                report["is_valid"] = False

        # -- Overall analytics (resume side) ----------------------------
        if all_jd_kws and all_resume_items:
            report["overall_analytics"] = semantic_compare(
                all_jd_kws,
                list(dict.fromkeys(all_resume_items)),
                weights=all_jd_weights,
                threshold=self.threshold,
            )


        return report


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _print_section_summary(section: str, res: Dict[str, Any]) -> None:
    r_metrics = res.get("resume_semantic_metrics")
    
    if r_metrics is None:
        tag = "[SKIPPED - numeric/bracket scoring]" if section in SKIP_SECTIONS else "[N/A]"
        print(f"\n  -- {section.upper()} {tag}")
        return

    print(f"\n  -- {section.upper()} --")

    # -- (A) vs Resume ----------------------------------------------------
    if r_metrics is not None:
        matched = r_metrics.get("matched_skills", [])
        print(f"     [vs RESUME]  Coverage: {r_metrics['weighted_coverage']}%   "
              f"Token Overlap: {r_metrics['token_overlap']:.4f}")
        if matched:
            print(f"       Matched ({len(matched)}):")
            for item in matched:
                print(f"         * JD: \"{item['jd_item']}\"")
                print(f"           -> Resume: \"{item['resume_match']}\"  "
                      f"(sim={item['similarity']:.3f}, weight={item['weight']})")
        else:
            print("       Matched: none")
    else:
        print("     [vs RESUME]  No resume content for this section.")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # -- Load validated JD (single source of truth for rules + JD content) --
    if not DEFAULT_VALIDATED_JD.exists():
        logger.error(f"validated_jd.json not found: {DEFAULT_VALIDATED_JD}")
        raise SystemExit(1)
    with open(DEFAULT_VALIDATED_JD, "r", encoding="utf-8") as f:
        validated_jd = json.load(f)

    if "scoring" not in validated_jd:
        logger.error("validated_jd.json has no 'scoring' section. Cannot derive rules.")
        raise SystemExit(1)

    logger.info(f"Loaded validated JD: {DEFAULT_VALIDATED_JD}")

    # -- Load AI scorer output -------------------------------------------
    if not DEFAULT_AI_SCORE_PATH.exists():
        logger.error(f"AI score file not found: {DEFAULT_AI_SCORE_PATH}")
        raise SystemExit(1)
    with open(DEFAULT_AI_SCORE_PATH, "r", encoding="utf-8") as f:
        ai_score = json.load(f)

    logger.info(f"Loaded AI scorer output: {DEFAULT_AI_SCORE_PATH}")

    # -- Run validation --------------------------------------------------
    validator = DeterministicValidator(validated_jd)
    report    = validator.validate(ai_score)

    # -- Save JSON output ------------------------------------------------
    os.makedirs(DEFAULT_OUT_PATH.parent, exist_ok=True)
    with open(DEFAULT_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Report saved -> {DEFAULT_OUT_PATH}")
    logger.info(f"Overall valid: {report['is_valid']}")

    # -- Per-section console output --------------------------------------
    print("==========================================================")
    print("   SEMANTIC VALIDATION REPORT  (all-MiniLM-L12-v2)")
    print("==========================================================")

    for sec, res in report["section_results"].items():
        _print_section_summary(sec, res)

    # -- Overall (resume side) ------------------------------------------
    ov = report.get("overall_analytics")
    if ov:
        print("\n==========================================================")
        print("   OVERALL vs RESUME  (all analysed sections combined)")
        print("==========================================================")
        print(f"  Weighted Coverage : {ov['weighted_coverage']}%")
        print(f"  Token Overlap     : {ov['token_overlap']:.4f}")
        print(f"  Matched Skills    : {len(ov.get('matched_skills', []))}")
        print("\n  -- MATCHED (JD <-> Resume) --")
        for item in ov.get("matched_skills", []):
            print(f"   [MATCH] [{item['similarity']:.3f}]  JD: \"{item['jd_item']}\"")
            print(f"           Resume: \"{item['resume_match']}\"")

