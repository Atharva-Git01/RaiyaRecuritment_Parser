# app/ai_scorer.py
import json
import math
import os
import datetime
from dateutil import parser
from copy import deepcopy
from typing import Any, Dict, Tuple, Union, Optional
import requests
from dotenv import load_dotenv

# Import Contracts
from app.scoring_contracts import AIScorerInput, ResumeFacts, JDRequirements, ScoringWeights
from pydantic import ValidationError

# Token usage monitor — logs prompt/completion tokens per LLM call
try:
    from token_usage_monitor import log_usage as _log_token_usage
except ImportError:
    _log_token_usage = None

# --- MONITOR AGENT INJECTION ---
try:
    import sys
    import os
    # Add parent dir so we can reach Monitor_Agent from inside Scoring_Agent
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Monitor_Agent.metrics_collector import log_token_usage as monitor_log_token_usage, log_latency as monitor_log_latency, MetricsCollector, MetricType
except ImportError as e:
    monitor_log_token_usage = monitor_log_latency = MetricsCollector = MetricType = None
    print(f"Warning: Monitor Agent hooks not found: {e}")
# -----------------------------

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
        # ai_scorer.py is in 'phi 4 testing', so base_dir is 'phi 4 testing'
        base_dir = os.path.dirname(os.path.abspath(__file__)) 
        
        # Path: prompts/{version}/ai_scorer/system_prompt.txt
        prompt_path = os.path.join(base_dir, "prompts", version, "ai_scorer", "system_prompt.txt")
        
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
             print(f"Warning: Prompt file not found at {prompt_path}, trying v1 fallback.")
             # Fallback to v1 if specific version missing
             fallback_path = os.path.join(base_dir, "prompts", "v1", "ai_scorer", "system_prompt.txt")
             if os.path.exists(fallback_path):
                 with open(fallback_path, "r", encoding="utf-8") as f:
                     return f.read().strip()

    except Exception as e:
        print(f"Warning: Failed to load system prompt from file: {e}")
    
    return "You are an intelligent AI Resume Evaluator. Score accurately based on JD."

SYSTEM_PROMPT = _load_system_prompt()

# === helper: expected schema keys & weights ===
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
    "position_score",
    "notes",
    "scoring_trace",
]


def _extract_candidate_name(resume_data: Dict[str, Any]) -> str:
    if not isinstance(resume_data, dict):
        return "unknown"
    return (
        resume_data.get("name")
        or (resume_data.get("personal_info") or {}).get("name")
        or resume_data.get("candidate_name")
        or "unknown"
    )


def _clamp_and_int(v: Any) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = 0
    return max(0, min(100, iv))


def _compute_weighted_final(score_map: Dict[str, int], weights: ScoringWeights) -> int:
    """
    Compute final score by SUMMING all (component_score * component_weight).
    """
    total = 0.0
    # Sum all keys ending in '_score' (excluding final_score itself if present)
    for k, v in score_map.items():
        if k.endswith("_score") and k != "final_score":
            # Get weight from ScoringWeights object (default 1.0 if missing, but we expect it to match)
            # weights is a Pydantic model, so we use getattr
            w = getattr(weights, k, 0.0)
            total += (v * w)
            
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
        print(f"Warning: Failed to load evidence rules: {e}")
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
            print(f"Warning: Error evaluating rule {rule.get('id')}: {e}")
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
    # Coerce / clamp numeric fields
    for key in EXPECTED_KEYS:
        if key == "notes":
            val = raw_obj.get("notes", "")
            out["notes"] = str(val)[:500]  # raised from 240 → 500 chars
        elif key == "scoring_trace":
            # Preserve the trace object as-is
            out["scoring_trace"] = raw_obj.get("scoring_trace", {})
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

    # Initialise guardrails_applied as a structured list so guardrail tags
    # are never lost in notes truncation — each fired rule is recorded here.
    out.setdefault("guardrails_applied", [])

    return True, out


