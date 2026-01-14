# app/ai_scorer.py
import json
import math
import os

# === JD SCORING NORMALIZATION HELPERS (scale small-value criteria to 0–100) ===
from copy import deepcopy
from typing import Any, Dict, Tuple

import requests
from dotenv import load_dotenv


def _scale_criteria_dict(criteria: Dict[str, float]) -> Dict[str, int]:
    """Scale any JD criteria map to 0–100 range."""
    if not criteria or not isinstance(criteria, dict):
        return {}

    numeric_values = []
    for k, v in criteria.items():
        try:
            numeric_values.append(float(v))
        except:
            numeric_values.append(0.0)

    max_val = max(numeric_values) if numeric_values else 0.0
    if max_val <= 0:
        return {k: 0 for k in criteria}

    # If already 0–100 scale, do nothing except clean ints.
    if max_val >= 100:
        out = {}
        for k, v in criteria.items():
            try:
                out[k] = max(0, min(100, int(round(float(v)))))
            except:
                out[k] = 0
        return out

    # Scale proportionally
    scale = 100.0 / max_val
    out = {}
    for k, v in criteria.items():
        try:
            val = float(v)
        except:
            val = 0.0
        scaled = int(round(val * scale))
        out[k] = max(0, min(100, scaled))

    return out


# === Load environment variables ===
load_dotenv()

AZURE_AI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
DEPLOYMENT_ID = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

# === SYSTEM PROMPT (strict, exhaustive, zero-hallucination) ===
SYSTEM_PROMPT = """
You are a strict, zero-hallucination AI resume scoring assistant.
You MUST follow these rules EXACTLY.

SOURCE RULES:
- You may only use information explicitly present in the job description (JD) and the parsed candidate resume JSON provided by the user.
- Do NOT infer or assume anything not present textually in the JD or resume.
- Do NOT expand abbreviations, add synonyms, or invent experiences/skills/projects/certificates/dates.

OUTPUT RULES:
- Return ONLY valid JSON (no prose, no commentary).
- Output MUST match the EXACT schema described below.
- All numeric scores MUST be integers in the range [0, 100].
- If a required input field is missing from the JD or resume, score that category 0.
- notes MUST be <= 240 chars, concise, factual, no lists.

MANDATORY OUTPUT SCHEMA (11 scoring fields + notes):
{
  "final_score": <int>,
  "skills_score": <int>,
  "experience_score": <int>,
  "relevant_experience_score": <int>,
  "projects_score": <int>,
  "certificates_score": <int>,
  "tools_score": <int>,
  "technologies_score": <int>,
  "qualification_score": <int>,
  "responsibilities_score": <int>,
  "salary_score": <int>,
  "notes": "<brief explanation>"
}

SCORING GUIDELINES (you MUST follow these formulas):
- Each sub-score should be 0-100 integer determined only by textual matches between JD and resume.

- Use this weighted formula to compute final_score (round to nearest integer):
    final_score = round(
        0.30 * skills_score +
        0.25 * experience_score +
        0.10 * relevant_experience_score +
        0.10 * projects_score +
        0.05 * certificates_score +
        0.05 * tools_score +
        0.05 * technologies_score +
        0.05 * qualification_score +
        0.03 * responsibilities_score +
        0.02 * salary_score
    )

- Salary scoring:
    - If JD contains salary expectation and candidate has expected/current, score based on match (100 = perfect, 0 = outside).
    - If missing in either -> 0.

- Skills scoring:
    - Count explicit skill tokens in JD and count how many appear in resume.skills.
    - skills_score = round(100 * matches / total_JD_skills).

- Experience scoring:
    - Compare JD required years/level with resume experience.
    - If no numeric requirement, base on keyword overlap.

- Other categories:
    - Score based on percent coverage of JD requirements found in resume.

IMPORTANT:
- Do NOT invent counts. Use exact tokens/phrases.
- Keep 'notes' short and factual e.g. "Skills: 4/8 matched; Exp: 3.5 yrs vs 5 req."
- Return ONLY the JSON object.
"""

