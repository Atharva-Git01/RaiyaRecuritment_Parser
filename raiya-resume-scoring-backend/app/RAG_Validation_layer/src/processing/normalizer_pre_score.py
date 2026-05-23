# app/normalizer_pre_score.py
from copy import deepcopy
from difflib import SequenceMatcher

# === 🔹 TECHNOLOGY & TOOL ALIASES ===
tech_aliases = {
    # Frontend
    "react native": "ReactJS",
    "react": "ReactJS",
    "react.js": "ReactJS",
    "typescript": "TypeScript",
    "type script": "TypeScript",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "html": "HTML5",
    "html/css": "HTML5",
    "css": "CSS3",
    "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    # Backend
    "python": "Python",
    "api": "REST API",
    "node": "Node.js",
    "express": "Express.js",
    "php": "Laravel",
    "django": "Django",
    "flask": "Flask",
    "spring boot": "Spring",
    # Databases
    "mysql": "MySQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    # Cloud / DevOps
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "linux": "Linux",
    "rest": "REST API",
    "graphql": "GraphQL",
    "firebase": "Firebase",
    # ML / AI
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "opencv": "OpenCV",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit": "Scikit-Learn",
    # Tools / IDEs
    "git": "GitHub",
    "git hub": "GitHub",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "vscode": "VS Code",
    "visual studio": "VS Code",
    "postman": "Postman",
    "jira": "Jira",
    "slack": "Slack",
    "eclipse": "Eclipse",
    "pycharm": "PyCharm",
    "intellij": "IntelliJ IDEA",
}

# === 🔹 SKILL / CONCEPTUAL ALIASES ===
skill_aliases = {
    "problem-solving": "Problem Solving",
    "problem solving": "Problem Solving",
    "algorithms": "Algorithms",
    "data structure": "Data Structures",
    "oop": "OOP",
    "object oriented": "OOP",
    "networking": "Networking",
    "cybersecurity": "Cyber Security",
    "cloud": "Cloud Computing",
    "devops": "DevOps",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "artificial intelligence": "AI",
    "ai": "AI",
    "database": "Database Management",
    "sql": "Database Management",
    "version control": "Version Control",
    "api": "API Development",
    "leadership": "Leadership",
    "team": "Teamwork",
    "management": "Project Management",
    "testing": "Testing & Debugging",
    "debugging": "Testing & Debugging",
}

# === 🔹 EDUCATION ALIASES ===
edu_aliases = {
    "b.e": "Bachelor's Degree in Engineering",
    "be": "Bachelor's Degree in Engineering",
    "btech": "Bachelor's Degree in Engineering",
    "bachelor": "Bachelor's Degree in Engineering",
    "mtech": "Master's Degree in Engineering",
    "m.e": "Master's Degree in Engineering",
    "master": "Master's Degree in Engineering",
}


def _to_list(value):
    if isinstance(value, list):
        return value
    if value in (None, "", {}, ()):
        return []
    if isinstance(value, (set, tuple)):
        return list(value)
    return [value]


def normalize_for_scoring(parsed_data: dict) -> dict:
    """
    Normalizes parsed resume JSON before JD scoring.
    Aligns skills, technologies, tools, and education fields
    to match the vocabulary and criteria defined in the JD.
    """

    # Work on a deepcopy to avoid mutating caller payload
    safe_data = deepcopy(parsed_data) if isinstance(parsed_data, dict) else {}

    # Ensure critical list fields always exist
    list_fields = ["skills", "education", "experience", "projects", "certificates"]
    for field in list_fields:
        safe_data[field] = _to_list(safe_data.get(field, []))

    # === 🔹 COMBINE ALIASES FOR SKILLS ===
    # EXCLUDE edu_aliases from skills to prevent degrees from appearing as skills
    skill_tech_aliases = {**tech_aliases, **skill_aliases}

    # === 🔹 Normalization Function (Generic) ===
    def match_alias(word, alias_map):
        word_l = word.lower().strip()
        for alias, canonical in alias_map.items():
            if alias in word_l:
                return canonical
        # Fallback fuzzy match
        for alias, canonical in alias_map.items():
            if SequenceMatcher(None, alias, word_l).ratio() > 0.8:
                return canonical
        return word.title()

    # === 🔹 Normalize Skills & Techs ===
    raw_skills = safe_data.get("skills", [])
    normalized_skills = set()
    for skill in raw_skills:
        if skill is None:
            continue
        # Use only tech/skill aliases
        normalized_skills.add(match_alias(str(skill), skill_tech_aliases))

    # === 🔹 Normalize Education ===
    clean_education = []
    for edu in safe_data.get("education", []):
        if isinstance(edu, dict):
            # Use edu_aliases specifically for degrees
            degree = match_alias(str(edu.get("degree", "")), edu_aliases)
            edu_copy = deepcopy(edu)
            edu_copy["degree"] = degree
            clean_education.append(edu_copy)
        elif edu:
            clean_education.append({
                "degree": match_alias(str(edu), edu_aliases), 
                "institution": "", 
                "year": ""
            })

    safe_data["education"] = clean_education

    # === 🔹 Merge skills & technologies ===
    safe_data["skills"] = sorted({s for s in (normalized_skills or []) if s})

    return safe_data
