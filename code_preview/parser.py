# parser.py
import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, Tuple

import requests
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

AZURE_AI_ENDPOINT = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
DEPLOYMENT_ID = os.getenv("AZURE_OPENAI_DEPLOYMENT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """
    **You are a strict Resume Parsing Assistant.
    Your ONLY job is to extract information explicitly present in the resume text.
    
    CRITICAL RULES:
    1. NO HALLUCINATIONS: Do not infer, guess, or create information. If it's not in the text, leave it empty.
    2. NO PLACEHOLDERS: Do not use "N/A", "None", "Not Specified", or similar placeholders. Use null or empty string/list.
    3. NO SYNONYMS: Extract exact terms (e.g., do not change "ML" to "Machine Learning").
    4. STRICT JSON: Return ONLY valid JSON. No markdown formatting, no explanations.

    OUTPUT SCHEMA:
    {
    "name": string (full name),
    "email": string,
    "phone": string,
    "location": string,
    "skills": list of strings (exact matches only),
    "education": list of {"degree": string, "institution": string, "year": string},
    "experience": list of {"company": string, "role": string, "start_date": string, "end_date": string, "description": list of strings},
    "projects": list of {"name": string, "description": string},
    "summary": string,
    "certificates": list of {"name": string, "issuer": string, "year": string},
    "salary": {"current_ctc_lpa": number or null, "expected_ctc_lpa": number or null}
    }
    **
    """


_PARSER_BASE_PAYLOAD = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "summary": "",
    "certificates": [],
    "courses": [],
    "raw_text": "",
    "salary": {
        "current_ctc_lpa": None,
        "expected_ctc_lpa": None,
    },
}


def _clean_value(value: Any) -> Any:
    """Recursively clean values to remove placeholders."""
    if isinstance(value, str):
        if value.lower() in ["n/a", "none", "not specified", "unknown", "null"]:
            return ""
        return value.strip()
    elif isinstance(value, list):
        return [_clean_value(v) for v in value if v]
    elif isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()}
    return value


def _ensure_parser_payload(
    normalized_text: str, payload: dict | None = None, error: str | None = None
) -> dict:
    """
    Ensures downstream steps always receive a safe, clean payload.
    """
    safe = deepcopy(_PARSER_BASE_PAYLOAD)
    safe["raw_text"] = (
        normalized_text
        if isinstance(normalized_text, str)
        else str(normalized_text or "")
    )

    if isinstance(payload, dict):
        # Clean the payload first
        cleaned_payload = _clean_value(payload)
        for key, value in cleaned_payload.items():
            try:
                if key in safe:
                    safe[str(key)] = value
            except Exception:
                continue

    # Ensure salary structure is preserved
    salary = safe.get("salary") if isinstance(safe.get("salary"), dict) else {}
    safe["salary"] = {
        "current_ctc_lpa": salary.get("current_ctc_lpa"),
        "expected_ctc_lpa": salary.get("expected_ctc_lpa"),
    }

    if error:
        safe["error"] = error

    return safe


def _strip_code_fences(text: str) -> str:
    """
    Remove Markdown code fences like ```json ... ``` that Phi-4 sometimes adds.
    """
    if not isinstance(text, str):
        return ""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned, count=1)
        if "```" in cleaned:
            cleaned = cleaned[: cleaned.rfind("```")]
    return cleaned.strip()


def _attempt_json_parse(content: str) -> Tuple[bool, Dict[str, Any] | None]:
    """
    Try strict JSON parsing first, then a trimmed substring between the first '{' and
    the last '}' (for outputs that contain preamble/epilogue text).
    """
    if not content:
        return False, None

    try:
        return True, json.loads(content)
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = content[start : end + 1]
        try:
            return True, json.loads(snippet)
        except json.JSONDecodeError:
            return False, None
    return False, None


def _invoke_parser_request(
    normalized_text: str, max_tokens: int
) -> Tuple[bool, Dict[str, Any] | str, str]:
    """
    Execute a single API request and try to parse the JSON response.
    Returns (success, payload_or_error, raw_text).
    """
    api_url = f"{AZURE_AI_ENDPOINT}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version=2024-05-01-preview"

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Extract ONLY information that is explicitly present in the resume. "
                "Do NOT infer or guess anything.",
            },
            {"role": "user", "content": normalized_text},
        ],
        "temperature": 0,
        "top_p": 1.0,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(api_url, headers=HEADERS, json=payload)
        data = response.json()
    except Exception as e:
        return False, f"Request failed: {e}", ""

    if isinstance(data, dict) and "error" in data:
        error_msg = data["error"].get("message", data["error"])
        return False, error_msg, ""

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        content = data.get("choices", [{}])[0].get("text", "") or ""
    content = _strip_code_fences(content)

    ok, parsed = _attempt_json_parse(content)
    if ok and isinstance(parsed, dict):
        return True, parsed, content

    return False, "Invalid JSON output", content


def parse_resume(normalized_text: str) -> dict:
    """
    Sends normalized resume text to Azure AI Foundry Phi-4 model (REST API)
    and returns structured JSON output.
    """

    attempt_configs = [1800, 2400]
    last_error = None
    last_raw_text = ""

    for max_tokens in attempt_configs:
        ok, payload_or_error, raw_text = _invoke_parser_request(
            normalized_text, max_tokens
        )
        if ok:
            return _ensure_parser_payload(normalized_text, payload_or_error)

        last_error = payload_or_error
        last_raw_text = raw_text or last_raw_text
        print(f"⚠️ Parser attempt (max_tokens={max_tokens}) failed: {last_error}")

    if last_raw_text:
        os.makedirs("storage/errors", exist_ok=True)
        raw_path = os.path.join("storage/errors", "raw_output.txt")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(last_raw_text)
        print(f"⚠️ Raw model output saved to {raw_path}")

    return _ensure_parser_payload(
        normalized_text, error=last_error or "Invalid JSON output"
    )
