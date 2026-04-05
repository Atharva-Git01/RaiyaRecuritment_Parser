import os
import json
import time
import sys
from datetime import datetime

# Ensure we can import app modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agent_controller import AgentController, AgentState
from app.runtime_paths import get_results_dir, list_resume_files, resolve_jd_path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_batch():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    jd_path = resolve_jd_path("job_description.json")
    
    if not os.path.exists(jd_path):
        print("JD not found!")
        return

    jd_data = load_json(jd_path)

    resume_files = list_resume_files()
    
    results = []

    print(f"Starting batch processing of {len(resume_files)} resumes...\n")
    
    for r_path in resume_files:
        r_file = os.path.basename(r_path)
        if not os.path.exists(r_path):
            print(f"Skipping {r_file}: File not found.")
            continue
            
        print(f"\n{'='*20} Processing {r_file} {'='*20}")
        try:
            resume_data = load_json(r_path)
            
            # Normalize name if needed (legacy support)
            if "name" not in resume_data and "candidate_name" in resume_data:
                resume_data["name"] = resume_data["candidate_name"]
            
            # Initialize Agent
            agent = AgentController(resume_data, jd_data)
            
            # Run
            t0 = time.time()
            output = agent.run()
            t1 = time.time()
            
            # Extract Score
            final_res = output.get("result", {})
            score = final_res.get("final_score", 0)
            notes = final_res.get("notes", "No notes")

            # Extract token usage (populated by token_usage_monitor in ai_scorer.py)
            tok = output.get("token_usage") or {}
            p_tok = tok.get("prompt_tokens",     0)
            c_tok = tok.get("completion_tokens", 0)
            t_tok = tok.get("total_tokens",      p_tok + c_tok)
            
            print(f"Status : {agent.state.value}")
            print(f"Score  : {score}")
            print(f"Time   : {t1-t0:.2f}s")
            if t_tok:
                print(f"Tokens : prompt={p_tok}  completion={c_tok}  total={t_tok}")
            else:
                print(f"Tokens : (not available — check Azure response includes 'usage' field)")
            
            # Save individual result
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_name = f"score_{r_file.replace('.json', '')}_{timestamp}.json"
            out_path = os.path.join(get_results_dir(), out_name)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=4)
            print(f"Saved  : {out_name}")
                
            results.append({
                "file":   r_file,
                "name":   resume_data.get("name", "Unknown"),
                "score":  score,
                "notes":  notes,
                "status": agent.state.value,
                "prompt_tokens":     p_tok,
                "completion_tokens": c_tok,
                "total_tokens":      t_tok,
            })
            
        except Exception as e:
            print(f"ERROR processing {r_file}: {e}")
            results.append({
                "file": r_file,
                "name": "ERROR",
                "score": 0,
                "error": str(e),
                "status": "ERROR"
            })
        print(f"{'-'*60}")

    # ─── Summary Table ─────────────────────────────────────────────────────
    total_p = sum(r.get("prompt_tokens",     0) for r in results)
    total_c = sum(r.get("completion_tokens", 0) for r in results)
    total_t = sum(r.get("total_tokens",      0) for r in results)

    print("\n" + "="*76)
    print(f"  {'CANDIDATE':<24} | {'SCORE':>5} | {'STATUS':<11} | {'PROMPT':>7} | {'COMPL':>6} | {'TOTAL':>7}")
    print("-" * 76)
    for res in results:
        name   = res.get("name",   "Unknown")[:23]
        score  = res.get("score",  0)
        status = res.get("status", "ERROR")
        pt     = res.get("prompt_tokens",     0)
        ct     = res.get("completion_tokens", 0)
        tt     = res.get("total_tokens",      0)
        tok_str = f"{pt:>7} | {ct:>6} | {tt:>7}" if tt else f"{'N/A':>7} | {'N/A':>6} | {'N/A':>7}"
        print(f"  {name:<24} | {score:>5} | {status:<11} | {tok_str}")
    print("-" * 76)
    if total_t:
        print(f"  {'TOTAL TOKENS':<24} | {'':>5} | {'':>11} | {total_p:>7} | {total_c:>6} | {total_t:>7}")
        print(f"  {'AVG PER RESUME':<24} | {'':>5} | {'':>11} | {total_p//max(1,len(results)):>7} | {total_c//max(1,len(results)):>6} | {total_t//max(1,len(results)):>7}")
    print("=" * 76)

if __name__ == "__main__":
    run_batch()
