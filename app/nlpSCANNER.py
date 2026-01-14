import contextlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

import pandas as pd
import pdfplumber
from docx import Document
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

model = SentenceTransformer("all-MiniLM-L6-v2")  # lightweight & fast

# Load Job Description JSON
job_file = os.path.join(os.path.dirname(__file__), "job_description.json")
with open(job_file, "r", encoding="utf-8") as f:
    job = json.load(f)

# -------------------------------
# Load Dataset JSON (for normalization/fuzzy matching)
# -------------------------------
dataset_file = os.path.join(os.path.dirname(__file__), "merged_fixed_dataset.json")
with open(dataset_file, "r", encoding="utf-8") as f:
    dataset = json.load(f)

# -------------------------------
# Technology, tools aliases
# -------------------------------
tech_aliases = {
    # Languages
    "python": "Python",
    "py": "Python",
    "java": "Java",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C++",
    "csharp": "C++",
    "golang": "Go",
    "go": "Go",
    "ruby": "Ruby",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "r": "R",
    "perl": "Perl",
    "dart": "Dart",
    "sql": "SQL",
    "pl/sql": "PL/SQL",
    "html": "HTML5",
    "css": "CSS3",
    "sass": "Sass",
    "scss": "Sass",
    "less": "Less",
    "xml": "XML",
    "json": "JSON",
    "yaml": "YAML",
    # Frontend frameworks
    "react": "ReactJS",
    "reactjs": "ReactJS",
    "angular": "Angular",
    "angularjs": "Angular",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "svelte": "Svelte",
    "ember": "Ember.js",
    "backbone": "Backbone.js",
    "jquery": "jQuery",
    "bootstrap": "Bootstrap",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    # Backend frameworks
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "express": "Express.js",
    "laravel": "Laravel",
    "symfony": "Symfony",
    # Data / ML
    "numpy": "NumPy",
    "pandas": "Pandas",
    "sklearn": "Scikit-Learn",
    "scikit-learn": "Scikit-Learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "opencv": "OpenCV",
    "matplotlib": "Matplotlib",
    "seaborn": "Seaborn",
    "plotly": "Plotly",
    # Big Data / Spark
    "spark": "Apache Spark",
    "pyspark": "PySpark",
    "hadoop": "Apache Hadoop",
    "hive": "Hive",
    "pig": "Apache Pig",
    "kafka": "Apache Kafka",
    "flink": "Apache Flink",
    "databricks": "Databricks",
}

tool_aliases = {
    "git": "Git",
    "gitlab": "GitLab",
    "github": "GitHub",
    "jira": "Jira",
    "bitbucket": "Bitbucket",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "jenkins": "Jenkins",
    "circleci": "CircleCI",
    "travis": "Travis CI",
    "ansible": "Ansible",
    "terraform": "Terraform",
    "chef": "Chef",
    "puppet": "Puppet",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "tableau": "Tableau",
    "power bi": "Power BI",
}

# -------------------------------
# Qualification mapping
# -------------------------------
qualification_mapping = {
    "bachelor": "Bachelor's Degree In Engineering",
    "b.tech": "Bachelor's Degree In Engineering",
    "b.e": "Bachelor's Degree In Engineering",
    "bsc": "BSC",
    "bca": "BCA",
    "bachelor of engineering": "Bachelor's Degree In Engineering",
    "master": "Master's Degree In Engineering",
    "m.tech": "Master's Degree In Engineering",
    "m.e": "Master's Degree In Engineering",
    "msc": "MSC",
    "mca": "MCA",
    "m.sc": "M.SC",
    "master of engineering": "Master's Degree In Engineering",
    "bachelor of science": "Bachelor's Of Science",
    "bachelor of computer engineering": "Bachelor's Degree In Engineering",
    "master of computer engineering": "Master's Degree In Engineering",
}

# Create normalization lists from dict keys
tech_normalization = [item["canonical"] for item in dataset.get("technologies", [])]
skill_normalization = [item["canonical"] for item in dataset.get("skills", [])]
tools_normalization = [item["canonical"] for item in dataset.get("tools", [])]


