# tests/replay_bench.py
import json
import sys
import os

# Create a mock job_id for testing
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas import CandidateFacts, JDRequirements
from app.phi4_explainer import generate_explanation
from app.dataset_manager import load_gold_dataset

def run_replay_bench():
    print("🚀 Starting Offline Replay Benchmark...")
    
    gold_data = load_gold_dataset()
    if not gold_data:
        print("⚠️ No golden dataset found. Run logic to promote entries first.")
        return

    total = len(gold_data)
    passed = 0
    failed = 0
    failures = []

    print(f"📦 Found {total} golden examples.")

    for i, entry in enumerate(gold_data):
        ctx = entry.get("input_context")
        if not ctx:
            print(f"⚠️ Skipping entry {entry['id']} (missing context)")
            continue

        try:
            # Reconstruct Objects
            facts = CandidateFacts(**ctx["candidate_facts"])
            jd = JDRequirements(**ctx["jd"])
            
            # Run Inference
            # Use 'BENCHMARK' as job_id to differentiate in ledger if we wanted
            result = generate_explanation(facts, jd, job_id=f"BENCH-{uuid.uuid4()}")
            
            if result:
                # We simply check if it produced a valid result (schema validation passed in wrapper)
                # In a real replay, we might compare Semantic Similarity with entry['output']
                # But for 'System Constraints', checking Structure & Guardrails is key.
                # Wrapper already runs guardrails. If result is None or failed, specific checks apply.
                # Currently wrapper always returns object if JSON is valid, loops error_tags.
                
                # Check for critical errors in the new run
                # We can't easily access error tags from here unless we return them from generate_explanation
                # But generate_explanation logs to DB.
                # For this script, let's assume if we got an object, it's a "Technical Pass".
                # To check Guardrails, we should ideally invoke guardrails directly.
                
                from app.guardrails import validate_explanation
                status, tags = validate_explanation(facts, jd, result)
                
                if status == "PASS":
                    passed += 1
                    print(f"✅ [{i+1}/{total}] PASS")
                else:
                    failed += 1
                    print(f"❌ [{i+1}/{total}] FAIL (Guardrails: {tags})")
                    failures.append({"id": entry["id"], "tags": tags})
            else:
                failed += 1
                print(f"❌ [{i+1}/{total}] FAIL (API/Schema Error)")
        except Exception as e:
            print(f"❌ [{i+1}/{total}] EXCEPTION: {e}")
            failed += 1

    print("\n--- Benchmark Results ---")
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    rate = (passed / total) * 100 if total > 0 else 0
    print(f"Success Rate: {rate:.1f}%")

    if failed > 0:
        print("\nFailures:")
        for f in failures:
            print(f" - ID {f['id']}: {f['tags']}")

if __name__ == "__main__":
    run_replay_bench()
