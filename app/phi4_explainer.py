# app/phi4_explainer.py
import json
import os
import hashlib
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

from app.schemas import CandidateFacts, JDRequirements, Phi4Explanation, LearningEvent
from app.ledger_db import log_learning_event

load_dotenv()

AZURE_AI_ENDPOINT = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
DEPLOYMENT_ID = os.getenv("AZURE_OPENAI_DEPLOYMENT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

PROMPT_VERSION = "v1" # Default fallback

def get_config():
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "config", "system_config.json")
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {"active_prompt_version": "v1"}

def _load_prompt_template(version=None) -> str:
    ver = version or get_config().get("active_prompt_version", "v1")
    # New Path: prompts/{ver}/explainer/system_prompt.txt
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", ver, "explainer", "system_prompt.txt")
    
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
            
    # Fallback to v1
    fallback_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "v1", "explainer", "system_prompt.txt")
    if os.path.exists(fallback_path):
         with open(fallback_path, "r", encoding="utf-8") as f:
             return f.read()
             
    return "Error: Prompt file not found."

def _compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def generate_explanation(
    facts: CandidateFacts, 
    jd: JDRequirements,
    job_id: str
) -> Optional[Phi4Explanation]:
    """
    Generates an explanation using Phi-4.
    Strictly validates output and logs to Ledger.
    """
    if not AZURE_AI_ENDPOINT or not API_KEY:
        print("⚠️ Missing Azure Credentials for Phi-4 Explainer")
        return None

    # Prepare Context
    context = {
        "candidate_facts": facts.dict(),
        "jd": jd.dict()
    }
    context_json = json.dumps(context, indent=2, default=str)
    
    # Load Prompt
    template = _load_prompt_template()
    system_prompt = template.format(context_json=context_json)
    
    # Input Hash for Ledger
    input_hash = _compute_hash(system_prompt)

    # Call API
    api_url = f"{AZURE_AI_ENDPOINT}/openai/deployments/{DEPLOYMENT_ID}/chat/completions?api-version=2024-05-01-preview"
    payload = {
        "messages": [
             {"role": "system", "content": "You are a helpful AI assistant."},
             {"role": "user", "content": system_prompt}
        ],
        "temperature": 0.0, # Deterministic behavior
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
    raw_response = {}
    validation_status = "FAIL"
    parsed_output = None
    error_tags = []

    try:
        response = requests.post(api_url, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        raw_response = {"content": content}
        
        # Parse JSON
        obj = json.loads(content)
        
        # Validate Schema
        parsed_output = Phi4Explanation(**obj)
        
        # Guardrails
        from app.guardrails import validate_explanation
        validation_status, guardrail_errors = validate_explanation(facts, jd, parsed_output)
        error_tags.extend(guardrail_errors)
        
    except json.JSONDecodeError:
        error_tags.append("invalid_json")
        raw_response["error"] = "JSONDecodeError"
    except Exception as e:
        error_tags.append(f"api_error: {str(e)}")
        raw_response["error"] = str(e)
        if parsed_output is None: 
             # Try to see if it failed pydantic validation
             if "validation error" in str(e).lower():
                 error_tags.append("schema_violation")

    # Log to Ledger
    try:
        event = LearningEvent(
            job_id=job_id,
            prompt_version=get_config().get("active_prompt_version", "v1"),
            input_hash=input_hash,
            context=context,
            phi4_response=raw_response,
            validation_status=validation_status,
            error_tags=error_tags
        )
        log_learning_event(event)
    except Exception as e:
        print(f"⚠️ Failed to log to ledger: {e}")

    return parsed_output
