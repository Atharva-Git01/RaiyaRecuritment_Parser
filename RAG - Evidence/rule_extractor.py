# Product/RAG - Evidence/rule_extractor.py
import re
from typing import Dict, Any, List, Set

class RuleExtractor:
    """Extracts explicit constraints and rules from Job Descriptions."""
    
    def __init__(self, jd_text: str):
        self.jd_text = jd_text if jd_text else ""
        
    def extract_hard_rules(self) -> List[str]:
        """Extracts mandatory requirements specified in the JD."""
        rules = []
        lines = self.jd_text.split('\n')
        
        mandatory_keywords = ["must", "required", "mandatory", "essential", "minimum"]
        
        for line in lines:
            lower_line = line.lower()
            if any(kw in lower_line for kw in mandatory_keywords) and len(line) > 10:
                rules.append(line.strip())
                
        return rules

    def extract_soft_rules(self) -> List[str]:
        """Extracts preferred or nice-to-have requirements."""
        rules = []
        lines = self.jd_text.split('\n')
        
        soft_keywords = ["preferred", "plus", "nice to have", "advantage", "bonus"]
        
        for line in lines:
            lower_line = line.lower()
            if any(kw in lower_line for kw in soft_keywords) and len(line) > 10:
                rules.append(line.strip())
                
        return rules

    def extract_required_tools(self) -> Set[str]:
        """Extracts specific tools or technologies mentioned."""
        common_tools = {
            "python", "java", "c++", "javascript", "react", "node", "aws", 
            "azure", "docker", "kubernetes", "sql", "git", "linux"
        }
        
        found_tools = set()
        words = re.findall(r'\b[a-zA-Z\+]+\b', self.jd_text.lower())
        
        for tool in common_tools:
            if tool in words:
                found_tools.add(tool)
                
        return found_tools
