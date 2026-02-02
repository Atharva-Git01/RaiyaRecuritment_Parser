# app/ai_scorer.py
import json
import math
import os
from copy import deepcopy
from typing import Any, Dict, Tuple, Union, Optional
import requests
from dotenv import load_dotenv

# Import Contracts
from app.scoring_contracts import AIScorerInput, ResumeFacts, JDRequirements, ScoringWeights

# === JD SCORING NORMALIZATION HELPERS ===

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

# === SYSTEM PROMPT ===
# === SYSTEM PROMPT LOADING ===
def _get_active_version() -> str:
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "config", "system_config.json")
        with open(config_path, "r") as f:
            cfg = json.load(f)
            return cfg.get("active_prompt_version", "v1")
    except Exception:
        return "v1"

def _load_system_prompt() -> str:
    """Load the system prompt dynamically based on active version."""
    try:
        version = _get_active_version()
        base_dir = os.path.dirname(os.path.dirname(__file__)) # Up one level from app/
        
        # Path: prompts/{version}/ai_scorer/system_prompt.txt
        prompt_path = os.path.join(base_dir, "prompts", version, "ai_scorer", "system_prompt.txt")
        
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
             print(f"⚠️ Prompt file not found at {prompt_path}, trying v1 fallback.")
             # Fallback to v1 if specific version missing
             fallback_path = os.path.join(base_dir, "prompts", "v1", "ai_scorer", "system_prompt.txt")
             if os.path.exists(fallback_path):
                 with open(fallback_path, "r", encoding="utf-8") as f:
                     return f.read().strip()

    except Exception as e:
        print(f"⚠️ Failed to load system prompt from file: {e}")
    
    return "You are an intelligent AI Resume Evaluator. Score accurately based on JD."

SYSTEM_PROMPT = _load_system_prompt()

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


def _clamp_and_int(v: Any) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = 0
    return max(0, min(100, iv))


def _compute_weighted_final(score_map: Dict[str, int], weights: ScoringWeights) -> int:
    total = 0.0
    w_dict = weights.model_dump()
    for k, w in w_dict.items():
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


# === EVIDENCE RULES EVALUATION ===

def _load_evidence_rules() -> list:
    """Load evidence rules from config/evidence_rules.json."""
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        rules_path = os.path.join(base_dir, "config", "evidence_rules.json")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load evidence rules: {e}")
    return []

def _get_nested_val(obj: dict, path: str):
    """Safe nested get, e.g. resume.experience"""
    parts = path.split(".")
    curr = obj
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        else:
            return None
    return curr

def _evaluate_rules(resume_data: dict, rules: list) -> list:
    """
    Evaluate rules against resume data.
    Returns a list of triggered rule descriptions/actions.
    """
    triggered = []
    
    # Wrap in "resume" key if path expects it (e.g., "resume.experience")
    # Our resume_data is usually the inner content, but let's standardize
    context = {"resume": resume_data}

    for rule in rules:
        try:
            cond = rule.get("condition", {})
            field_path = cond.get("field", "")
            operator = cond.get("operator", "")
            
            val = _get_nested_val(context, field_path)
            
            is_triggered = False
            
            if operator == "contains_keyword_ratio":
                # Check ratio of items containing keyword
                if isinstance(val, list) and val:
                    keyword = cond.get("keyword", "").lower()
                    threshold = cond.get("threshold", 0.0)
                    count = 0
                    for item in val:
                        # naive check in string representation of item
                        if keyword in str(item).lower():
                            count += 1
                    if (count / len(val)) >= threshold:
                        is_triggered = True
                        
            elif operator == "empty":
                # Check if empty string, list or None
                if val in [None, "", [], {}]:
                    is_triggered = True
                    
            elif operator == "avg_duration_months_lt":
                # Special logic for duration
                threshold_months = cond.get("value", 0)
                if isinstance(val, list) and val:
                    total_dur = 0
                    valid_items = 0
                    from app.validator import calculate_duration
                    for item in val:
                        s = item.get("start_date")
                        e = item.get("end_date")
                        dur = calculate_duration(s, e) # returns years
                        if dur > 0:
                            total_dur += dur * 12 # to months
                            valid_items += 1
                    
                    if valid_items > 0:
                        avg_months = total_dur / valid_items
                        if avg_months < threshold_months:
                            is_triggered = True

            if is_triggered:
                desc = rule.get("description", "")
                action = rule.get("action", {})
                triggered.append(f"CONSTRAINT: {desc} -> Action: Apply {action.get('operation')} {action.get('value')} to {action.get('target')}")
                
        except Exception as e:
            print(f"⚠️ Error evaluating rule {rule.get('id')}: {e}")
            continue
            
    return triggered