def _calculate_total_years(experience_list: list) -> float:
    """
    Calculate total years of experience from a list of experience objects.
    Handles overlapping durations by merging intervals.
    """
    if not experience_list:
        return 0.0
        
    intervals = []
    now = datetime.datetime.now()
    
    for exp in experience_list:
        start_str = exp.get("start") or exp.get("start_date")
        end_str = exp.get("end") or exp.get("end_date")
        
        if not start_str:
            continue
            
        try:
            start_date = parser.parse(start_str, fuzzy=True)
            if not end_str or str(end_str).lower() in ["present", "current", "now"]:
                end_date = now
            else:
                end_date = parser.parse(end_str, fuzzy=True)
            
            if start_date > end_date:
                continue
            
            intervals.append((start_date, end_date))
        except Exception:
            continue
            
    if not intervals:
        return 0.0
        
    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = []
    if intervals:
        curr_start, curr_end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start <= curr_end:
                 curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
    total_days = sum((end - start).days for start, end in merged)
    return total_days / 365.25


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
    candidate_name = _extract_candidate_name(resume_for_prompt)

    # === SALARY NORMALIZATION ===
    # Convert numeric salary to "LPA" string format for clearer AI context
    try:
        raw_sal = resume_for_prompt.get("salary_expectation") or {}  # guard: None → {}
        val = raw_sal.get("value") or raw_sal.get("amount")  # resumes use 'amount', not 'value'
        curr = raw_sal.get("currency", "INR")
        
        if val and isinstance(val, (int, float)):
            if str(curr).upper() == "INR" and val > 100000:
                lpa_val = val / 100000.0
                resume_for_prompt["salary_expectation"]["value_formatted"] = f"{lpa_val:.2f} Lakhs Per Annum (LPA)"
    except Exception as e:
        print(f"Warning: Salary normalization error: {e}")
    
    # === SANITIZATION: Remove problematic pre-calculated experience fields ===
    # Using model_dump might have cleaned it if strictly defined, but extra='allow' means we manual check
    keys_to_remove = ["total_experience_years", "experience_years", "total_experience", "raw_text"]
    for k in keys_to_remove:
        if k in resume_for_prompt:
            del resume_for_prompt[k]

    # === EVIDENCE ENFORCEMENT: Strip skills/technologies lists from AI view ===
    # The AI ignores the evidence-based scoring rule and awards points whenever a
    # skill/technology appears in resume.skills[] or resume.technologies[],
    # regardless of whether it was actually used in any job/project.
    # Removing these lists forces the AI to find evidence only in experience text.
    # We keep a copy for post-processing guardrails.
    _skills_list_backup = resume_for_prompt.pop("skills", None) or []
    _tools_list_backup  = resume_for_prompt.pop("tools", None) or []      # tools stay for tools_score
    _tech_list_backup   = resume_for_prompt.pop("technologies", None) or []
    # Restore tools — tools scoring is less susceptible and tools rarely appear in exp text
    resume_for_prompt["tools"] = _tools_list_backup or None  # keep None if originally absent
    print(f"   -> Evidence enforcement: stripped resume.skills ({len(_skills_list_backup)} items) "
          f"and resume.technologies ({len(_tech_list_backup)} items) from AI prompt.")

    # === EVIDENCE RULES CHECK ===
    evidence_rules = _load_evidence_rules()
    triggered_constraints = _evaluate_rules(resume_for_prompt, evidence_rules)
    
    constraints_text = ""
    if triggered_constraints:
        constraints_text = "\n\n### MANDATORY SCORING CONSTRAINTS (EVIDENCE-BASED):\n" + "\n".join(triggered_constraints)

    current_date_str = datetime.date.today().isoformat()
    
    user_prompt = (
        f"CURRENT_DATE: {current_date_str}\n"
        "Below are the job description and the parsed resume JSON. Score strictly per the SYSTEM_PROMPT.\n\n"
        f"JOB_DESCRIPTION:\n{json.dumps(validated_jd, ensure_ascii=False)}\n\n"
        f"PARSED_RESUME:\n{json.dumps(resume_for_prompt, ensure_ascii=False)}"
        f"{constraints_text}\n\n"
        "IMPORTANT SCORING RULES:\n"
        "1. **Evidence-Based Scoring (STRICT)**: You will notice that resume.skills[] and "
        "resume.technologies[] have been REMOVED from the resume. You MUST score skills_score "
        "and technologies_score ONLY based on evidence found inside 'experience[].description' "
        "or 'projects[].description'. If a skill or technology is not explicitly mentioned in "
        "those fields, award 0 for it — even if you believe the candidate has it. "
        "Do NOT infer or assume skills that are not written in the experience text.\n"
        "2. **Experience Calculation**: Use CURRENT_DATE to calculate duration for 'Present' roles.\n"
        "3. **Salary**: Interpret salary carefully. '7.2 LPA' means 7,20,000 INR. Compare against JD criteria numerically.\n"
        "4. **Relevance**: Only award relevant_experience credit for roles directly related to the JD's job_title and technologies.\n\n"
        "**CRITICAL OUTPUT INSTRUCTION**:\n"
        "You MUST return ONLY a single valid JSON object. Do not include any markdown formatting (like ```json), explanations, or text outside the JSON. "
        "The output must be parseable by `json.loads()`."
    )

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 1500,
        "response_format": { "type": "json_object" }
    }

    # Retry logic: 3 attempts
    max_retries = 3
    effective_timeout = timeout if timeout > 90 else 180
    
    import time
    last_error = None
    data = None
    _call_usage = {}  # token usage from this call — populated after successful response
    _request_latency_ms = 0
    overrides_fired = []
    
    # Generate a run identifier for the Monitor Agent (using timestamp)
    monitor_run_id = f"run_{int(time.time())}"
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"   -> AI Request Attempt {attempt}/{max_retries} (timeout={effective_timeout}s)...")
            
            start_time = time.time()
            resp = requests.post(api_url, headers=HEADERS, json=payload, timeout=effective_timeout)
            resp.raise_for_status() # Raise error for 4xx/5xx
            duration = time.time() - start_time
            _request_latency_ms = int(duration * 1000)
            
            if monitor_log_latency:
                monitor_log_latency(monitor_run_id, "ai_scorer", duration)
                
            data = resp.json()
            # ── Token usage logging ──────────────────────────────────────────
            try:
                _usage = data.get("usage", {})
                if _usage:
                    _call_usage = {
                        "prompt_tokens":     int(_usage.get("prompt_tokens",     _usage.get("input_tokens",  0))),
                        "completion_tokens": int(_usage.get("completion_tokens", _usage.get("output_tokens", 0))),
                        "total_tokens":      int(_usage.get("total_tokens",      0)),
                    }
                    if _log_token_usage:
                        _log_token_usage(
                            candidate=candidate_name,
                            usage=_usage,
                            model=DEPLOYMENT_ID,
                        )
                    if monitor_log_token_usage:
                        monitor_log_token_usage(
                            run_id=monitor_run_id, 
                            stage="ai_scorer", 
                            prompt_tokens=_call_usage["prompt_tokens"], 
                            completion_tokens=_call_usage["completion_tokens"], 
                            model=DEPLOYMENT_ID
                        )
            except Exception as e:
                print(f"Warning: Monitor Agent Token Logging failed: {e}")
            # ─────────────────────────────────────────────────────────────────
            break  # success
        except Exception as e:
            last_error = e
            print(f"      Warning: Attempt {attempt} failed: {e}")
            if MetricsCollector:
                MetricsCollector.log_event(monitor_run_id, "ai_scorer", MetricType.ERROR, 1.0, {"error": str(e)})
            if attempt < max_retries:
                time.sleep(2) # Brief backoff
    
    if data is None:
        return {"ai_ok": False, "error": f"AI request failed after {max_retries} attempts. Last error: {last_error}"}

    # Detect API-level error
    if isinstance(data, dict) and "error" in data:
        if MetricsCollector:
            MetricsCollector.log_event(monitor_run_id, "ai_scorer", MetricType.ERROR, 1.0, {"error": "API returned an error object"})
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
    
    try:
        # `parsed` holds the JSON object from AI output.
        # Pass it directly to validate_ai_score_output for business logic validation / normalization.
        valid, normalized = validate_ai_score_output(parsed, validated_input.weights, guardrail_context=guardrail_ctx)
        if not valid:
            # This branch handles business logic validation failures within validate_ai_score_output
            if MetricsCollector:
                MetricsCollector.log_event(monitor_run_id, "ai_scorer", MetricType.VALIDATION_FAILED, 1.0, {"error": "AI output business logic validation failed"})
            return {
                "ai_ok": False,
                "error": "AI output validation failed.",
                "raw_ai": parsed,
            }
        normalized["ai_ok"] = True # Indicate success after all validations
    except ValidationError as e:
        # Pydantic schema violation detected
        if MetricsCollector:
            MetricsCollector.log_event(monitor_run_id, "ai_scorer", MetricType.SCHEMA_VIOLATION, 1.0, {"error": str(e)})
        
        err_str = f"Pydantic Validation failed: {e}"
        print(f"   -> ValidationError: {err_str}")
        return {"ai_ok": False, "error": err_str, "raw_ai": parsed}
    except Exception as e:
        # General parse error (e.g., if `parsed` wasn't a dict or other unexpected issues)
        if MetricsCollector:
            MetricsCollector.log_event(monitor_run_id, "ai_scorer", MetricType.ERROR, 1.0, {"error": f"Parse Exception: {e}"})
        
        err_str = f"Exception parsing output: {e}"
        print(f"   -> JSON Parse Exception: {err_str}")
        return {"ai_ok": False, "error": err_str, "raw_ai": parsed}

    # === DETERMINISTIC OVERRIDES ===

    # -1. Experience & Relevant Experience Band Snapping
    # The AI often returns interpolated out-of-band values (e.g. 10, 20) instead of
    # the JD-defined step values. We calculate years deterministically from resume dates
    # and snap both scores to the exact criteria bands.
    try:
        exp_list = resume_for_prompt.get("experience", [])
        total_years = _calculate_total_years(exp_list)

        # ── Total Experience band (from JD criteria) ──
        # JD: >=8yr→100, 5-7yr→80, 3-4yr→60, <3yr→30
        def _exp_band(years: float) -> int:
            if years >= 8:  return 100
            if years >= 5:  return 80
            if years >= 3:  return 60
            return 30

        det_exp_score = _exp_band(total_years)
        ai_exp_score  = normalized.get("experience_score", 0)
        if ai_exp_score != det_exp_score:
            print(f"   -> DETERMINISTIC EXP: Overriding AI exp_score {ai_exp_score} with {det_exp_score} ({total_years:.1f}yr)")
            normalized["experience_score"] = det_exp_score
            overrides_fired.append("experience_score")

        # ── Relevant Experience band ──
        # JD: >=5yr_relevant→100, 3-4yr→73, 1-2yr→50, <1yr→17
        # We use total_years as a proxy for relevant experience since the AI decides
        # relevance — we only correct the band value, not the relevance judgement.
        # Read what band the AI intended from its trace note, then snap the value.
        VALID_REL_EXP_BANDS = {100, 73, 50, 17, 0}
        ai_rel_score = normalized.get("relevant_experience_score", 0)
        if ai_rel_score not in VALID_REL_EXP_BANDS:
            # Snap to nearest valid band
            nearest = min(VALID_REL_EXP_BANDS, key=lambda x: abs(x - ai_rel_score))
            print(f"   -> DETERMINISTIC REL_EXP: Snapping off-band {ai_rel_score} to {nearest}")
            normalized["relevant_experience_score"] = nearest
            overrides_fired.append("relevant_experience_score_band_snap")

    except Exception as e:
        print(f"   -> Experience Band Override Failed: {e}")

    # 0. Qualification Score Override
    # The AI frequently misclassifies non-engineering degrees (BCA, MCA, B.Sc)

    # as 'Bachelor/Master in Engineering' and awards 80 pts instead of the
    # correct 'Other' tier (50 pts).
    # JD criteria: Master's Engineering→100, Bachelor's Engineering→80, Other→50
    try:
        education = resume_for_prompt.get("education", [])
        if education:
            all_degrees = " ".join(
                (e.get("degree", "") + " " + e.get("field", "")).lower()
                for e in education
            )
            ENGINEERING_KEYWORDS = [
                "b.tech", "btech", "b.e", "be ", "m.tech", "mtech", "m.e", "me ",
                "bachelor of technology", "bachelor of engineering",
                "master of technology", "master of engineering",
                "b.tech.", "m.tech.",
            ]
            MASTERS_ENGINEERING = ["m.tech", "mtech", "m.e", "master of technology", "master of engineering"]
            OTHER_KEYWORDS = [
                "bca", "mca", "b.sc", "bsc", "b.a", "ba ", "b.com",
                "bachelor of computer application", "master of computer application",
                "bachelor of science", "master of science", "b.voc",
            ]

            is_engineering  = any(kw in all_degrees for kw in ENGINEERING_KEYWORDS)
            is_masters_eng  = any(kw in all_degrees for kw in MASTERS_ENGINEERING)
            is_other        = any(kw in all_degrees for kw in OTHER_KEYWORDS)

            # Determine correct tier score from JD qualification criteria
            jd_qual_crit = {}
            try:
                jd_qual_crit = jd_dict.get("scoring", {}).get("qualification", {}).get("criteria", {})
            except Exception:
                pass

            # Get tier scores (fallback to canonical JD values if criteria missing)
            masters_eng_score  = jd_qual_crit.get("Master's Degree in Engineering", 100)
            bachelors_eng_score = jd_qual_crit.get("Bachelor's Degree in Engineering", 80)
            other_score         = jd_qual_crit.get("Other", 50)

            correct_qual_score = None
            if is_other and not is_engineering:
                # Non-engineering degree → 'Other' tier
                correct_qual_score = int(other_score)
            elif is_engineering and is_masters_eng:
                correct_qual_score = int(masters_eng_score)
            elif is_engineering:
                correct_qual_score = int(bachelors_eng_score)

            if correct_qual_score is not None:
                ai_qual = normalized.get("qualification_score", 0)
                if ai_qual != correct_qual_score:
                    print(f"   -> DETERMINISTIC QUAL: Overriding AI score {ai_qual} with {correct_qual_score} (degrees: {all_degrees[:80]})")
                    normalized["qualification_score"] = correct_qual_score
                    overrides_fired.append("qualification_score")
    except Exception as e:
        print(f"   -> Qualification Override Failed: {e}")

    # 1. Salary Score Override
    # The AI often struggles with numeric ranges. We allow Python to calculate this strictly if possible.

    try:
        # Extract Resume Salary (LPA)
        resume_lpa = None
        val = None  # initialise before conditional to prevent NameError
        curr = "INR"
        raw_sal = validated_input.resume.salary_expectation
        # salary_expectation is Optional[dict]; resumes use 'amount', fallback to 'value'
        if raw_sal:
            val = (raw_sal.get("value") or raw_sal.get("amount")) if isinstance(raw_sal, dict) else (getattr(raw_sal, 'value', None) or getattr(raw_sal, 'amount', None))
            curr = (raw_sal.get("currency", "INR") if isinstance(raw_sal, dict) else str(getattr(raw_sal, 'currency', 'INR'))).upper()
        if raw_sal and val:
            if curr == "INR":
                if val > 100000: # Assume absolute value
                     resume_lpa = val / 100000.0
                else: # Assume already in LPA if small, or uncertain.
                     resume_lpa = val if val < 100 else None
        
        if resume_lpa:
            # Safely get criteria from jd_dict which is already a clean dictionary
            # jd_dict is defined earlier in the function: jd_dict = validated_input.jd.model_dump()
            # or we can re-fetch if variable scope is issue, but it should be fine.
            # Wait, `jd_dict` is defined at line 437. `ai_score_resume` is one big function.
            # But let's be safe and use getattr loop or just try block.
            
            jd_salary_crit = None
            try:
                # Robustly convert Pydantic model to dict
                raw_jd = {}
                if hasattr(validated_input.jd, "model_dump"):
                     raw_jd = validated_input.jd.model_dump()
                elif hasattr(validated_input.jd, "dict"):
                     raw_jd = validated_input.jd.dict()
                else:
                     raw_jd = validated_input.jd.__dict__
                
                jd_salary_crit = raw_jd.get("scoring", {}).get("salary", {}).get("criteria", {})
            except Exception as e:
                print(f"   -> Deterministic Salary: Criteria extraction failed: {e}")
                pass
        
        if resume_lpa and jd_salary_crit:
            best_score = 0
            # Logic: We want to match the resume_lpa to the criteria ranges.
            # Criteria keys examples: "<3", "3-6", "6-10", ">10"
            for range_str, score in jd_salary_crit.items():
                try:
                   # Simple parsing of ranges
                   r = range_str.replace("LPA", "").strip()
                   match = False
                   
                   if r.startswith("<"):
                       limit = float(r[1:])
                       if resume_lpa < limit: match = True
                   elif r.startswith(">"):
                       limit = float(r[1:])
                       if resume_lpa > limit: match = True
                   elif "-" in r:
                       parts = r.split("-")
                       low, high = float(parts[0]), float(parts[1])
                       if low <= resume_lpa <= high: match = True
                   
                   if match:
                       # If multiple match (rare), take max? Or just take first? 
                       # Usually ranges are exclusive.
                       best_score = max(best_score, int(score))
                       
                except Exception:
                    continue
            
            # Application
            if best_score > 0:
                print(f"   -> DETERMINISTIC SALARY: Overriding AI score {normalized.get('salary_score')} with {best_score} for {resume_lpa} LPA")
                normalized["salary_score"] = best_score
                normalized["notes"] = (normalized.get("notes", "") + f" [Salary Calculated: {best_score} for {resume_lpa} LPA]").strip()
                overrides_fired.append("salary_score")

    except Exception as e:
        print(f"   -> Salary Override Failed: {e}")

    # === GUARDRAIL: Strict Experience Duration Check ===
    # For candidates with < 1 year total experience (Freshers), we cap the experience scores.
    # This prevents AI hallucinations where project complexity overrides tenure.
    try:
        total_years = _calculate_total_years(resume_for_prompt.get("experience", []))
        if total_years < 1.0:
            print(f"   -> GUARDRAIL TRIGGERED: Experience {total_years:.2f}y < 1.0y. Clamping scores.")
            
            # Cap Experience Score at 25 (Low tier)
            normalized["experience_score"] = min(normalized.get("experience_score", 0), 25)
            
            # Cap Relevant Experience Score at 25
            if "relevant_experience_score" in normalized:
                 normalized["relevant_experience_score"] = min(normalized["relevant_experience_score"], 25)
            
            # Recalculate Final Score using the new component scores
            normalized["final_score"] = _compute_weighted_final(normalized, validated_input.weights)

            # Record in structured guardrails_applied list (never lost to truncation)
            guardrails_applied = normalized.setdefault("guardrails_applied", [])
            guardrail_tag = f"Exp. Limited <1y ({total_years:.1f}yr calculated)"
            if guardrail_tag not in guardrails_applied:
                guardrails_applied.append(guardrail_tag)
            overrides_fired.append("fresher_experience_guardrail")
            # Also append short tag to notes for backwards-compatibility
            normalized["notes"] = (normalized.get("notes", "") + " [Exp. Limited <1y]").strip()
            
    except Exception as e:
        print(f"   -> GUARDRAIL ERROR: {e}")

    # === FINAL SCORE RECOMPUTE (always last) ===
    # Qualification override, salary override, and guardrails all mutate component
    # scores independently. Recompute final_score here so it always reflects the
    # true weighted sum — regardless of which overrides fired.
    try:
        normalized["final_score"] = _compute_weighted_final(normalized, validated_input.weights)
    except Exception as e:
        print(f"   -> Final Score Recompute Failed: {e}")

    # === SCORING TRACE RECONCILIATION ===
    # Guardrails and deterministic overrides mutate component scores AFTER the
    # AI writes the scoring_trace. Sync trace score_awarded fields with the
    # actual final component values so the trace is always truthful.
    try:
        TRACE_TO_RESULT = {
            "relevant_experience": "relevant_experience_score",
            "salary":              "salary_score",
            "qualification":       "qualification_score",
            "skills":              "skills_score",
            "technologies":        "technologies_score",
            "experience":          "experience_score",
            "tools":               "tools_score",
            "position":            "position_score",
        }
        trace = normalized.get("scoring_trace", {})
        if isinstance(trace, dict):
            for trace_key, result_key in TRACE_TO_RESULT.items():
                if trace_key in trace and isinstance(trace[trace_key], dict):
                    final_val = normalized.get(result_key)
                    if final_val is not None:
                        trace[trace_key]["score_awarded"] = final_val
            normalized["scoring_trace"] = trace
    except Exception as e:
        print(f"   -> Trace Reconciliation Failed: {e}")

    normalized["overrides_fired"] = sorted(set(overrides_fired))
    normalized["evaluation_metadata"] = {
        "candidate_name": candidate_name,
        "deployment": DEPLOYMENT_ID or "unknown",
        "prompt_version": _get_active_version(),
        "latency_ms": _request_latency_ms,
    }

    return {"ai_ok": True, "ai_score": normalized, "token_usage": _call_usage}

