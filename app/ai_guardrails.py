import json
import os
from typing import Dict, List, Tuple, Protocol, Any
from dataclasses import dataclass
from app.scoring_contracts import ResumeFacts, JDRequirements
from app.validator import calculate_duration

@dataclass
class GuardrailContext:
    resume: ResumeFacts
    jd: JDRequirements

class GuardrailRule(Protocol):
    name: str
    
    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        """
        Apply rule to the score map.
        Returns: (updated_score_map, list_of_notes_to_append)
        """
        ...

# --- Existing Concrete Rules ---
class SkillsEvidenceRule:
    name = "Skills Evidence Check"
    
    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        notes = []
        # If resume has no skills, skill score must be 0
        if not context.resume.skills:
            if score_map.get("skills_score", 0) > 0:
                score_map["skills_score"] = 0
                notes.append("[Guardrail] Skills score zeroed: No skills found in resume.")
        return score_map, notes

class ExperienceEvidenceRule:
    name = "Experience Evidence Check"
    
    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        notes = []
        # If resume has no experience entries, experience categories should be 0
        if not context.resume.experience:
            for key in ["experience_score", "relevant_experience_score", "responsibilities_score"]:
                if score_map.get(key, 0) > 0:
                    score_map[key] = 0
                    notes.append(f"[Guardrail] {key} zeroed: No experience entries found.")
        return score_map, notes

class ProjectsEvidenceRule:
    name = "Projects Evidence Check"
    
    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        notes = []
        if not context.resume.projects:
            if score_map.get("projects_score", 0) > 0:
                score_map["projects_score"] = 0
                notes.append("[Guardrail] Projects score zeroed: No projects found.")
        return score_map, notes

class CertificationsEvidenceRule:
    name = "Certifications Evidence Check"
    
    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        notes = []
        if not context.resume.certifications:
             if score_map.get("certificates_score", 0) > 0:
                score_map["certificates_score"] = 0
                notes.append("[Guardrail] Certificates score zeroed: No certifications found.")
        return score_map, notes

# --- NEW: Generic Evidence Rule (Dataset-driven) ---

class GenericEvidenceRule:
    name = "Generic Evidence Lookup"
    
    def __init__(self):
        self.rules = self._load_rules()
        
    def _load_rules(self) -> List[Dict[str, Any]]:
        try:
            # Locate config/evidence_rules.json relative to app/
            base_dir = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base_dir, "config", "evidence_rules.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load evidence rules: {e}")
        return []

    def _evaluate_condition(self, condition: Dict[str, Any], context: GuardrailContext) -> bool:
        field_path = condition.get("field", "")
        operator = condition.get("operator", "")
        
        # Resolve value (simplistic resolution)
        value = None
        if field_path == "resume.experience":
            value = context.resume.experience
        elif field_path == "resume.summary":
            value = context.resume.summary
        elif field_path == "resume.skills":
            value = context.resume.skills
        
        if value is None: 
            return False
            
        if operator == "empty":
            return not value
        
        if operator == "contains_keyword_ratio":
            keyword = condition.get("keyword", "").lower()
            threshold = condition.get("threshold", 0.0)
            if isinstance(value, list) and value: # List of dicts (experience)
                matches = 0
                total = len(value)
                for item in value:
                    # check role/title
                    role = str(item.get("role", "")).lower()
                    if keyword in role:
                        matches += 1
                return (matches / total) >= threshold
            return False

        if operator == "avg_duration_months_lt":
            limit = condition.get("value", 0)
            if isinstance(value, list) and value:
                total_months = 0
                count = 0
                for item in value:
                    dur = calculate_duration(item.get("start_date"), item.get("end_date")) # years
                    total_months += (dur * 12)
                    count += 1
                if count > 0:
                    avg = total_months / count
                    return avg < limit
            return False

        return False

    def apply(self, score_map: Dict[str, int], context: GuardrailContext) -> Tuple[Dict[str, int], List[str]]:
        notes = []
        for rule in self.rules:
            try:
                if self._evaluate_condition(rule.get("condition", {}), context):
                    action = rule.get("action", {})
                    target = action.get("target")
                    op = action.get("operation")
                    val = action.get("value")
                    
                    current_score = score_map.get(target, 0)
                    new_score = current_score
                    
                    if op == "cap":
                        new_score = min(current_score, val)
                    elif op == "multiply":
                        new_score = int(current_score * val)
                    elif op == "set":
                        new_score = val
                        
                    if new_score != current_score:
                        score_map[target] = new_score
                        notes.append(f"[Guardrail: {rule.get('id')}] {target} adjusted ({op} {val}).")
            except Exception as e:
                # Fail open to avoid crashing pipeline
                print(f"⚠️ Error evaluating rule {rule.get('id', 'unknown')}: {e}")
                
        return score_map, notes

# Rule Registry
ACTIVE_GUARDRAILS: List[GuardrailRule] = [
    SkillsEvidenceRule(),
    ExperienceEvidenceRule(),
    ProjectsEvidenceRule(),
    CertificationsEvidenceRule(),
    GenericEvidenceRule(),
]

def apply_guardrails(score_map: Dict[str, int], context: GuardrailContext) -> Dict[str, int]:
    """
    Apply all active guardrails to the score map.
    Modifies score map in place and appends notes if changes occur.
    """
    # Defensive copy not strictly needed if we want in-place mod, but cleaner logic
    # We will modify input dict directly as per requirement (in the chain)
    
    all_notes = []
    
    for rule in ACTIVE_GUARDRAILS:
        score_map, notes = rule.apply(score_map, context)
        all_notes.extend(notes)
        
    if all_notes:
        existing_notes = score_map.get("notes", "")
        # Append guardrail notes
        score_map["notes"] = (existing_notes + " " + " ".join(all_notes))[:500] # Cap length
        
    return score_map
