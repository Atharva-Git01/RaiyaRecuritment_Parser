"""
Phase 1: Historical Score Quality Analyzer
===========================================
Reads all results/*.json files and produces:
  1. Reproducibility matrix (score variance across runs for same resume)
  2. Ranking stability (do archetypes always rank the same?)
  3. Guardrail / override fire rates
  4. Score distribution overview

NO API calls required — pure offline analysis.
"""

import os
import sys
import json
import statistics
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "score_analysis_report.json")

COMPONENT_KEYS = [
    "final_score",
    "skills_score",
    "experience_score",
    "relevant_experience_score",
    "projects_score",
    "certificates_score",
    "tools_score",
    "technologies_score",
    "qualification_score",
    "responsibilities_score",
    "salary_score",
    "position_score",
]

# Known archetype short names (extracted from filenames)
ARCHETYPE_ORDER = [
    "5_perfect_lead",
    "1_senior_java_mismatch",
    "2_junior_prodigy",
    "3_phd_academic",
    "4_career_switcher",
]


def load_all_results():
    """Load all result JSON files from results/ directory."""
    results = []
    if not os.path.isdir(RESULTS_DIR):
        print(f"Results directory not found: {RESULTS_DIR}")
        return results

    for fname in sorted(os.listdir(RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(RESULTS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_filename"] = fname
            results.append(data)
        except Exception as e:
            print(f"  ⚠️ Failed to load {fname}: {e}")

    return results


def extract_resume_key(filename):
    """Extract a canonical resume identifier from the result filename."""
    # Pattern: score_{resume_name}_{timestamp}.json
    # e.g. score_5_perfect_lead_20260304_154606.json
    # Also: scoring_result_resume_7_20260305_114947.json
    name = filename.replace(".json", "")

    # Remove timestamp suffix (last two underscore-separated groups that look like dates)
    parts = name.split("_")

    # Find the timestamp portion (YYYYMMDD_HHMMSS at the end)
    # Walk backwards and strip date-like parts
    ts_parts = []
    while parts and parts[-1].isdigit() and len(parts[-1]) >= 6:
        ts_parts.insert(0, parts.pop())

    # Remove 'score_' or 'scoring_result_' prefix
    remaining = "_".join(parts)
    for prefix in ["score_", "scoring_result_"]:
        if remaining.startswith(prefix):
            remaining = remaining[len(prefix):]
            break

    return remaining


def get_candidate_name(result):
    """Extract candidate name from result data."""
    inputs = result.get("inputs", {})
    resume = inputs.get("resume", {})
    pi = resume.get("personal_info", {})
    name = pi.get("name") or resume.get("name") or resume.get("candidate_name", "Unknown")
    return name


def analyze_reproducibility(results):
    """Analyze score variance across runs for the same resume."""
    # Group results by resume key
    groups = defaultdict(list)
    for r in results:
        key = extract_resume_key(r["_filename"])
        res = r.get("result")
        if not res or not isinstance(res, dict):
            continue
        groups[key].append({
            "filename": r["_filename"],
            "name": get_candidate_name(r),
            "scores": {k: res.get(k, 0) for k in COMPONENT_KEYS},
            "guardrails": res.get("guardrails_applied", []),
        })

    report = {}
    for resume_key, entries in sorted(groups.items()):
        if len(entries) < 2:
            continue  # Can't compute variance with < 2 runs

        entry_report = {
            "candidate_name": entries[0]["name"],
            "run_count": len(entries),
            "runs": [],
            "variance": {},
            "flags": [],
        }

        for e in entries:
            entry_report["runs"].append({
                "file": e["filename"],
                "final_score": e["scores"]["final_score"],
            })

        # Compute per-component variance
        for key in COMPONENT_KEYS:
            values = [e["scores"][key] for e in entries]
            if len(values) >= 2:
                avg = statistics.mean(values)
                stdev = statistics.stdev(values)
                max_drift = max(values) - min(values)
                entry_report["variance"][key] = {
                    "values": values,
                    "mean": round(avg, 2),
                    "stdev": round(stdev, 2),
                    "max_drift": max_drift,
                }
                # Flag high variance
                if key == "final_score" and max_drift > 5:
                    entry_report["flags"].append(
                        f"⚠️ final_score drift = {max_drift} (threshold: 5)"
                    )
                elif key != "final_score" and max_drift > 10:
                    entry_report["flags"].append(
                        f"⚠️ {key} drift = {max_drift} (threshold: 10)"
                    )

        report[resume_key] = entry_report

    return report


def analyze_ranking_stability(results):
    """Check if archetype resumes always rank in the expected order."""
    # Group by run date (extracted from filename timestamp)
    runs_by_date = defaultdict(dict)
    for r in results:
        key = extract_resume_key(r["_filename"])
        res = r.get("result")
        if not res:
            continue

        # Check if this is an archetype
        if not any(arch in key for arch in ARCHETYPE_ORDER):
            continue

        # Extract date from filename
        fname = r["_filename"].replace(".json", "")
        parts = fname.split("_")
        # Find the date part (YYYYMMDD)
        date_str = None
        for p in parts:
            if len(p) == 8 and p.isdigit():
                date_str = p
                break

        if date_str:
            for arch in ARCHETYPE_ORDER:
                if arch in key:
                    runs_by_date[date_str][arch] = res.get("final_score", 0)
                    break

    ranking_report = {
        "expected_order": ARCHETYPE_ORDER,
        "runs": {},
        "inversions": [],
    }

    for date_str, scores in sorted(runs_by_date.items()):
        # Sort by score descending
        actual_ranking = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        ranking_report["runs"][date_str] = {
            "scores": scores,
            "ranking": actual_ranking,
        }

        # Check for inversions against expected
        for i, arch in enumerate(ARCHETYPE_ORDER):
            if arch in actual_ranking:
                actual_pos = actual_ranking.index(arch)
                if actual_pos != i and arch in scores:
                    ranking_report["inversions"].append({
                        "date": date_str,
                        "expected_pos": i,
                        "actual_pos": actual_pos,
                        "archetype": arch,
                        "score": scores[arch],
                    })

    return ranking_report


def analyze_guardrail_fire_rates(results):
    """Check how often deterministic overrides fired."""
    total = 0
    salary_override = 0
    exp_override_count = 0
    qual_override_count = 0
    fresher_guardrail = 0
    guardrails_fired = 0

    for r in results:
        res = r.get("result")
        if not res:
            continue
        total += 1

        notes = res.get("notes", "")
        guardrails = res.get("guardrails_applied", [])

        if "[Salary Calculated:" in notes:
            salary_override += 1

        if any("Exp. Limited" in g for g in guardrails):
            fresher_guardrail += 1

        if guardrails:
            guardrails_fired += 1

    return {
        "total_results": total,
        "salary_override_fired": salary_override,
        "salary_override_pct": round(salary_override / max(total, 1) * 100, 1),
        "fresher_guardrail_fired": fresher_guardrail,
        "fresher_guardrail_pct": round(fresher_guardrail / max(total, 1) * 100, 1),
        "any_guardrail_fired": guardrails_fired,
    }


def analyze_score_distribution(results):
    """Compute distribution statistics across all results."""
    all_finals = []
    component_all = defaultdict(list)

    for r in results:
        res = r.get("result")
        if not res:
            continue
        for key in COMPONENT_KEYS:
            val = res.get(key, 0)
            component_all[key].append(val)
            if key == "final_score":
                all_finals.append(val)

    dist = {}
    for key in COMPONENT_KEYS:
        vals = component_all[key]
        if not vals:
            continue
        dist[key] = {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": round(statistics.mean(vals), 1),
            "median": round(statistics.median(vals), 1),
            "stdev": round(statistics.stdev(vals), 1) if len(vals) > 1 else 0,
        }

    # Histogram buckets for final_score
    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in all_finals:
        if s <= 20:
            buckets["0-20"] += 1
        elif s <= 40:
            buckets["21-40"] += 1
        elif s <= 60:
            buckets["41-60"] += 1
        elif s <= 80:
            buckets["61-80"] += 1
        else:
            buckets["81-100"] += 1

    dist["final_score_histogram"] = buckets

    return dist


def print_report(repro, ranking, guardrails, distribution):
    """Pretty-print the analysis report."""
    print("\n" + "=" * 80)
    print("  SCORING QUALITY ANALYSIS REPORT")
    print("=" * 80)

    # --- Reproducibility ---
    print("\n📊 1. REPRODUCIBILITY ANALYSIS")
    print("-" * 60)
    flagged = 0
    for resume_key, data in repro.items():
        name = data["candidate_name"]
        runs = data["run_count"]
        final_var = data["variance"].get("final_score", {})
        drift = final_var.get("max_drift", 0)
        stdev = final_var.get("stdev", 0)
        flags = data["flags"]

        status = "✅" if not flags else "⚠️"
        print(f"  {status} {name:<30} | Runs: {runs} | Final drift: {drift} | StDev: {stdev:.1f}")
        if flags:
            flagged += 1
            for f in flags:
                print(f"       {f}")

    print(f"\n  Summary: {len(repro)} resumes analyzed, {flagged} flagged for high variance")

    # --- Ranking Stability ---
    print("\n📊 2. RANKING STABILITY")
    print("-" * 60)
    print(f"  Expected order: {' > '.join(ARCHETYPE_ORDER)}")
    for date_str, run_data in ranking["runs"].items():
        scores_str = ", ".join(f"{k}: {v}" for k, v in run_data["scores"].items())
        print(f"\n  Run {date_str}:")
        print(f"    Scores: {scores_str}")
        print(f"    Ranking: {' > '.join(run_data['ranking'])}")

    if ranking["inversions"]:
        print(f"\n  ⚠️ Found {len(ranking['inversions'])} rank inversions:")
        for inv in ranking["inversions"]:
            print(f"    - {inv['date']}: {inv['archetype']} expected #{inv['expected_pos']+1}, got #{inv['actual_pos']+1} (score: {inv['score']})")
    else:
        print("\n  ✅ No rank inversions detected!")

    # --- Guardrail Fire Rates ---
    print("\n📊 3. GUARDRAIL / OVERRIDE FIRE RATES")
    print("-" * 60)
    print(f"  Total results analyzed: {guardrails['total_results']}")
    print(f"  Salary override fired:  {guardrails['salary_override_fired']} ({guardrails['salary_override_pct']}%)")
    print(f"  Fresher guardrail:      {guardrails['fresher_guardrail_fired']} ({guardrails['fresher_guardrail_pct']}%)")
    print(f"  Any guardrail fired:    {guardrails['any_guardrail_fired']}")

    # --- Score Distribution ---
    print("\n📊 4. SCORE DISTRIBUTION")
    print("-" * 60)
    print(f"  {'Component':<30} | {'Min':>4} | {'Max':>4} | {'Mean':>6} | {'Median':>6} | {'StDev':>6}")
    print(f"  {'-'*30}-+-{'-'*4}-+-{'-'*4}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")
    for key in COMPONENT_KEYS:
        d = distribution.get(key, {})
        if not d:
            continue
        print(f"  {key:<30} | {d['min']:>4} | {d['max']:>4} | {d['mean']:>6} | {d['median']:>6} | {d['stdev']:>6}")

    hist = distribution.get("final_score_histogram", {})
    if hist:
        print(f"\n  Final Score Histogram:")
        for bucket, count in hist.items():
            bar = "█" * count
            print(f"    {bucket:>6}: {bar} ({count})")

    print("\n" + "=" * 80)


def main():
    print("Loading results...")
    results = load_all_results()
    print(f"Loaded {len(results)} result files.\n")

    if not results:
        print("No results found. Run the scoring pipeline first.")
        return

    # Filter to only successful results
    successful = [r for r in results if r.get("current_state") == "COMPLETED" and r.get("result")]
    print(f"Successful results: {successful.__len__()}")

    repro = analyze_reproducibility(successful)
    ranking = analyze_ranking_stability(successful)
    guardrails = analyze_guardrail_fire_rates(successful)
    distribution = analyze_score_distribution(successful)

    print_report(repro, ranking, guardrails, distribution)

    # Save JSON report
    full_report = {
        "generated_at": datetime.now().isoformat(),
        "total_files": len(results),
        "successful_files": len(successful),
        "reproducibility": repro,
        "ranking_stability": ranking,
        "guardrail_fire_rates": guardrails,
        "score_distribution": distribution,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, default=str)
    print(f"\nFull report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