# === helper: expected schema keys & weights ===
EXPECTED_KEYS = [
    "final_score",
    "skills_score",
    "experience_score",
    "relevant_experience_score",
    "projects_score",
    "certificates_score",
    "tools_score",
    "technologies_score",
    "qualification_score",
    "responsibilities_score",
    "salary_score",
    "notes",
]

# === Configurable Weights ===
def get_weights():
    """
    Returns the scoring weights. 
    In the future, this can load from a config file or DB.
    """
    return {
        "skills_score": 0.30,
        "experience_score": 0.25,
        "relevant_experience_score": 0.10,
        "projects_score": 0.10,
        "certificates_score": 0.05,
        "tools_score": 0.05,
        "technologies_score": 0.05,
        "qualification_score": 0.05,
        "responsibilities_score": 0.03,
        "salary_score": 0.02,
    }

WEIGHTS = get_weights()


def _clamp_and_int(v: Any) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = 0
    return max(0, min(100, iv))


def _compute_weighted_final(score_map: Dict[str, int]) -> int:
    total = 0.0
    for k, w in WEIGHTS.items():
        total += score_map.get(k, 0) * w
    return int(round(total))


def _extract_json_from_text(text: str) -> Tuple[bool, Any]:
    """Try to find the first JSON object in text and parse it."""
    if not isinstance(text, str):
        return False, None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return False, None
    try:
        candidate = text[start : end + 1]
        return True, json.loads(candidate)
    except Exception:
        return False, None


