import os
from typing import List, Optional


def get_repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_existing(paths: List[str]) -> Optional[str]:
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def get_results_dir() -> str:
    path = os.path.join(get_repo_root(), "results")
    os.makedirs(path, exist_ok=True)
    return path


def get_resume_dir() -> str:
    root = get_repo_root()
    return _resolve_existing(
        [
            os.path.join(root, "uploads", "parsed resumes"),
            os.path.join(root, "uploads"),
        ]
    ) or os.path.join(root, "uploads")


def get_jd_dir() -> str:
    root = get_repo_root()
    return _resolve_existing(
        [
            os.path.join(root, "uploads", "jd"),
            os.path.join(root, "uploads"),
        ]
    ) or os.path.join(root, "uploads")


def resolve_resume_path(preferred_name: str = "") -> str:
    resume_dir = get_resume_dir()
    candidates = []
    if preferred_name:
        candidates.append(os.path.join(resume_dir, preferred_name))
        if not preferred_name.endswith(".json"):
            candidates.append(os.path.join(resume_dir, f"{preferred_name}.json"))

    candidates.extend(
        [
            os.path.join(resume_dir, "test_parsed_resume_6.json"),
            os.path.join(resume_dir, "test_parsed_resume"),
        ]
    )
    return _resolve_existing(candidates) or candidates[0]


def resolve_jd_path(preferred_name: str = "job_description.json") -> str:
    jd_dir = get_jd_dir()
    candidates = [os.path.join(jd_dir, preferred_name)]
    if preferred_name != "job_description.json":
        candidates.append(os.path.join(jd_dir, "job_description.json"))
    return _resolve_existing(candidates) or candidates[0]


def list_resume_files() -> List[str]:
    resume_dir = get_resume_dir()
    if not os.path.isdir(resume_dir):
        return []
    return sorted(
        [
            os.path.join(resume_dir, file_name)
            for file_name in os.listdir(resume_dir)
            if file_name.endswith(".json")
        ]
    )
