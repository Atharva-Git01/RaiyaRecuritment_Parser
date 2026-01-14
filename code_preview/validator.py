# validator.py
import datetime
import json
import re
from copy import deepcopy

# ===============================
# DATE NORMALIZER
# ===============================
MONTH_MAP = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


def normalize_date(date_str):
    """Convert ANY date format into YYYY-MM, if possible."""
    if not date_str or not isinstance(date_str, str):
        return ""

    s = date_str.lower().strip()

    # Handle "present"
    if "present" in s:
        now = datetime.datetime.now()
        return f"{now.year}-{now.month:02d}"

    # Find Month + Year combos like "Jan 2022"
    for key, mm in MONTH_MAP.items():
        if key in s:
            # Extract year
            match = re.search(r"(20\d{2}|19\d{2}|\d{2})", s)
            if match:
                year = match.group(1)
                # Fix cases like "22" → "2022"
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{mm}"

    # Find formats like 03/2020 or 3/20
    slash = re.match(r"(\d{1,2})/(\d{2,4})", s)
    if slash:
        mm = int(slash.group(1))
        year = slash.group(2)
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{mm:02d}"

    # If only year is present: "2020"
    yr = re.match(r"(19\d{2}|20\d{2})", s)
    if yr:
        year = yr.group(1)
        return f"{year}-01"

    # Unknown format, return raw
    return date_str


def calculate_total_experience(exp_list):
    """
    Compute total experience across all experience blocks in years (float).
    Handles overlapping date ranges correctly by merging intervals.
    Each block must have normalized YYYY-MM start/end dates.
    """
    intervals = []

    for exp in exp_list:
        sd = exp.get("start_date", "")
        ed = exp.get("end_date", "")

        if not sd or not ed or len(sd) != 7 or len(ed) != 7:
            continue

        try:
            sy, sm = map(int, sd.split("-"))
            ey, em = map(int, ed.split("-"))
            start = datetime.date(sy, sm, 1)
            end = datetime.date(ey, em, 1)
            
            # Ensure start <= end
            if start > end:
                continue
                
            intervals.append((start, end))
        except:
            continue

    if not intervals:
        return 0.0

    # Sort by start date
    intervals.sort(key=lambda x: x[0])

    merged = []
    if intervals:
        curr_start, curr_end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start <= curr_end:  # Overlap or adjacent
                curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))

    total_months = 0
    for start, end in merged:
        # Calculate months (inclusive of start month, exclusive of end month logic usually, 
        # but for experience we often want roughly the span. 
        # (end.year - start.year) * 12 + (end.month - start.month) is standard difference.
        diff = (end.year - start.year) * 12 + (end.month - start.month)
        # Add 1 month to be inclusive? Standard practice varies. 
        # Let's stick to simple difference but ensure at least 1 month if start==end?
        # Actually, usually start=Jan, end=Feb is 1 month. start=Jan, end=Jan is 0.
        # Let's stick to difference.
        if diff > 0:
            total_months += diff

    return round(total_months / 12, 2)


def calculate_duration(start_date: str, end_date: str) -> float:
    """
    Convert YYYY-MM → duration in years (float)
    Handles invalid/missing data.
    """
    if not start_date or not end_date:
        return 0.0

    try:
        s_year, s_month = map(int, start_date.split("-"))
        e_year, e_month = map(int, end_date.split("-"))
    except:
        return 0.0

    try:
        import datetime

        s = datetime.date(s_year, s_month, 1)
        e = datetime.date(e_year, e_month, 1)
    except:
        return 0.0

    months = (e.year - s.year) * 12 + (e.month - s.month)
    if months < 0:
        return 0.0

    return round(months / 12, 2)


def extract_keywords_from_text(text: str, alias_map: dict) -> set:
    """
    Scan role/description to find skill/tech keywords.
    """
    if not text:
        return set()

    t = text.lower()
    found = set()

    for alias, canonical in alias_map.items():
        if alias in t:
            found.add(canonical)

    return found