def validate_ai_score_output(raw_obj: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Ensure output has required keys, integer 0-100 scores, and a notes string.
    If final_score is missing or inconsistent, recompute using weights.
    """
    out = {}
    if not isinstance(raw_obj, dict):
        return False, {"error": "AI output is not a JSON object."}

    # Coerce / clamp numeric fields
    for key in EXPECTED_KEYS:
        if key == "notes":
            val = raw_obj.get("notes", "")
            # Clean notes: remove placeholders
            if str(val).lower() in ["n/a", "none", "null", "not specified"]:
                val = ""
            out["notes"] = str(val)[:240]
        else:
            val = raw_obj.get(key)
            out[key] = _clamp_and_int(val)

    # Recompute final_score and override if mismatch (we allow AI to propose but ensure consistency)
    computed_final = _compute_weighted_final(out)
    # if AI provided final_score and differs by more than 2 points, replace and add note
    if abs(out.get("final_score", 0) - computed_final) > 2:
        out["final_score"] = computed_final
        # prepend small note about recompute
        note = out.get("notes", "")
        prefix = "FINAL_RECOMPUTED: "
        out["notes"] = (prefix + note)[:240]

    return True, out


def _build_fallback_payload(
    local_scores: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(local_scores, dict):
        return None

    fallback = {}
    for key in EXPECTED_KEYS:
        if key == "notes":
            fallback["notes"] = str(local_scores.get("notes", "")).strip()
        else:
            fallback[key] = _clamp_and_int(local_scores.get(key, 0))
    if "final_score" not in fallback:
        fallback["final_score"] = _compute_weighted_final(fallback)
    fallback["notes"] = (fallback.get("notes") or "") + " [AI fallback]"
    fallback["notes"] = fallback["notes"][:240]
    return fallback


def ai_score_resume(
    parsed_resume: dict,
    job_description: dict,
    timeout: int = 30,
    fallback_local_scores: Dict[str, Any] | None = None,
) -> dict:
    """
    Use Azure/OpenAI-compatible REST endpoint to request a full JD scoring from the LLM.
    This function enforces the system prompt (zero-hallucination + exact schema).
    Returns dict: {"ai_ok": bool, "ai_score": {...}} or {"ai_ok": False, "error": "..."}
    """
    if not AZURE_AI_ENDPOINT or not DEPLOYMENT_ID or not API_KEY:
        fb = _build_fallback_payload(fallback_local_scores)
        payload = {
            "ai_ok": False,
            "error": "Missing AZURE_OPENAI credentials; using fallback matcher score.",
        }
        if fb:
            payload["ai_score"] = fb
        return payload

    api_url = f"{AZURE_AI_ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version=2024-05-01-preview"

    # --- NEW: Phase 4 Part 3 Integration ---
    from app.jd_validator import validate_jd

    # Validate + normalize JD completely
    validated_jd = validate_jd(job_description)

    user_prompt = (
        "Below are the job description and the parsed resume JSON. Score strictly per the SYSTEM_PROMPT.\n\n"
        f"JOB_DESCRIPTION:\n{json.dumps(validated_jd, ensure_ascii=False, indent=2)}\n\n"
        f"PARSED_RESUME:\n{json.dumps(parsed_resume, ensure_ascii=False, indent=2)}\n\n"
        "Return ONLY the required JSON object with the mandatory schema."
    )

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 900,
    }

    try:
        resp = requests.post(api_url, headers=HEADERS, json=payload, timeout=timeout)
        data = resp.json()
    except Exception as e:
        return {"ai_ok": False, "error": f"AI request failed: {e}"}

    # Detect API-level error
    if isinstance(data, dict) and "error" in data:
        return {"ai_ok": False, "error": data["error"].get("message", data["error"])}

    # Extract raw assistant content robustly
    content = ""
    try:
        # Typical structure: choices -> [{message: {content: "..."} }]
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        content = ""

    if not content:
        # fallback: sometimes model outputs in 'choices'[0]['text']
        try:
            content = data.get("choices", [{}])[0].get("text", "") or ""
        except Exception:
            content = ""

    if not content:
        # save raw response and return error
        os.makedirs("storage/errors", exist_ok=True)
        with open(
            "storage/errors/ai_raw_empty_response.json", "w", encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"ai_ok": False, "error": "Empty model response content."}

    # Try to parse JSON directly, otherwise extract object from text
    parsed = None
    try:
        parsed = json.loads(content)
    except Exception:
        ok, parsed = _extract_json_from_text(content)
        if not ok:
            # Save raw output for debugging
            os.makedirs("storage/errors", exist_ok=True)
            with open("storage/errors/ai_raw_output.txt", "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "ai_ok": False,
                "error": "Could not parse JSON from AI output; raw saved to storage/errors/ai_raw_output.txt.",
            }

    # Validate and normalize the AI output
    valid, normalized = validate_ai_score_output(parsed)
    if not valid:
        fb = _build_fallback_payload(fallback_local_scores)
        result = {
            "ai_ok": False,
            "error": "AI output validation failed.",
            "raw_ai": parsed,
        }
        if fb:
            result["ai_score"] = fb
        return result

    if (
        normalized.get("final_score", 0) == 0
        and fallback_local_scores
        and (fallback_local_scores.get("final_score", 0) or 0) > 0
    ):
        fb = _build_fallback_payload(fallback_local_scores)
        if fb:
            return {
                "ai_ok": False,
                "error": "AI scoring returned 0; falling back to local matcher output.",
                "ai_score": fb,
            }

    return {"ai_ok": True, "ai_score": normalized}


def load_jd_file(jd_path: str) -> dict:
    """Load job description JSON file (simple helper)."""
    with open(jd_path, "r", encoding="utf-8") as f:
        return json.load(f)


# If run as script, quick smoke test (requires valid env + files)
if __name__ == "__main__":
    sample_jd_path = "storage/sample_jd.json"
    sample_resume_path = "storage/sample_resume.json"
    if os.path.exists(sample_jd_path) and os.path.exists(sample_resume_path):
        jd = load_jd_file(sample_jd_path)
        with open(sample_resume_path, "r", encoding="utf-8") as f:
            resume = json.load(f)
        print("Requesting AI score...")
        result = ai_score_resume(resume, jd, timeout=60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(
            "Place sample_jd.json and sample_resume.json in storage/ for quick smoke test."
        )
