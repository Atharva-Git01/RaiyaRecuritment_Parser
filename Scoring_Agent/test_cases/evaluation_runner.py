import argparse
import json
import os
import re
import sys
import time
import uuid
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_controller import AgentController
from ai_scorer import AZURE_AI_ENDPOINT, API_KEY, DEPLOYMENT_ID, _get_active_version
from test_cases.evaluation_harness import (
    CORE_ARCHETYPE_ORDER,
    DEFAULT_RESULTS_DIR,
    evaluate_result_payload,
    load_benchmark_manifest,
    time_call,
    write_evaluation_report,
)


SYNTHETIC_FIXTURES: Dict[str, Dict] = {
    "minimal_resume": {"personal_info": {"name": "Empty Candidate"}},
    "skills_only_candidate": {
        "personal_info": {"name": "Skills Only"},
        "skills": [f"Skill_{index}" for index in range(50)],
        "experience": [],
        "education": [],
    },
    "future_dates_candidate": {
        "personal_info": {"name": "Future Candidate"},
        "skills": ["Python"],
        "experience": [
            {
                "title": "Future Engineer",
                "company": "FutureCorp",
                "start_date": "2027-01",
                "end_date": "2028-01",
                "description": "Will use Python and AWS.",
            }
        ],
    },
    "extreme_salary_candidate": {
        "personal_info": {"name": "Expensive Candidate"},
        "skills": ["Python"],
        "salary_expectation": {"currency": "INR", "amount": 9999999},
    },
    "zero_salary_candidate": {
        "personal_info": {"name": "Zero Salary"},
        "skills": ["Python"],
        "salary_expectation": {"currency": "INR", "amount": 0},
    },
    "overlapping_roles_candidate": {
        "personal_info": {"name": "Overlapper"},
        "skills": ["Python"],
        "experience": [
            {
                "title": "Role 1",
                "company": "Company 1",
                "start_date": "2020-01",
                "end_date": "2021-06",
                "description": "Used Python and AWS in role 1.",
            },
            {
                "title": "Role 2",
                "company": "Company 2",
                "start_date": "2020-06",
                "end_date": "2022-01",
                "description": "Used Python and AWS in role 2.",
            },
        ],
    },
    "vague_descriptions_candidate": {
        "personal_info": {"name": "Vague Candidate"},
        "experience": [
            {
                "title": "Engineer",
                "company": "Unknown",
                "start_date": "2022-01",
                "end_date": "Present",
                "description": "Worked on many things and helped the team succeed.",
            }
        ],
    },
    "academic_only_candidate": {
        "personal_info": {"name": "Academic Candidate"},
        "education": [{"degree": "PhD", "field": "Physics"}],
        "projects": [
            {
                "name": "Research Platform",
                "description": "Published papers and ran simulations with Matlab and LaTeX.",
            }
        ],
    },
    "legacy_stack_candidate": {
        "personal_info": {"name": "Legacy Candidate"},
        "experience": [
            {
                "title": "Senior Java Developer",
                "company": "LegacyCo",
                "start_date": "2014-01",
                "end_date": "2023-12",
                "description": "Maintained Java 7, JSP, Servlets, Oracle Forms, and WebLogic systems.",
            }
        ],
    },
    "career_switcher_variant": {
        "personal_info": {"name": "Switcher Variant"},
        "experience": [
            {
                "title": "Sales Manager",
                "company": "RetailCo",
                "start_date": "2016-01",
                "end_date": "2024-01",
                "description": "Managed quotas, team scheduling, and regional growth targets.",
            }
        ],
        "projects": [
            {
                "name": "Bootcamp Demo",
                "description": "Built a small React demo in a weekend bootcamp project.",
            }
        ],
        "salary_expectation": {"currency": "INR", "amount": 600000},
    },
}


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_case_input(path: str) -> Dict:
    if path.startswith("generated://"):
        fixture_name = path.split("generated://", 1)[1]
        return SYNTHETIC_FIXTURES[fixture_name]
    return load_json(os.path.join(os.path.dirname(os.path.dirname(__file__)), path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run live Azure scoring benchmarks.")
    parser.add_argument("legacy_repeats", nargs="?", type=int, help="Legacy positional repeats override.")
    parser.add_argument("--mode", choices=["smoke", "repro"], default="smoke")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--scope", choices=["all", "real", "core"], default="all")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--output-tag", default="", help="Optional tag added to report filenames.")
    parser.add_argument("--case-filter", default="", help="Case-id substring filter for debugging.")
    parser.add_argument("--output-dir", default=DEFAULT_RESULTS_DIR)
    return parser


def parse_runner_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.repeats is None and args.legacy_repeats is not None:
        args.repeats = args.legacy_repeats
    if args.repeats is None:
        args.repeats = 1 if args.mode == "smoke" else 5
    args.repeats = max(int(args.repeats), 1)
    args.sleep_seconds = max(float(args.sleep_seconds), 0.0)
    args.case_filter = str(args.case_filter or "").strip()
    args.output_tag = str(args.output_tag or "").strip()
    return args


def inspect_env_file(env_path: str) -> List[str]:
    warnings: List[str] = []
    if not os.path.exists(env_path):
        return warnings

    valid_pattern = re.compile(r"^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=")
    with open(env_path, "r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not valid_pattern.match(line):
                warnings.append(f".env line {index} may not parse cleanly: {stripped[:80]}")
    return warnings


def ensure_output_dir_writable(output_dir: str) -> Tuple[bool, str]:
    try:
        os.makedirs(output_dir, exist_ok=True)
        probe_path = os.path.join(output_dir, ".write_probe")
        with open(probe_path, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe_path)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def preflight_live_run(output_dir: str) -> Dict[str, object]:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    dotenv_warnings = inspect_env_file(env_path)
    output_ok, output_error = ensure_output_dir_writable(output_dir)

    missing_credentials = []
    if not AZURE_AI_ENDPOINT:
        missing_credentials.append("AZURE_OPENAI_ENDPOINT")
    if not API_KEY:
        missing_credentials.append("AZURE_OPENAI_API_KEY")
    if not DEPLOYMENT_ID:
        missing_credentials.append("AZURE_OPENAI_DEPLOYMENT")

    errors = []
    if missing_credentials:
        errors.append(f"Missing Azure credentials: {', '.join(missing_credentials)}")
    if not output_ok:
        errors.append(f"Output directory is not writable: {output_error}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": dotenv_warnings,
        "deployment": DEPLOYMENT_ID or "unknown",
        "prompt_version": _get_active_version(),
        "output_dir": output_dir,
        "credentials_present": not missing_credentials,
        "missing_credentials": missing_credentials,
    }


def filter_manifest_cases(cases, scope: str, case_filter: str = ""):
    selected = []
    case_filter_lower = case_filter.lower()

    for case in cases:
        if scope == "real" and case.resume_path.startswith("generated://"):
            continue
        if scope == "core" and case.case_id not in CORE_ARCHETYPE_ORDER:
            continue
        if case_filter_lower and case_filter_lower not in case.case_id.lower():
            continue
        selected.append(case)

    return selected


def build_filename_prefix(mode: str, output_tag: str = "") -> str:
    prefix = f"azure_{mode}"
    if output_tag:
        prefix = f"{prefix}_{output_tag}"
    return prefix


def save_raw_output(output: Dict, output_dir: str, suite_batch_id: str, case_id: str, repeat_index: int) -> str:
    raw_dir = os.path.join(output_dir, suite_batch_id, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{case_id}_repeat_{repeat_index:02d}.json")
    with open(raw_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    return raw_path


def build_runner_config(args: argparse.Namespace, selected_cases_count: int, suite_batch_id: str) -> Dict[str, object]:
    return {
        "mode": args.mode,
        "repeats": args.repeats,
        "scope": args.scope,
        "sleep_seconds": args.sleep_seconds,
        "output_tag": args.output_tag,
        "case_filter": args.case_filter,
        "selected_cases_count": selected_cases_count,
        "suite_batch_id": suite_batch_id,
        "deployment": DEPLOYMENT_ID or "unknown",
        "prompt_version": _get_active_version(),
    }


def run_manifest(
    mode: str = "smoke",
    repeats: int | None = None,
    scope: str = "all",
    sleep_seconds: float = 1.0,
    output_tag: str = "",
    case_filter: str = "",
    output_dir: str = DEFAULT_RESULTS_DIR,
) -> Dict[str, object]:
    repeats = 1 if repeats is None and mode == "smoke" else repeats
    repeats = 5 if repeats is None and mode == "repro" else repeats
    repeats = max(int(repeats or 1), 1)
    sleep_seconds = max(float(sleep_seconds), 0.0)

    suite_batch_id = f"{mode}_{uuid.uuid4().hex[:12]}"
    cases = filter_manifest_cases(load_benchmark_manifest(), scope=scope, case_filter=case_filter)
    runner_config = {
        "mode": mode,
        "repeats": repeats,
        "scope": scope,
        "sleep_seconds": sleep_seconds,
        "output_tag": output_tag,
        "case_filter": case_filter,
        "selected_cases_count": len(cases),
        "suite_batch_id": suite_batch_id,
        "deployment": DEPLOYMENT_ID or "unknown",
        "prompt_version": _get_active_version(),
    }
    preflight_result = preflight_live_run(output_dir=output_dir)
    filename_prefix = build_filename_prefix(mode, output_tag=output_tag)

    if not preflight_result["ok"]:
        report_path, summary_path = write_evaluation_report(
            [],
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            runner_config=runner_config,
            preflight_result=preflight_result,
        )
        return {
            "run_results": [],
            "report_path": report_path,
            "summary_path": summary_path,
            "runner_config": runner_config,
            "preflight_result": preflight_result,
        }

    run_results = []
    total_runs = len(cases) * repeats
    completed_runs = 0

    for repeat_index in range(1, repeats + 1):
        for case in cases:
            try:
                resume = resolve_case_input(case.resume_path)
                jd = resolve_case_input(case.jd_path)
                agent = AgentController(resume, jd)
                output, latency_ms = time_call(agent.run)
            except Exception as exc:
                output = {"success": False, "error": f"Runner exception: {exc}"}
                latency_ms = 0

            try:
                raw_result_path = save_raw_output(
                    output=output,
                    output_dir=output_dir,
                    suite_batch_id=suite_batch_id,
                    case_id=case.case_id,
                    repeat_index=repeat_index,
                )
            except Exception:
                raw_result_path = ""
            run_results.append(
                evaluate_result_payload(
                    case=case,
                    output=output,
                    latency_ms=latency_ms,
                    deployment=DEPLOYMENT_ID or "unknown",
                    prompt_version=_get_active_version(),
                    suite_mode=mode,
                    suite_batch_id=suite_batch_id,
                    repeat_index=repeat_index,
                    scope=scope,
                    raw_result_path=raw_result_path,
                )
            )
            completed_runs += 1
            if sleep_seconds > 0 and completed_runs < total_runs:
                time.sleep(sleep_seconds)

    report_path, summary_path = write_evaluation_report(
        run_results,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
        runner_config=runner_config,
        preflight_result=preflight_result,
    )
    return {
        "run_results": [run.model_dump() for run in run_results],
        "report_path": report_path,
        "summary_path": summary_path,
        "runner_config": runner_config,
        "preflight_result": preflight_result,
    }


def main(argv: List[str] | None = None) -> Dict[str, object]:
    args = parse_runner_args(argv)
    result = run_manifest(
        mode=args.mode,
        repeats=args.repeats,
        scope=args.scope,
        sleep_seconds=args.sleep_seconds,
        output_tag=args.output_tag,
        case_filter=args.case_filter,
        output_dir=args.output_dir,
    )
    print(f"Wrote detailed evaluation report to: {result['report_path']}")
    print(f"Wrote summary report to: {result['summary_path']}")
    return result


if __name__ == "__main__":
    main(sys.argv[1:])
