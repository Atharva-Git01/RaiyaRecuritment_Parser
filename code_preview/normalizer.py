# normalizer.py
import json
import os
import re


def clean_text(raw_text: str) -> str:
    """
    Remove extra spaces, line breaks, and non-ASCII symbols.
    """
    text = raw_text
    # collapse multiple newlines/spaces
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r" +", " ", text)
    # join broken words like "devel-\nopment"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # 🔥 Fix merged alphanumeric tokens (critical for salary extraction)
    # Example: "current ctc6.5 lpa" → "current ctc 6.5 lpa"
    text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)

    # remove strange symbols
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()


def normalize_sections(clean_text: str) -> str:
    """
    Insert Markdown-style headers for main resume sections.
    """
    text = clean_text
    section_patterns = {
        "OBJECTIVE": "## Objective",
        "SKILLS": "## Skills",
        "EXPERIENCE": "## Experience",
        "EDUCATION": "## Education",
        "PROJECTS": "## Projects",
        "CERTIFICATIONS": "## Certifications",
        "ACHIEVEMENTS": "## Achievements",
        "CONTACT": "## Contact",
    }

    for pattern, replacement in section_patterns.items():
        text = re.sub(
            rf"\b{pattern}\b", f"\n\n{replacement}\n", text, flags=re.IGNORECASE
        )

    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def normalize_resume_text(raw_text: str, tmp_dir: str) -> str:
    """
    Run both cleaning and section normalization,
    and extract CGPA/Percentage info if available.
    """
    cleaned = clean_text(raw_text)
    normalized = normalize_sections(cleaned)

    # 🧠 Extract CGPA or percentage scores
    scores = extract_academic_scores(normalized)
    if scores:
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, "academic_scores.json")

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=4)

        print(f"🎓 Found academic scores → saved to {tmp_path}")

    # 💰 Extract salary info
    salary = extract_salary(normalized)
    if salary and (salary.get("current_ctc_lpa") or salary.get("expected_ctc_lpa")):
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_salary = os.path.join(tmp_dir, "salary.json")

        with open(tmp_salary, "w", encoding="utf-8") as f:
            json.dump(salary, f, indent=4)

        print(f"💰 Found salary info → saved to {tmp_salary}")

    return normalized


def extract_academic_scores(text: str) -> dict:
    """
    Extract CGPA or percentage values from the resume text.
    Returns a dictionary with found values, if any.
    """
    cgpa_match = re.search(r"(CGPA|GPA)\s*[:\-]?\s*(\d+(\.\d+)?)", text, re.IGNORECASE)
    perc_match = re.search(
        r"(Percentage|Percent)\s*[:\-]?\s*(\d+(\.\d+)?)", text, re.IGNORECASE
    )

    result = {}
    if cgpa_match:
        result["cgpa"] = float(cgpa_match.group(2))
    if perc_match:
        result["percentage"] = float(perc_match.group(2))
    return result


def extract_salary(text: str) -> dict:
    """
    Extract salary mentions like:
    - Current CTC: 8 LPA
    - Expected salary 12 LPA
    - ₹6,00,000 p.a.
    - 80k per month
    Returns normalized salary in LPA (Lakhs Per Annum).
    """
    t = text.replace(",", " ").replace("₹", " ").lower()

    patterns = [
        r"(current\s+ctc|current\s+salary)\s*[:\-]?\s*(\d+(\.\d+)?)\s*(lpa|lakhs|lakh|pa|p\.a\.|per annum)?",
        r"(expected\s+ctc|expected\s+salary|desired\s+ctc)\s*[:\-]?\s*(\d+(\.\d+)?)\s*(lpa|lakhs|lakh|pa|p\.a\.|per annum)?",
        r"(\d+(\.\d+)?)\s*(lpa|lakhs|lakh)\b",
        r"(\d+(\.\d+)?)\s*k\s*(per\s*month|monthly|pm)",
        r"ctc\s*[:\-]?\s*(\d+(\.\d+)?)\s*(lpa|lakhs|lakh|pa|per annum)?",
    ]

    salary = {"current_ctc_lpa": None, "expected_ctc_lpa": None}

    for patt in patterns:
        for m in re.finditer(patt, t):
            full = m.group(0)
            num = float(re.search(r"\d+(\.\d+)?", full).group())

            # Monthly salary → convert to LPA
            if "per month" in full or "monthly" in full or "pm" in full:
                annual = num * 12 * 1000
                lpa = round(annual / 100000, 2)

            # '80k' or '500k per annum'
            elif "k" in full and not (
                "per month" in full or "monthly" in full or "pm" in full
            ):
                annual_inr = num * 1000
                lpa = round(annual_inr / 100000, 2)

            # '8 LPA', '12 lakh'
            elif "lpa" in full or "lakh" in full or "lakhs" in full:
                lpa = num

            else:
                # If it's a large number like 600000 → convert to LPA
                if num > 1000:
                    lpa = round(num / 100000, 2)
                else:
                    lpa = num

            # Assign to correct field
            if "current" in full:
                salary["current_ctc_lpa"] = lpa
            elif "expected" in full or "desired" in full:
                salary["expected_ctc_lpa"] = lpa
            elif "ctc" in full:
                salary["current_ctc_lpa"] = lpa
            else:
                if salary["expected_ctc_lpa"] is None:
                    salary["expected_ctc_lpa"] = lpa

    return salary