# Suppress stderr (useful for pdfplumber warnings)
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as fnull:
        old_stderr = sys.stderr
        sys.stderr = fnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


# Extract text from PDF
def extract_pdf_text(path):
    text = ""
    with suppress_stderr():
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    return text


# Extract text from DOCX
def extract_docx_text(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs])


# General resume extractor
def extract_resume_text(path):
    if path.lower().endswith(".pdf"):
        return extract_pdf_text(path)
    elif path.lower().endswith(".docx"):
        return extract_docx_text(path)
    else:
        return ""


# -------------------------------
# Text normalization
# -------------------------------
def normalize_text(text):
    """
    Lowercase, strip spaces, remove special characters.
    """
    return re.sub(r"[\s\-\+\./]", "", text.lower().strip())


# -------------------------------
# Generate embeddings for job description lists
# -------------------------------
def generate_jd_embeddings(job_description, model):
    """
    Precompute embeddings for job description lists.

    Args:
        job_description (dict): keys = 'technologies', 'skills', 'tools'
        model: SentenceTransformer model instance

    Returns:
        dict of embeddings: {'technologies': tensor, 'skills': tensor, 'tools': tensor}
    """
    jd_embeddings = {}
    for category in ["technologies", "skills", "tools"]:
        items = job_description.get(category, [])
        normalized_items = [i.lower() for i in items]
        embeddings = model.encode(normalized_items, convert_to_tensor=True)
        jd_embeddings[category] = {"items": items, "embeddings": embeddings}
    return jd_embeddings


# -------------------------------
# Precompute embeddings for JD lists
# -------------------------------
jd_embeddings = generate_jd_embeddings(job, model)


def semantic_match_candidates(candidates, candidates_embeddings, text, threshold=0.55):
    """
    Semantic match using precomputed embeddings (chunked for long text).
    """
    if not candidates or not text.strip():
        return []

    # Split text into lines or sentences
    text_chunks = re.split(r"\n|\.|\-|,", text.lower())
    text_chunks = [t.strip() for t in text_chunks if t.strip()]

    matched = set()
    for chunk in text_chunks:
        chunk_embedding = model.encode([chunk], convert_to_tensor=True)
        cosine_scores = util.cos_sim(chunk_embedding, candidates_embeddings)[0]
        for i, score in enumerate(cosine_scores):
            if score >= threshold:
                matched.add(candidates[i])

    return list(matched)


def extract_tech_tool_experience(text, candidates):
    """
    Extracts years of experience per technology or tool from resume text.

    Args:
        text (str): Resume text
        candidates (list): List of technologies or tools

    Returns:
        dict: {candidate_name: years_of_experience}
    """
    text_lower = text.lower()
    exp_dict = defaultdict(float)

    # -------------------------------
    # Regex: Explicit experience like '3 years in Python'
    # -------------------------------
    for candidate in candidates:
        pattern = rf"(\d+(?:\.\d+)?)\s*\+?\s*(?:yrs|years|year).*?\b{re.escape(candidate.lower())}\b"
        matches = re.findall(pattern, text_lower)
        if matches:
            exp_dict[candidate] = max([float(m) for m in matches])

    # -------------------------------
    # Regex: Job blocks with dates (e.g., "Software Engineer, Google, Jan 2020 - Mar 2022")
    # -------------------------------
    job_blocks = re.findall(
        r"(?P<title>.+?)\s*,\s*(?P<company>.+?)\s*,\s*"
        r"(?P<start>[A-Za-z]{3,}\s+\d{4})\s*-\s*"
        r"(?P<end>[A-Za-z]{3,}\s+\d{4}|present)"
        r"(?P<desc>.*?)(?=(?:\n[A-Z][^,\n]+,\s*[A-Z][^,\n]+,\s*[A-Za-z]{3,}\s+\d{4})|$)",
        text,
        flags=re.S | re.I,
    )

    for title, company, start, end, desc in job_blocks:
        try:
            start_dt = datetime.strptime(start[:3] + " " + start.split()[1], "%b %Y")
            end_dt = (
                datetime.now()
                if end.lower() == "present"
                else datetime.strptime(end[:3] + " " + end.split()[1], "%b %Y")
            )
            months = (end_dt.year - start_dt.year) * 12 + (
                end_dt.month - start_dt.month
            )
            years = round(months / 12, 1)
        except:
            years = 0

        job_text = f"{title} {company} {desc}".lower()
        for candidate in candidates:
            # Semantic match: simple fuzzy check for now
            if candidate.lower() in job_text:
                exp_dict[candidate] = max(exp_dict.get(candidate, 0), years)

    return dict(exp_dict)