def extract_salary_from_resume(raw_text: str) -> dict:
    if not raw_text or not isinstance(raw_text, str):
        return {"current": None, "expected": None}

    text = raw_text.lower()

    # Correct merged token splitting:
    # "currentctc6.5lpa" → "current ctc 6.5 lpa"
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    # Remove fake alphanumeric-LPA (e.g., ABC123LPA)
    text = re.sub(r"[a-zA-Z]+(?=\d+lpa)", " ", text)

    # Patterns
    # STRICTER: block ABC123LPA fake matches
    lpa_pattern = r"(?<![A-Za-z])(\d+\.?\d*)\s*(?:lpa|lakh|lakhs|lac)"

    monthly_pattern = r"(\d+)\s*k\s*(?:per month|monthly|pm)"
    inr_pattern = r"(\d[\d,]{4,})\s*(?:per annum|pa|p\.a\.)?"

    current = None
    expected = None

    # -------------------------
    # 1) CURRENT extraction
    # -------------------------
    current_patterns = [
        rf"current\s*ctc[:\s]*{lpa_pattern}",
        rf"current\s*salary[:\s]*{lpa_pattern}",
        rf"current\s*compensation[:\s]*{lpa_pattern}",
        rf"current\s*ctc\s+{lpa_pattern}",
        rf"ctc[:\s]*{lpa_pattern}",
        rf"current\s*ctc[:\s]*(\d+\.?\d*)",
        rf"current\s*salary[:\s]*(\d+\.?\d*)",
    ]

    for pat in current_patterns:
        m = re.search(pat, text)
        if m:
            # Skip ONLY if pattern explicitly starts with 'expected'
            prefix = text[max(0, m.start() - 15) : m.start()]
            if "expected" in prefix:
                continue

            current = float(m.group(1))
            break

    # Monthly → LPA
    m = re.search(rf"current\s*salary[:\s]*{monthly_pattern}", text)
    if m:
        num = float(m.group(1))
        current = round((num * 12 * 1000) / 100000, 2)

    # INR annual → LPA
    m = re.search(rf"current\s*(?:salary|ctc)?[:\s]*{inr_pattern}", text)
    if m:
        num = float(m.group(1).replace(",", ""))
        current = round(num / 100000, 2)
    # Prevent CURRENT from being filled when the number actually belongs to EXPECTED
    m = re.search(r"expected[^\d]{0,10}(\d+\.?\d*)", text)
    if m:
        # Mark as expected ONLY – do not treat it as current
        expected = float(m.group(1))
        current = None

    # -------------------------
    # 2) EXPECTED extraction
    # -------------------------
    expected_patterns = [
        rf"expected\s*ctc[:\s]*{lpa_pattern}",
        rf"expected\s*salary[:\s]*{lpa_pattern}",
        rf"expected\s*compensation[:\s]*{lpa_pattern}",
        rf"expected\s*ctc\s+{lpa_pattern}",
        rf"expected[:\s]*{lpa_pattern}",
        rf"expected\s*ctc[:\s]*(\d+\.?\d*)",
        rf"expected\s*salary[:\s]*(\d+\.?\d*)",
    ]

    for pat in expected_patterns:
        m = re.search(pat, text)
        if m:
            expected = float(m.group(1))
            break

    # --- FIX #7: Expected appears before current ---
    pair = re.search(r"expected.*?(\d+\.?\d*).*?current.*?(\d+\.?\d*)", text, re.DOTALL)
    if pair:
        expected = float(pair.group(1))
        current = float(pair.group(2))

    # Monthly → LPA
    m = re.search(rf"expected\s*salary[:\s]*{monthly_pattern}", text)

    # -------------------------
    # 3) FALLBACK: LPA values
    # -------------------------
    lpa_vals = [float(x) for x in re.findall(lpa_pattern, text)]
    if current is None and expected is None:
        if len(lpa_vals) >= 1:
            expected = lpa_vals[0]
        if len(lpa_vals) >= 2:
            current = lpa_vals[0]
            expected = lpa_vals[1]

    # If multiple LPA values and both current/expected missing:
    if current is None and expected is None and len(lpa_vals) >= 2:
        current = lpa_vals[0]
        expected = lpa_vals[1]

    # -------------------------
    # 4) FALLBACK: INR (large numbers)
    # -------------------------
    inr_vals = re.findall(inr_pattern, text)
    if current is None and expected is None and len(inr_vals) >= 1:
        nums = [int(x.replace(",", "")) for x in inr_vals]
        nums.sort()
        if len(nums) == 1:
            expected = round(nums[0] / 100000, 2)
        elif len(nums) >= 2:
            current = round(nums[0] / 100000, 2)
            expected = round(nums[1] / 100000, 2)

    # -------------------------
    # 5) Rules
    # -------------------------
    if current is not None and expected is None:
        expected = current

    if current is not None and expected is not None and expected < current:
        expected = current

    return {"current": current, "expected": expected}


