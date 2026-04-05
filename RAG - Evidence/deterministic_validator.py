# Product/RAG - Evidence/deterministic_validator.py
import re
from typing import Dict, Any, List
# We use try/except block just in case sentence_transformers causes CI/CD issues
try:
    from sentence_transformers import SentenceTransformer, util
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

from rule_extractor import RuleExtractor
from normalizer_pre_score import normalize_pre_score

class DeterministicValidator:
    """
    Evaluates AI Score JSON payload against deterministic evidence from the parsed resume.
    Hunts for Hallucinations and semantic rule adherence.
    """
    
    def __init__(self, jd_data: Dict[str, Any]):
        self.jd_data = jd_data
        jd_text = jd_data.get("job_description", "")
        self.extractor = RuleExtractor(jd_text)
        
        # We attempt to load a fast, lightweight model for local semantic embeddings
        if ST_AVAILABLE:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
        self.hard_rules = self.extractor.extract_hard_rules()
        self.soft_rules = self.extractor.extract_soft_rules()
        self.required_tools = self.extractor.extract_required_tools()

    def _fallback_keyword_match(self, rule: str, text_list: List[str]) -> bool:
        """Fallback to basic keyword matching if sentence_transformers isn't available."""
        rule_lower = rule.lower()
        for text in text_list:
            if any(word in text.lower() for word in rule_lower.split()):
                return True
        return False
        
    def _semantic_match(self, rule: str, text_list: List[str], threshold: float = 0.6) -> bool:
        if not ST_AVAILABLE:
            return self._fallback_keyword_match(rule, text_list)
            
        if not text_list:
            return False
            
        rule_emb = self.model.encode(rule, convert_to_tensor=True)
        text_embs = self.model.encode(text_list, convert_to_tensor=True)
        
        cosine_scores = util.cos_sim(rule_emb, text_embs)[0]
        max_score = cosine_scores.max().item()
        
        return max_score >= threshold

    def _detect_hallucinations(self, ai_scores: Dict[str, Any], raw_text: str, norm_resume: Dict[str, Any]) -> List[str]:
        """Checks if the AI claims something exists that isn't statically present."""
        hallucinations = []
        raw_text_lower = str(raw_text).lower()
        
        # Check skill claims
        ai_skills = ai_scores.get("skills_assessed", [])
        if isinstance(ai_skills, dict):
            # Sometimes AI returns dict mapping skill to score
            ai_skills = list(ai_skills.keys())
            
        static_skills = [s.lower() for s in norm_resume.get("skills", [])]
        
        for skill in ai_skills:
            skill_lower = str(skill).lower()
            if skill_lower not in static_skills and skill_lower not in raw_text_lower:
                hallucinations.append(f"AI claimed skill '{skill}' but it was not found in parsed payload or raw text.")

        return hallucinations

    def validate(self, resume_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes deterministic rules against the finalized AI payload.
        resume_payload should contain 'raw_text', 'parsed_json', and the AI's 'ai_score'.
        """
        ai_score = resume_payload.get("ai_score", {})
        raw_text = resume_payload.get("raw_text", "")
        parsed_json = resume_payload.get("parsed_json", {})
        
        norm_resume = normalize_pre_score(parsed_json)
        
        # Flatten all resume content for semantic search
        all_resume_text = (
            norm_resume.get("skills", []) +
            norm_resume.get("experience", []) +
            norm_resume.get("education", [])
        )
        all_resume_text.append(raw_text) # Append raw text as final fallback
        
        report = {
            "is_valid": True,
            "hallucinations": [],
            "rule_adherence": {
                "hard_rules_met": 0,
                "total_hard_rules": len(self.hard_rules),
                "soft_rules_met": 0,
                "total_soft_rules": len(self.soft_rules),
                "required_tools_found": []
            },
            "missing_critical_requirements": []
        }
        
        # 1. Detect Hallucinations
        hallucs = self._detect_hallucinations(ai_score, raw_text, norm_resume)
        if hallucs:
            report["is_valid"] = False
            report["hallucinations"] = hallucs

        # 2. Check Hard Rules
        for rule in self.hard_rules:
            if self._semantic_match(rule, all_resume_text, 0.65):
                report["rule_adherence"]["hard_rules_met"] += 1
            else:
                report["missing_critical_requirements"].append(rule)
                
        # 3. Check Soft Rules
        for rule in self.soft_rules:
            if self._semantic_match(rule, all_resume_text, 0.5): # Lower threshold for soft rules
                report["rule_adherence"]["soft_rules_met"] += 1

        # 4. Check Tools
        found_tools = []
        raw_text_lower = raw_text.lower()
        for tool in self.required_tools:
            if tool in raw_text_lower:
                found_tools.append(tool)
        report["rule_adherence"]["required_tools_found"] = found_tools

        # If zero hard rules met but JD had hard rules, invalidate
        if self.hard_rules and report["rule_adherence"]["hard_rules_met"] == 0:
            report["is_valid"] = False
            
        return report
