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

if not AZURE_AI_ENDPOINT or not DEPLOYMENT_ID or not API_KEY:
    print("⚠️  MISSING AZURE OPENAI CREDENTIALS ⚠️")
    print("Please check your .env file for:")
    print(" - AZURE_OPENAI_ENDPOINT")
    print(" - AZURE_OPENAI_DEPLOYMENT")
    print(" - AZURE_OPENAI_API_KEY")

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
        
        # Path: prompts/{version}/parser/system_prompt.txt
        prompt_path = os.path.join(base_dir, "prompts", version, "parser", "system_prompt.txt")
        
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
             print(f"⚠️ Prompt file not found at {prompt_path}, trying v1 fallback.")
             # Fallback to v1 if specific version missing
             fallback_path = os.path.join(base_dir, "prompts", "v1", "parser", "system_prompt.txt")
             if os.path.exists(fallback_path):
                 with open(fallback_path, "r", encoding="utf-8") as f:
                     return f.read().strip()

    except Exception as e:
        print(f"⚠️ Failed to load system prompt from file: {e}")
    
    return "You are a resume parser that strictly follows rules."

SYSTEM_PROMPT = _load_system_prompt()


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


def _ensure_parser_payload(
    normalized_text: str, payload: dict | None = None, error: str | None = None
) -> dict:
    """
    Ensures downstream steps always receive a safe payload.
    """
    safe = deepcopy(_PARSER_BASE_PAYLOAD)
    safe["raw_text"] = (
        normalized_text
        if isinstance(normalized_text, str)
        else str(normalized_text or "")
    )

    if isinstance(payload, dict):
        for key, value in payload.items():
            try:
                safe[str(key)] = value
            except Exception:
                continue

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