# ===============================
# SMART DESCRIPTION NORMALIZER
# ==============================
def convert_description_to_list(desc):
    """Smart normalize experience.description into a clean list."""
    if not isinstance(desc, str):
        return []

    desc = desc.strip()

    # CASE 1: JSON-like list string
    if desc.startswith("[") and desc.endswith("]"):
        try:
            parsed = json.loads(desc)
            return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass

    # CASE 2: Try safe sentence split
    sentences = re.split(r"(?<=[.!?])\s+", desc)

    # Avoid over-splitting → only accept small clean splits
    if 1 < len(sentences) <= 6:
        return [s.strip() for s in sentences if s.strip()]

    # CASE 3: fallback → one list element
    return [desc]


# ===============================
# EDUCATION / COURSE EXTRACTOR
# ===============================
def extract_courses_from_raw(raw_text):
    """
    Extracts coursework / subjects / modules from raw resume text.
    Zero hallucination — strict text-only extraction.
    Returns list of course strings.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    lines = [l.rstrip() for l in raw_text.split("\n")]

    keywords = ["course", "coursework", "relevant coursework", "subjects", "modules"]
    capture = False
    courses = []

    for line in lines:
        low = line.lower().strip()

        # start capture when we see coursework header
        if any(k in low for k in keywords) and len(low) < 60:
            capture = True
            # If header line contains inline items after colon, capture them:
            if ":" in line and "," in line:
                tail = line.split(":", 1)[1]
                parts = [p.strip() for p in tail.split(",") if p.strip()]
                courses.extend(parts)
            continue

        # stop when a new section header likely appears
        if capture and (re.match(r"^[A-Za-z].+\:$", line) or line.isupper()):
            break

        if capture:
            # bullets
            if line.strip().startswith("-") or line.strip().startswith("•"):
                item = line.strip().lstrip("-• ").strip()
                if item:
                    courses.append(item)
                continue

            # comma separated inline
            if "," in line:
                parts = [p.strip() for p in line.split(",") if p.strip()]
                courses.extend(parts)
                continue

            # plain line: treat as course ONLY if not a degree/institution/year line
            if 1 < len(line.split()) <= 6:

                # block degree-like content
                if re.search(
                    r"\b(b\.?tech|m\.?tech|b\.?sc|m\.?sc|b\.?e|m\.?e|bca|mca|ph\.?d|mba|ms|bs)\b",
                    low,
                ):
                    continue

                # block institution keywords
                if any(
                    word in low for word in ["university", "college", "institute", "|"]
                ):
                    continue

                # block year lines
                if re.search(r"\b(19\d{2}|20\d{2})\b", low):
                    continue

                # block lines that contain 'graduated' (these are education info, not courses)
                if "graduated" in low:
                    continue

                courses.append(line.strip())

    # clean & dedupe while preserving order
    seen = set()
    out = []
    for c in courses:
        if not c:
            continue
        s = c.strip()
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


# ===============================
# PROJECT EXTRACTOR
# ===============================
def extract_projects_from_raw(raw_text):
    """
    Extract project names + descriptions from raw resume text.
    This version is stricter about section boundaries and filters
    out false-positive headings like 'Certificates', 'Salary', 'Current CTC', etc.
    Returns list of {name, description}.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    lines = [l.rstrip() for l in raw_text.split("\n")]

    projects = []
    inside_section = False
    buffer_title = ""
    buffer_desc = []

    # Section headers that indicate projects start
    section_headers = ["project", "projects", "project work", "academic projects"]

    # Headers that mark the end of projects section
    stop_headers = set(
        [
            "experience",
            "education",
            "skills",
            "certificates",
            "certification",
            "summary",
            "salary",
            "salary details",
            "contact",
            "contact info",
            "contact information",
        ]
    )

    # Strings that should never be treated as project titles
    project_blacklist_keywords = set(
        ["certificate", "salary", "ctc", "current ctc", "expected ctc"]
    )

    for line in lines:
        stripped = line.strip()
        low = stripped.lower()

        # Detect section start
        if not inside_section and any(h in low for h in section_headers):
            inside_section = True
            # Reset buffers in case previous attempts left them
            buffer_title = ""
            buffer_desc = []
            continue

        if inside_section:
            # Stop when we hit a clear next-section header line
            if (
                low.rstrip(":") in stop_headers
                or re.match(r"^[A-Z ]{3,}$", stripped)
                or re.match(r"^[A-Za-z].+\:$", stripped)
            ):
                # flush any buffered project before exit
                if buffer_title:
                    entry = {
                        "name": buffer_title.strip(),
                        "description": " ".join(buffer_desc).strip(),
                    }
                    if entry not in projects:
                        projects.append(entry)
                break

            # Skip clearly non-project lines (salary, ctc, certificate headers)
            if any(k in low for k in project_blacklist_keywords):
                continue

            # Pattern 1: Title — Description (dash / em-dash)
            dash_split = re.split(r"\s[-–—]\s", stripped, maxsplit=1)
            if len(dash_split) == 2:
                # flush previous
                if buffer_title:
                    entry = {
                        "name": buffer_title.strip(),
                        "description": " ".join(buffer_desc).strip(),
                    }
                    if entry not in projects:
                        projects.append(entry)
                # new project
                candidate_title = dash_split[0].strip()
                candidate_desc = dash_split[1].strip()
                # filter out short garbage titles like "Salary Details" etc.
                if len(candidate_title) > 2 and not any(
                    k in candidate_title.lower() for k in project_blacklist_keywords
                ):
                    buffer_title = candidate_title
                    buffer_desc = [candidate_desc] if candidate_desc else []
                else:
                    buffer_title = ""
                    buffer_desc = []
                continue

            # Pattern 2: Bullet points (append to description)
            if stripped.startswith("-") or stripped.startswith("•"):
                bullet = stripped.lstrip("-• ").strip()
                if buffer_title and bullet:
                    buffer_desc.append(bullet)
                # if there is no buffer_title but bullets appear, attempt to treat last project as description
                elif not buffer_title and bullet:
                    # attach to last project if exists
                    if projects:
                        projects[-1]["description"] = (
                            projects[-1].get("description", "") + " " + bullet
                        ).strip()
                continue

            # Pattern 3: Standalone title lines - only accept if "looks like a project title"
            # heuristics: length between 3 and 60 characters, contains alphabetic and not blacklisted
            if (
                3 <= len(stripped) <= 60
                and any(ch.isalpha() for ch in stripped)
                and not any(k in low for k in project_blacklist_keywords)
            ):
                # If we already were buffering a title, flush it
                if buffer_title:
                    entry = {
                        "name": buffer_title.strip(),
                        "description": " ".join(buffer_desc).strip(),
                    }
                    if entry not in projects:
                        projects.append(entry)
                buffer_title = stripped
                buffer_desc = []
                continue

            # Otherwise, treat as continuation of description if we have a buffer_title
            if buffer_title:
                buffer_desc.append(stripped)
                continue

            # If nothing matched and no buffer, ignore the line (avoid garbage)
            continue

    # Final flush
    if buffer_title:
        entry = {
            "name": buffer_title.strip(),
            "description": " ".join(buffer_desc).strip(),
        }
        if entry not in projects:
            projects.append(entry)

    # Post-filter projects: remove entries whose name contains salary/ctc words or is too short
    final_projects = []
    for p in projects:
        name = (p.get("name") or "").strip()
        lowname = name.lower()
        if not name:
            continue
        if any(k in lowname for k in project_blacklist_keywords):
            continue
        if len(name) < 3:
            continue
        final_projects.append(
            {"name": name, "description": (p.get("description") or "").strip()}
        )

    return final_projects