def parse_resume_semantic(text, job, jd_embeddings):
    """
    Parse a resume using semantic + regex extraction.

    Returns:
        dict: Parsed resume including experience, qualifications, tech/tools/skills, position
    """
    text_lower = text.lower()

    # -------------------------------
    # Overall Experience
    # -------------------------------
    exp_years = 0
    matches = re.findall(
        r"(?:over|more than|~)?\s*(\d+)\s*\+?\s*(?:years|yrs|year)", text_lower
    )
    if matches:
        exp_years = max([int(m) for m in matches])

    # -------------------------------
    # Qualification
    # -------------------------------
    qualification = "Other"
    for key, val in qualification_mapping.items():
        if key in text_lower:
            qualification = val
            break
    # -------------------------------
    # Technologies, Tools, Skills (normalized + semantic fuzzy)
    # -------------------------------
    tech_list = semantic_match_candidates(
        jd_embeddings["technologies"]["items"],
        jd_embeddings["technologies"]["embeddings"],
        text_lower,
        threshold=0.55,
    )

    skill_list = semantic_match_candidates(
        jd_embeddings["skills"]["items"],
        jd_embeddings["skills"]["embeddings"],
        text_lower,
        threshold=0.55,
    )

    tool_list = semantic_match_candidates(
        jd_embeddings["tools"]["items"],
        jd_embeddings["tools"]["embeddings"],
        text_lower,
        threshold=0.55,
    )

    # Deduplicate
    skill_list = [s for s in skill_list if s not in tech_list]
    tool_list = [t for t in tool_list if t not in tech_list and t not in skill_list]

    # -------------------------------
    # Extract experience per technology/tool
    # -------------------------------
    tech_exp = extract_tech_tool_experience(text, tech_list)
    tool_exp = extract_tech_tool_experience(text, tool_list)

    # -------------------------------
    # Prepare display versions
    # -------------------------------
    tech_display = [
        f"{tech} ({tech_exp.get(tech,0)} yrs)" if tech_exp.get(tech, 0) > 0 else tech
        for tech in tech_list
    ]
    tool_display = [
        f"{tool} ({tool_exp.get(tool,0)} yrs)" if tool_exp.get(tool, 0) > 0 else tool
        for tool in tool_list
    ]

    # -------------------------------
    # Position detection
    # -------------------------------
    position = "Individual Contributor"
    if re.search(r"\blead\b|\bmanager\b", text_lower):
        position = "Team Lead (Preferred)"
    elif re.search(r"\bintern\b|\btrainee\b", text_lower):
        position = "Intern"
    elif re.search(r"\bsenior\b|\bsr\b", text_lower):
        position = "Senior Developer"

    # -------------------------------
    # Final parsed dict
    # -------------------------------
    parsed_resume = {
        "experience": exp_years,
        "qualification": qualification,
        "technologies": tech_display,
        "skills": skill_list,
        "tools": tool_display,
        "tech_stack": sorted(set(tech_list + skill_list + tool_list)),
        "position": position,
    }

    return parsed_resume