# Import guardrails
from app.ai_guardrails import apply_guardrails, GuardrailContext

def validate_ai_score_output(
    raw_obj: Any, 
    weights: ScoringWeights,
    guardrail_context: Optional[GuardrailContext] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Ensure output has required keys, integer 0-100 scores, and a notes string.
    Apply guardrails to sanitize scores based on evidence.
    If final_score is missing or inconsistent, recompute using weights.
    """
    out = {}
    if not isinstance(raw_obj, dict):
        return False, {"error": "AI output is not a JSON object."}

    # Coerce / clamp numeric fields
    for key in EXPECTED_KEYS:
        if key == "notes":
            val = raw_obj.get("notes", "")
            out["notes"] = str(val)[:240]
        else:
            val = raw_obj.get(key)
            out[key] = _clamp_and_int(val)

    # ---------------------------
    # GUARDRAILS APPLICATION
    # ---------------------------
    # Apply guardrails if context is provided
    if guardrail_context:
        out = apply_guardrails(out, guardrail_context)

    # ---------------------------
    # SINGLE PASS SCORE CALCULATION
    # ---------------------------
    # We explicitly ignore the AI's hallucinated/draft 'final_score'.
    # The Source of Truth is ALWAYS the weighted sum of the (guarded) component scores.
    out["final_score"] = _compute_weighted_final(out, weights)

    return True, out


def ai_score_resume(
    parsed_resume: Union[dict, ResumeFacts],
    job_description: Union[dict, JDRequirements],
    timeout: int = 90,
    scoring_weights: Union[dict, ScoringWeights, None] = None
) -> dict:
    """
    Use Azure/OpenAI-compatible REST endpoint to request a full JD scoring from the LLM.
    This function enforces the system prompt (zero-hallucination + exact schema).
    Returns dict: {"ai_ok": bool, "ai_score": {...}} or {"ai_ok": False, "error": "..."}
    """
    
    # ---------------------------
    # CONTRACT ENFORCEMENT
    # ---------------------------
    
    # 1. Weights
    # If weights passed explicitly, use them. Else check JD. Else default.
    final_weights = None
    
    try:
        if isinstance(scoring_weights, ScoringWeights):
            final_weights = scoring_weights
        elif isinstance(scoring_weights, dict):
            final_weights = ScoringWeights(**scoring_weights)
        else:
            # Try to get from JD if it's a dict or JDRequirements model
            jd_obj = job_description
            if hasattr(job_description, "weights") and job_description.weights:
                # Assuming job_description is Pydantic and has weights
                 final_weights = ScoringWeights(**job_description.weights)
            elif isinstance(job_description, dict) and "weights" in job_description:
                 final_weights = ScoringWeights(**job_description["weights"])
            else:
                # Fallback to default
                final_weights = ScoringWeights()
    except Exception as e:
        return {"ai_ok": False, "error": f"Invalid Scoring Weights: {e}"}

    # 2. Resume & JD Input Validation
    try:
        if not isinstance(parsed_resume, ResumeFacts):
            resume_input = ResumeFacts(**parsed_resume)
        else:
            resume_input = parsed_resume
            
        if not isinstance(job_description, JDRequirements):
            jd_input = JDRequirements(**job_description) 
        else:
            jd_input = job_description
            
        validated_input = AIScorerInput(
            resume=resume_input,
            jd=jd_input,
            weights=final_weights
        )
    except Exception as e:
         return {"ai_ok": False, "error": f"Input Contract Violation: {e}"}
         
    # ---------------------------
    # EXECUTION
    # ---------------------------
    
    # 1. Validation & Setup (Azure)
    if not AZURE_AI_ENDPOINT or not DEPLOYMENT_ID or not API_KEY:
        return {
            "ai_ok": False,
            "error": "Missing AZURE_OPENAI credentials.",
        }

    api_url = f"{AZURE_AI_ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version=2024-05-01-preview"

    # --- NEW: Phase 4 Part 3 Integration ---
    from app.jd_validator import validate_jd

    # Validate + normalize JD completely (using dict representation)
    # We use valid_input.jd.model_dump() to get the clean dict
    jd_dict = validated_input.jd.model_dump()
    
    # NOTE: validate_jd might expect specific keys not present if we just dumped JDRequirements without extras.
    # But JDRequirements allows extra, so if we passed in a full JD dict, it should be fine.
    validated_jd = validate_jd(jd_dict)

    # Optimization: Strip raw_text and use compact JSON to save tokens/time
    resume_for_prompt = validated_input.resume.model_dump()
    
    # === SANITIZATION: Remove problematic pre-calculated experience fields ===
    # Using model_dump might have cleaned it if strictly defined, but extra='allow' means we manual check
    keys_to_remove = ["total_experience_years", "experience_years", "total_experience", "raw_text"]
    for k in keys_to_remove:
        if k in resume_for_prompt:
            del resume_for_prompt[k]

    # === EVIDENCE RULES CHECK ===
    evidence_rules = _load_evidence_rules()
    triggered_constraints = _evaluate_rules(resume_for_prompt, evidence_rules)
    
    constraints_text = ""
    if triggered_constraints:
        constraints_text = "\n\n### MANDATORY SCORING CONSTRAINTS (EVIDENCE-BASED):\n" + "\n".join(triggered_constraints)

    user_prompt = (
        "Below are the job description and the parsed resume JSON. Score strictly per the SYSTEM_PROMPT.\n\n"
        f"JOB_DESCRIPTION:\n{json.dumps(validated_jd, ensure_ascii=False)}\n\n"
        f"PARSED_RESUME:\n{json.dumps(resume_for_prompt, ensure_ascii=False)}"
        f"{constraints_text}\n\n"
        "IMPORTANT: Use the 'relevant_experience_map' (if present) to weight the relevance of Skills, Tools, and Technologies. "
        "Skills with higher years of experience in this map MUST receive higher relevance scores. "
        "For example, 5 years of usage is significantly better than 1 year.\n\n"
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

    # Retry logic: 3 attempts
    max_retries = 3
    effective_timeout = timeout if timeout > 90 else 180
    
    import time
    last_error = None
    data = None
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   -> AI Request Attempt {attempt}/{max_retries} (timeout={effective_timeout}s)...")
            resp = requests.post(api_url, headers=HEADERS, json=payload, timeout=effective_timeout)
            resp.raise_for_status() # Raise error for 4xx/5xx
            data = resp.json()
            break # Success
        except Exception as e:
            last_error = e
            print(f"      ⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(2) # Brief backoff
    
    if data is None:
        return {"ai_ok": False, "error": f"AI request failed after {max_retries} attempts. Last error: {last_error}"}

    # Detect API-level error
    if isinstance(data, dict) and "error" in data:
        return {"ai_ok": False, "error": data["error"].get("message", data["error"])}

    # Extract raw assistant content robustly
    content = ""
    try:
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
        with open("storage/errors/ai_raw_empty_response.json", "w", encoding="utf-8") as f:
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
    # Pass weights to validation function for correct calculation
    # Create Guardrail Context
    guardrail_ctx = GuardrailContext(
        resume=validated_input.resume,
        jd=validated_input.jd
    )
    
    valid, normalized = validate_ai_score_output(parsed, validated_input.weights, guardrail_context=guardrail_ctx)
    if not valid:
        return {
            "ai_ok": False,
            "error": "AI output validation failed.",
            "raw_ai": parsed,
        }

    return {"ai_ok": True, "ai_score": normalized}
