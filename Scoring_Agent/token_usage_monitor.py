"""
token_usage_monitor.py
──────────────────────
Tracks input (prompt) and output (completion) token usage for every
LLM call made by the scoring pipeline.

Usage in ai_scorer.py
──────────────────────
    from token_usage_monitor import log_usage, get_summary, print_summary

    # Right after data = resp.json() in the retry loop:
    usage = data.get("usage", {})
    if usage:
        log_usage(
            candidate=resume_for_prompt.get("name", "unknown"),
            usage=usage,
            model=DEPLOYMENT_ID,
        )

Log file: storage/token_log.jsonl  (one JSON object per line)
"""

import os
import json
import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG  –  update pricing if your model/region changes
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "storage", "token_log.jsonl")

# Azure Phi-4 / GPT-4o pricing per 1,000 tokens (USD) — adjust as needed
PROMPT_COST_PER_1K     = 0.00030   # input tokens
COMPLETION_COST_PER_1K = 0.00060   # output tokens


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def log_usage(candidate: str, usage: dict, model: str = "unknown") -> None:
    """
    Append one token-usage record to the JSONL log.

    Parameters
    ----------
    candidate : str  — candidate name (from resume["name"])
    usage     : dict — the 'usage' object from the Azure API response,
                       e.g. {"prompt_tokens": 1850, "completion_tokens": 310, "total_tokens": 2160}
    model     : str  — deployment / model name
    """
    prompt_tok = int(usage.get("prompt_tokens",     usage.get("input_tokens",  0)))
    compl_tok  = int(usage.get("completion_tokens", usage.get("output_tokens", 0)))
    total_tok  = int(usage.get("total_tokens",      prompt_tok + compl_tok))

    est_cost   = (prompt_tok / 1000 * PROMPT_COST_PER_1K) + \
                 (compl_tok  / 1000 * COMPLETION_COST_PER_1K)

    entry = {
        "ts":                datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "candidate":         str(candidate),
        "model":             str(model),
        "prompt_tokens":     prompt_tok,
        "completion_tokens": compl_tok,
        "total_tokens":      total_tok,
        "est_cost_usd":      round(est_cost, 6),
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(
        f"   -> TOKEN USAGE: prompt={prompt_tok}, "
        f"completion={compl_tok}, total={total_tok}, "
        f"est_cost=${est_cost:.5f}"
    )


def get_summary(last_n: int = None) -> dict:
    """
    Read the token log and return aggregate statistics.

    Parameters
    ----------
    last_n : int | None — if set, only consider the last N records

    Returns
    -------
    dict with keys:
        calls, total_prompt, total_completion, total_tokens,
        avg_prompt, avg_completion, avg_total,
        min_prompt, max_prompt,
        min_completion, max_completion,
        total_cost_usd, avg_cost_usd
    """
    if not os.path.exists(LOG_PATH):
        return {"error": "No token log found. Run the pipeline first."}

    rows = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if last_n:
        rows = rows[-last_n:]

    if not rows:
        return {"error": "Token log is empty."}

    prompt_list = [r["prompt_tokens"]     for r in rows]
    compl_list  = [r["completion_tokens"] for r in rows]
    total_list  = [r["total_tokens"]      for r in rows]
    cost_list   = [r["est_cost_usd"]      for r in rows]

    return {
        "calls":              len(rows),
        "total_prompt":       sum(prompt_list),
        "total_completion":   sum(compl_list),
        "total_tokens":       sum(total_list),
        "avg_prompt":         round(sum(prompt_list) / len(prompt_list), 1),
        "avg_completion":     round(sum(compl_list)  / len(compl_list),  1),
        "avg_total":          round(sum(total_list)  / len(total_list),  1),
        "min_prompt":         min(prompt_list),
        "max_prompt":         max(prompt_list),
        "min_completion":     min(compl_list),
        "max_completion":     max(compl_list),
        "total_cost_usd":     round(sum(cost_list), 6),
        "avg_cost_usd":       round(sum(cost_list) / len(cost_list), 6),
    }


def print_summary(last_n: int = None) -> None:
    """Pretty-print the token usage summary to stdout."""
    s = get_summary(last_n=last_n)

    if "error" in s:
        print(f"\n  [TOKEN MONITOR] {s['error']}")
        return

    label = f"last {last_n} calls" if last_n else f"all {s['calls']} calls"
    print(f"\n{'='*62}")
    print(f"  TOKEN USAGE SUMMARY  ({label})")
    print(f"{'='*62}")
    print(f"  {'Metric':<28} {'Value':>14}")
    print(f"  {'-'*42}")
    print(f"  {'Total calls':<28} {s['calls']:>14}")
    print(f"  {'Avg prompt tokens':<28} {s['avg_prompt']:>14.1f}")
    print(f"  {'Avg completion tokens':<28} {s['avg_completion']:>14.1f}")
    print(f"  {'Avg total tokens':<28} {s['avg_total']:>14.1f}")
    print(f"  {'Max prompt tokens':<28} {s['max_prompt']:>14}")
    print(f"  {'Max completion tokens':<28} {s['max_completion']:>14}")
    print(f"  {'Total tokens used':<28} {s['total_tokens']:>14,}")
    print(f"  {'Total cost (est. USD)':<28} ${s['total_cost_usd']:>13.5f}")
    print(f"  {'Avg cost per call':<28} ${s['avg_cost_usd']:>13.5f}")
    print(f"{'='*62}\n")


def get_per_candidate_table(last_n: int = None) -> list[dict]:
    """Return per-candidate token records for tabular display."""
    if not os.path.exists(LOG_PATH):
        return []
    rows = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows[-last_n:] if last_n else rows


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE REPORT  –  run directly to view the log
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rows = get_per_candidate_table()
    if not rows:
        print("No token data logged yet. Run the pipeline first.")
    else:
        print(f"\n{'='*80}")
        print(f"  PER-CALL TOKEN LOG  ({LOG_PATH})")
        print(f"{'='*80}")
        print(f"  {'#':<4} {'CANDIDATE':<28} {'PROMPT':>7} {'COMPL':>7} {'TOTAL':>7} {'COST $':>9}  TS")
        print(f"  {'-'*76}")
        for i, r in enumerate(rows, 1):
            print(
                f"  {i:<4} {str(r['candidate']):<28} "
                f"{r['prompt_tokens']:>7} "
                f"{r['completion_tokens']:>7} "
                f"{r['total_tokens']:>7} "
                f"{r['est_cost_usd']:>9.5f}  "
                f"{r['ts']}"
            )

    print_summary()