def score_resume(parsed_resume, job):
    """
    Calculate the resume score based on job description criteria.

    Args:
        parsed_resume (dict): Output from parse_resume_semantic
        job (dict): Job description with scoring criteria

    Returns:
        int: Total score (0-100)
    """
    total_score = 0

    # -------------------------------
    # 1. Experience scoring
    # -------------------------------
    exp_years = parsed_resume["experience"]
    for crit, pts in job["scoring"]["experience"]["criteria"].items():
        if ">=" in crit and exp_years >= int(re.findall(r"\d+", crit)[0]):
            total_score += pts
            break
        elif "-" in crit:
            low, high = map(int, re.findall(r"\d+", crit))
            if low <= exp_years <= high:
                total_score += pts
                break
        elif "<" in crit and exp_years < int(re.findall(r"\d+", crit)[0]):
            total_score += pts
            break

    # -------------------------------
    # 2. Qualification scoring
    # -------------------------------
    total_score += job["scoring"]["qualification"]["criteria"].get(
        parsed_resume["qualification"], 0
    )

    # -------------------------------
    # 3. Technologies scoring
    # -------------------------------
    for tech in parsed_resume["technologies"]:
        # remove "(X yrs)" if present
        tech_name = re.sub(r"\s*\(\d+\.?\d*\s*yrs\)", "", tech)
        total_score += job["scoring"]["technologies"]["criteria"].get(tech_name, 0)

    # -------------------------------
    # 4. Skills scoring
    # -------------------------------
    for skill in parsed_resume["skills"]:
        total_score += job["scoring"]["skills"]["criteria"].get(skill, 0)

    # -------------------------------
    # 5. Tools scoring
    # -------------------------------
    for tool in parsed_resume["tools"]:
        tool_name = re.sub(r"\s*\(\d+\.?\d*\s*yrs\)", "", tool)
        total_score += (
            job.get("scoring", {})
            .get("tools", {})
            .get("criteria", {})
            .get(tool_name, 0)
        )

    # -------------------------------
    # 6. Position scoring
    # -------------------------------
    total_score += job["scoring"]["position"]["criteria"].get(
        parsed_resume["position"], 0
    )

    # -------------------------------
    # Cap score at 100
    # -------------------------------
    return min(total_score, 100)


from tqdm import tqdm


def process_resumes_folder(resume_folder, job, output_file="Resume_Analysis.xlsx"):
    """
    Process all resumes in a folder with terminal progress bar: parse, score, export to Excel.
    """
    results = []
    files = [
        f for f in os.listdir(resume_folder) if f.lower().endswith((".pdf", ".docx"))
    ]

    # Terminal loading bar
    for filename in tqdm(
        files, desc="Processing Resumes", unit="resume", ncols=100, colour="green"
    ):
        path = os.path.join(resume_folder, filename)

        # Extract text
        text = extract_resume_text(path)
        if not text.strip():
            continue

        # Parse using semantic embeddings
        parsed_resume = parse_resume_semantic(text, job, jd_embeddings)
        parsed_resume["filename"] = filename

        # Score resume
        parsed_resume["score"] = score_resume(parsed_resume, job)

        # Convert lists to comma-separated strings
        for key in ["technologies", "skills", "tools", "tech_stack"]:
            parsed_resume[key] = (
                ", ".join(parsed_resume[key]) if parsed_resume[key] else ""
            )

        results.append(parsed_resume)

    # Sort by score descending
    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)

    # -------------------------------
    # Save to Excel with adjusted column widths
    # -------------------------------
    df = pd.DataFrame(results_sorted).astype(str)

    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        workbook = writer.book
        worksheet = writer.sheets["Results"]

        # Auto-adjust column widths
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            max_len = min(max_len, 50)
            cell_format = workbook.add_format(
                {
                    "text_wrap": True,
                    "align": "center",
                    "valign": "vcenter",
                    "font_name": "Calibri",
                    "font_size": 11,
                }
            )
            worksheet.set_column(idx, idx, max_len, cell_format)

    print(f"\n✅ Resume analysis complete! Saved to '{output_file}'")


# -------------------------------
# Run the script
# -------------------------------
if __name__ == "__main__":
    # Path to folder containing resumes
    resume_folder = (
        r"C:\Users\Janak Gujarati\Desktop\Reaper\work_101\My_Resume_Checker\Resumes"
    )

    # Output Excel file
    output_file = "NLP_Analysis.xlsx"

    # Process all resumes
    process_resumes_folder(resume_folder, job, output_file)