def safe_str(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


ROLE_NORMALIZATION = {
    "software intern": "Software Intern",
    "sde intern": "Software Development Intern",
    "developer intern": "Software Developer Intern",
    "web intern": "Web Development Intern",
    "data intern": "Data Science Intern",
    "ml intern": "Machine Learning Intern",
    "python developer": "Python Developer",
    "web developer": "Web Developer",
    "frontend developer": "Frontend Developer",
    "backend developer": "Backend Developer",
    "full stack developer": "Full Stack Developer",
}


def normalize_role(role: str) -> str:
    if not isinstance(role, str):
        return ""

    r = role.strip().lower()

    # remove 'at', 'for', leading junk
    r = re.sub(r"\b(at|for)\b", "", r).strip()

    # direct mapping
    for key, value in ROLE_NORMALIZATION.items():
        if key in r:
            return value

    # Capitalize first letters
    return r.title()


def clean_company_name(name: str) -> str:
    if not isinstance(name, str):
        return ""

    name = name.strip().lower()

    # Remove noise words
    name = re.sub(r"\b(worked|working|at|for|company)\b", "", name, flags=re.IGNORECASE)

    # Remove leading symbols and extra spaces
    name = re.sub(r"[-–—]|:", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    # Title case the remaining words
    return name.title()


def validate_resume_data(data: dict) -> dict:
    """
    Cleans, normalizes, and validates parsed resume JSON.
    Ensures all keys exist and values are in the correct format.
    """

    # === Required keys with default values ===
    schema = {
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
    }

    if not isinstance(data, dict):
        data = {}

    # 1️⃣ Normalize keys to lowercase with safe coercion
    normalized = {}
    for k, v in data.items():
        key_str = str(k) if not isinstance(k, str) else k
        normalized[key_str.lower().strip()] = v

    # 2️⃣ Fill missing keys
    for key, default_value in schema.items():
        if key not in normalized or normalized[key] is None:
            normalized[key] = deepcopy(default_value)

    # Ensure raw_text is always a string for downstream consumers
    raw_text_value = normalized.get("raw_text", "")
    if isinstance(raw_text_value, list):
        raw_text_value = "\n".join([str(x) for x in raw_text_value])
    elif not isinstance(raw_text_value, str):
        raw_text_value = str(raw_text_value or "")
    normalized["raw_text"] = raw_text_value

    # 3️⃣ Normalize email
    email = normalized.get("email", "")
    if isinstance(email, str):
        email = email.strip()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            email = ""
    else:
        email = ""
    normalized["email"] = email

    # 4️⃣ Normalize phone number
    phone = normalized.get("phone", "")
    if isinstance(phone, str):
        phone = re.sub(r"[^0-9+]", "", phone)
        if len(phone) < 8:
            phone = ""
    normalized["phone"] = phone

    # 5️⃣ Normalize skills to list
    skills = normalized.get("skills", [])
    if isinstance(skills, str):
        skills = re.split(r",|;|\n", skills)
    normalized["skills"] = [s.strip() for s in skills if s.strip()]

    # 6️⃣ Standardize education list
    edu_list = normalized.get("education", [])
    if isinstance(edu_list, dict):
        edu_list = [edu_list]
    clean_edu = []
    for edu in edu_list:
        if isinstance(edu, str):
            clean_edu.append(
                {"degree": edu, "institution": "", "year_start": "", "year_end": ""}
            )
        elif isinstance(edu, dict):
            degree = safe_str(edu.get("degree", "")).strip()
            institution = safe_str(edu.get("institution", "")).strip()
            year_raw = safe_str(edu.get("year", "")).strip()

            year_start = ""
            year_end = ""

            # 1) look for range like "2018 - 2022" or "2018–2022" or "2018 to 2022"
            r = re.search(
                r"(19\d{2}|20\d{2})\s*[–—\-to]{0,5}\s*(19\d{2}|20\d{2})",
                year_raw,
                flags=re.IGNORECASE,
            )
            if r:
                year_start = normalize_date(r.group(1))
                year_end = normalize_date(r.group(2))
            else:
                # 2) look for single year (graduated/pursuing)
                s = re.search(r"(19\d{2}|20\d{2})", year_raw)
                if s:
                    year_start = normalize_date(s.group(1))
                    # if string contains 'pursuing' or 'present', set year_end to present
                    if re.search(
                        r"pursu|present|ongoing|current", year_raw, flags=re.IGNORECASE
                    ):
                        year_end = normalize_date("present")
                    else:
                        year_end = ""

            clean_edu.append(
                {
                    "degree": degree,
                    "institution": institution,
                    "year_start": year_start,
                    "year_end": year_end,
                }
            )

    normalized["education"] = clean_edu

    # === Stage 7: Extract courses from raw_text (fallback if LLM didn't provide)
    raw_text = normalized.get("raw_text", "")
    if isinstance(raw_text, list):
        raw_text = "\n".join([str(x) for x in raw_text])
    normalized["courses"] = extract_courses_from_raw(raw_text)

    # 7️⃣ Standardize experience list
    exp_list = normalized.get("experience", [])
    if isinstance(exp_list, dict):
        exp_list = [exp_list]

    clean_exp = []
    for exp in exp_list:
        if isinstance(exp, dict):

            # Extract description using smart LLM logic
            desc_list = convert_description_to_list(exp.get("description", ""))

            # Fallback: if LLM returned empty list, extract bullets manually
            if not desc_list:
                raw_desc = exp.get("description", "")

                if isinstance(raw_desc, list):
                    raw_desc = "\n".join([str(x) for x in raw_desc])
                elif raw_desc is None:
                    raw_desc = ""

                bullets = []
                for line in raw_desc.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("•"):
                        bullets.append(line.lstrip("-• ").strip())

                if not bullets:
                    full_raw = normalized.get("raw_text", "")
                    if isinstance(full_raw, list):
                        full_raw = "\n".join([str(x) for x in full_raw])

                    if full_raw:
                        raw_lines = full_raw.split("\n")

                        # Identify raw segments per company
                        cleaned_company = clean_company_name(
                            safe_str(exp.get("company", ""))
                        ).lower()

                        capture = False

                        for raw in raw_lines:
                            r = raw.strip()

                            # Start capturing when we hit the company header
                            if cleaned_company and cleaned_company in r.lower():
                                capture = True
                                continue

                            # Stop capturing when next job header appears
                            if capture and re.match(
                                r"^(intern|developer|software engineer|software developer|software development engineer|sde|sde ?-? ?\d|python developer|ml engineer|full stack developer|frontend developer|backend developer)\b",
                                r.lower(),
                            ):
                                break

                            if capture:
                                if r.startswith("-") or r.startswith("•"):
                                    bullets.append(r.lstrip("-• ").strip())

                if bullets:
                    desc_list = bullets

                # Split long bullets into short clean points
                final_desc = []
                for d in desc_list:
                    if len(d.split()) > 18:
                        # break into sentences
                        parts = re.split(r"[.!?]\s+", d)
                        for p in parts:
                            p = p.strip()
                            if len(p) > 3:
                                final_desc.append(p)
                    else:
                        final_desc.append(d)

                desc_list = final_desc

            # === Append experience block (NOW CORRECT & COMPLETE) ===
            clean_exp.append(
                {
                    "company": clean_company_name(safe_str(exp.get("company", ""))),
                    "role": normalize_role(safe_str(exp.get("role", ""))),
                    "start_date": normalize_date(
                        safe_str(exp.get("start_date", "")).strip()
                    ),
                    "end_date": normalize_date(
                        safe_str(exp.get("end_date", "")).strip()
                    ),
                    "description": desc_list,
                }
            )

            # === Fix reversed / wrong dates ===
            sd = clean_exp[-1]["start_date"]
            ed = clean_exp[-1]["end_date"]

            if sd and ed and sd > ed:
                clean_exp[-1]["start_date"], clean_exp[-1]["end_date"] = ed, sd

            # === DATE FALLBACK USING RAW TEXT ===
            if not clean_exp[-1]["start_date"] or not clean_exp[-1]["end_date"]:

                rt = normalized.get("raw_text", "")
                if isinstance(rt, list):
                    rt = "\n".join([str(x) for x in rt])

                # Look for date ranges like "Jan 2020 - Dec 2021"
                date_range = re.search(
                    r"([A-Za-z]{3,9}\s+\d{2,4}).{1,6}([A-Za-z]{3,9}\s+\d{2,4})", rt
                )
                if date_range:
                    start_raw = date_range.group(1)
                    end_raw = date_range.group(2)
                    clean_exp[-1]["start_date"] = normalize_date(start_raw)
                    clean_exp[-1]["end_date"] = normalize_date(end_raw)

            # === FINAL DATE CORRECTION (AFTER FALLBACK) ===
            sd = clean_exp[-1]["start_date"]
            ed = clean_exp[-1]["end_date"]

            # Fix reversed dates like 2022–2021
            if sd and ed and sd > ed:
                clean_exp[-1]["start_date"], clean_exp[-1]["end_date"] = ed, sd

    normalized["experience"] = clean_exp

    # =======================================================
    # RELEVANT EXPERIENCE SCORING (Skill-wise Years)
    # =======================================================

    # Import alias maps from normalizer_pre_score
    from app.normalizer_pre_score import edu_aliases, skill_aliases, tech_aliases

    all_alias_map = {**tech_aliases, **skill_aliases, **edu_aliases}

    relevant_experience_map = {}

    for exp in clean_exp:
        years = calculate_duration(exp.get("start_date"), exp.get("end_date"))

        role_text = exp.get("role", "")
        desc_text = " ".join(exp.get("description", []))

        # Extract relevant skills/technologies
        keywords = set()
        keywords |= extract_keywords_from_text(role_text, all_alias_map)
        keywords |= extract_keywords_from_text(desc_text, all_alias_map)

        # Add experience years for each skill
        for kw in keywords:
            relevant_experience_map[kw] = relevant_experience_map.get(kw, 0.0) + years

    normalized["relevant_experience_map"] = relevant_experience_map

    # 8️⃣ Standardize projects (Stage 9)
    proj_list = normalized.get("projects", [])

    clean_proj = []

    # ---- 1) Use LLM projects if valid ----
    if isinstance(proj_list, dict):
        proj_list = [proj_list]

    for proj in proj_list:
        if not isinstance(proj, dict):
            continue

        nm = safe_str(proj.get("name", "")).strip()
        ds = safe_str(proj.get("description", "")).strip()

        # Skip garbage entries: empty, "-", "N/A", etc.
        if not nm or nm in ["-", "--", "none", "null", "n/a"]:
            continue

        entry = {"name": nm, "description": ds}

        # Deduplicate projects based on name
        if not any(p["name"].lower() == nm.lower() for p in clean_proj):
            clean_proj.append(entry)

    # ---- 2) ALWAYS also extract from raw_text and MERGE with LLM projects ----
    raw_text = normalized.get("raw_text", "")
    if isinstance(raw_text, list):
        raw_text = "\n".join([str(x) for x in raw_text])

    extracted = extract_projects_from_raw(raw_text)

    for p in extracted:
        nm = p.get("name", "").strip()
        ds = p.get("description", "").strip()

        if not nm:
            continue

        # Add only if project is NOT already present
        if not any(existing["name"].lower() == nm.lower() for existing in clean_proj):
            clean_proj.append({"name": nm, "description": ds})

    normalized["projects"] = clean_proj

    # 10️⃣ Standardize certificates (Stage 10)
    cert_list = normalized.get("certificates", [])

    # Normalize string → list
    if isinstance(cert_list, str):
        cert_list = re.split(r",|;|\n|- ", cert_list)
    elif isinstance(cert_list, dict):
        cert_list = [cert_list]

    clean_cert = []

    # ----------------------------------------------------
    # 1) CLEAN LLM-PROVIDED CERTIFICATES (DEDUPE + CLEAN)
    # ----------------------------------------------------
    for cert in cert_list:
        if isinstance(cert, dict):
            name = safe_str(cert.get("name", "")).strip()
        else:
            name = safe_str(cert).strip()

        name = name.lstrip("-• ").strip()

        if not name or name.lower() in ["-", "n/a", "null", "none"]:
            continue

        parts = [p.strip() for p in name.split(",") if p.strip()]
        for p in parts:
            if p.lower() not in [c.lower() for c in clean_cert]:
                clean_cert.append(p)

    # ----------------------------------------------------
    # 2) MERGE RAW TEXT CERTIFICATES (STRICT EXTRACTION)
    # ----------------------------------------------------

    raw = normalized.get("raw_text", "")
    if isinstance(raw, list):
        raw = "\n".join([str(x) for x in raw])

    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    capture = False
    cert_candidates = []

    cert_section_keywords = ["certificate", "certification", "certifications"]
    end_section_keywords = [
        "experience",
        "projects",
        "project",
        "education",
        "skills",
        "summary",
        "salary",
        "contact",
    ]

    for line in lines:
        low = line.lower()

        if (
            not capture
            and any(k in low for k in cert_section_keywords)
            and len(low) < 60
        ):
            capture = True
            continue

        if capture and (
            low in end_section_keywords
            or re.match(r"^[A-Z ]{3,}$", line)
            or re.match(r"^[A-Za-z].+\:$", line)
        ):
            break

        if capture:
            if any(k in low for k in ["ctc", "salary", "lpa"]):
                continue

            if line[:1] in ["-", "•", "–", "—"]:
                item = line.lstrip("-•–— ").strip()
                if item:
                    cert_candidates.append(item)
                continue

            if "," in line:
                cert_candidates.extend(
                    [p.strip() for p in line.split(",") if p.strip()]
                )
                continue

            if 1 <= len(line.split()) <= 12:
                cert_candidates.append(line)

    # Merge raw certs
    for c in cert_candidates:
        if c.lower() not in [x.lower() for x in clean_cert]:
            clean_cert.append(c)

    # ----------------------------------------------------
    # 3) FINAL DEDUPLICATION (KEEP ONLY BEST VERSION)
    # ----------------------------------------------------

    final_cert = []

    def normalize_text(s):
        return re.sub(r"\s+", " ", s.strip().lower())

    for cert in clean_cert:
        c_norm = normalize_text(cert)

        is_sub = False
        to_remove = []

        for fc in final_cert:
            fc_norm = normalize_text(fc)

            if c_norm in fc_norm and c_norm != fc_norm:
                is_sub = True
                break

            if fc_norm in c_norm and c_norm != fc_norm:
                to_remove.append(fc)

        if is_sub:
            continue

        for r in to_remove:
            final_cert.remove(r)

        if cert not in final_cert:
            final_cert.append(cert)

    # FINAL RESULT
    normalized["certificates"] = final_cert

    # 🔟 Trim name & location
    normalized["name"] = safe_str(normalized["name"]).strip().title()
    normalized["location"] = safe_str(normalized["location"]).strip()

    # 1️⃣1️⃣ Final summary clean
    normalized["summary"] = safe_str(normalized.get("summary", "")).strip()

    # === SALARY EXTRACTION PATCH (Step 2) ===
    raw_salary = extract_salary_from_resume(normalized.get("raw_text", ""))

    # Force salary to come ONLY from resume text, ignore parser completely
    current = raw_salary.get("current")
    expected = raw_salary.get("expected")

    # Rule: expected >= current
    if current is not None and expected is not None and expected < current:
        expected = current

    # Rule: if expected missing → expected = current
    if current is not None and expected is None:
        expected = current

    normalized["salary"] = {
        "current_ctc_lpa": current,
        "expected_ctc_lpa": expected,
    }

    normalized["total_experience_years"] = calculate_total_experience(
        normalized["experience"]
    )

    return normalized
