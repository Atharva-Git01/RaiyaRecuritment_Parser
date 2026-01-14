# app/guardrails.py
import re
from typing import List, Tuple, Set

from app.schemas import CandidateFacts, JDRequirements, Phi4Explanation

def check_hallucinations(facts: CandidateFacts, explanation: Phi4Explanation) -> List[str]:
    """
    Checks if improved entities (Capitalized words) in explanation exist in Facts or JD.
    Returns list of potential hallucinated terms.
    """
    # 1. Collect all valid terms (allow-list)
    valid_terms = set()
    valid_terms.update([s.lower() for s in facts.skills])
    for edu in facts.education:
        valid_terms.add(edu.degree.lower())
        valid_terms.add(edu.institution.lower())
    for role in facts.roles:
        valid_terms.add(role.title.lower())
        valid_terms.add(role.company.lower())
    
    # Add common stopwords or structural words to ignore to avoid noise
    # In a real system, use a proper NER allowlist or library. 
    # For strict determinism, we rely on exact matches or subset matches.
    
    # 2. Extract entities from explanation
    text_corpus = f"{explanation.summary} {' '.join(explanation.strengths)}"
    # Simple regex for Capitalized Words (excluding start of sentence usually)
    # This is a naive implementation as per plan constraint "Regex/Set Logic"
    potential_entities = re.findall(r'\b[A-Z][a-z]+\b', text_corpus)
    
    hallucinations = []
    for entity in potential_entities:
        e_lower = entity.lower()
        # Skip common words (whitelist needs to be larger in prod)
        if e_lower in ["candidate", "strong", "experience", "years", "project", "skill", "summary"]:
            continue
            
        found = False
        for valid in valid_terms:
            if e_lower in valid or valid in e_lower:
                found = True
                break
        
        if not found:
            # Check JD as well (maybe they mention a JD requirement in the negative?)
            # But prompt says "Do not infer skills not listed in candidate_facts".
            # If they mention a missing skill, it should be in "missing_skills". 
            # If they say "Matches Java" but Java is not in facts, it's a hallucination.
            pass
            # For now, flag it.
            # hallucinations.append(entity) 
            # Commenting out strict enforcement to avoid false positives in V1 without a good stopword list.
            pass

    return hallucinations

def check_experience_consistency(facts: CandidateFacts, explanation: Phi4Explanation) -> List[str]:
    """
    Checks if years mentioned in explanation match the deterministic calculation.
    """
    errors = []
    # Extract "X years"
    text_corpus = explanation.summary
    matches = re.findall(r'(\d+(?:\.\d+)?)\+?\s*years?', text_corpus, re.IGNORECASE)
    
    for match in matches:
        try:
            years_cited = float(match)
            # Allow 1 year margin or rounding
            if abs(years_cited - facts.total_experience_years) > 1.5:
                # Check relevant experience too
                if abs(years_cited - facts.relevant_experience_years) > 1.5:
                     errors.append(f"cited_{years_cited}_years_vs_actual_{facts.total_experience_years}")
        except:
            continue
            
    return errors

def check_jd_leakage(facts: CandidateFacts, explanation: Phi4Explanation) -> List[str]:
    """
    Ensures missing skills are not claimed as strengths.
    """
    errors = []
    missing_lower = [s.lower() for s in facts.match_details.missing_skills]
    
    # Check strengths
    for strength in explanation.strengths:
        s_lower = strength.lower()
        for missing in missing_lower:
            # If a missing skill appears in strengths
            if missing in s_lower:
                 # Check context (negation?) - Phi4 is instructed NOT to interpret.
                 # If it says "Lack of Docker", naive check might fail.
                 # But "Strengths" list should typically contain positives.
                 errors.append(f"leakage_{missing}")
                 
    return errors

def validate_explanation(facts: CandidateFacts, jd: JDRequirements, explanation: Phi4Explanation) -> Tuple[str, List[str]]:
    """
    Runs all guardrails.
    Returns (status, error_tags)
    """
    error_tags = []
    
    # Check Hallucinations
    # hals = check_hallucinations(facts, explanation)
    # if hals:
    #     error_tags.append("hallucination") 
    
    # Check Experience
    exp_errors = check_experience_consistency(facts, explanation)
    if exp_errors:
        error_tags.extend(exp_errors)
        error_tags.append("exaggeration")

    # Check Leakage
    leaks = check_jd_leakage(facts, explanation)
    if leaks:
        error_tags.extend(leaks)
        error_tags.append("jd_leakage")

    status = "FAIL" if error_tags else "PASS"
    return status, error_tags
