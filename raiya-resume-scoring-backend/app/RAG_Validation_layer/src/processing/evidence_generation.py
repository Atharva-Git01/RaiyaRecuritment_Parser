import os
import json
import uuid
import datetime
from src.config import settings
from src.logging_config import logger

def generate_historical_evidence():
    # Use paths from settings
    evidences_dir = settings.HISTORICAL_DIR
    os.makedirs(evidences_dir, exist_ok=True)
    
    # File paths for inputs from settings
    jd_path = settings.VALIDATED_JD_PATH
    det_path = settings.DET_OUT_PATH
    math_path = settings.MATH_OUT_PATH
    fin_path = settings.FINAL_OUT_PATH
    
    # Helper to load JSON
    def load_json(p):
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    # Load input data
    jd = load_json(jd_path)
    det = load_json(det_path)
    math_val = load_json(math_path)
    fin = load_json(fin_path)
    
    # Metadata for new evidence
    now = datetime.datetime.now(datetime.timezone.utc)
    ts_str = now.strftime("%Y%m%d_%H%M%S")
    rand_hex = uuid.uuid4().hex[:8]
    evidence_id = f"EVD_{ts_str}_{rand_hex}"
    
    # Extract general details
    job_title = jd.get("job_title", "Unknown Title")
    job_id = jd.get("job_id", "Unknown ID")
    
    # 1. Build text_blob (A unified searchable text string for vectorless RAG processing)
    blob_parts = []
    blob_parts.append(f"job_title {job_title}")
    blob_parts.append(f"job_id {job_id}")
    
    if "qualification" in jd:
        blob_parts.append(f"qualification {jd['qualification']}")
    if "experience" in jd:
        blob_parts.append(f"experience {jd['experience']}")
    if "job_description" in jd:
        blob_parts.append(f"{jd['job_description']}")
        
    blob_parts.extend(jd.get('skills', []))
    blob_parts.extend(jd.get('tools', []))
    blob_parts.extend(jd.get('technologies', []))
    
    # Append structured semantic match text
    sec_results = det.get("section_results", {})
    for sec, res in sec_results.items():
        blob_parts.append(sec)
        metrics = res.get("resume_semantic_metrics")
        if metrics and metrics.get("matched_skills"):
            for m in metrics["matched_skills"]:
                jd_item = m.get('jd_item', '')
                resume_match = m.get('resume_match', '')
                blob_parts.append(f"{jd_item} {resume_match}")
                
    # Append mathematical ground truths
    gt_scores = math_val.get("ground_truth_scores", {})
    for k, v in gt_scores.items():
        blob_parts.append(f"{k} {v}")
        
    # Append final validation notes
    if fin.get("notes"):
        blob_parts.append(fin["notes"])
    
    text_blob = " ".join([str(p).strip() for p in blob_parts if str(p).strip()])
    
    # 2. Extract keywords list
    kws = set()
    for category in ['skills', 'tools', 'technologies']:
        kws.update(jd.get(category, []))
    keywords = sorted(list(kws))
    
    # 3. Compile validation metrics summary
    overall_det = det.get("overall_analytics", {})
    glob_math = math_val.get("global_metrics", {})
    
    summary = {
        "deterministic_valid": det.get("is_valid", False),
        "overall_coverage": overall_det.get("weighted_coverage", 0.0),
        "overall_token_overlap": overall_det.get("token_overlap", 0.0),
        "math_accuracy": glob_math.get("overall_accuracy", 0.0),
        "math_mae": glob_math.get("mae", 0.0),
        "math_rmse": glob_math.get("rmse", 0.0),
        "final_verdict": fin.get("final_verdict", False)
    }
    
    # 4. Construct final historical evidence object
    historical_evidence = {
        "evidence_id": evidence_id,
        "timestamp": now.isoformat(),
        "job_id": job_id,
        "job_title": job_title,
        "text_blob": text_blob,
        "keywords": keywords,
        "summary": summary,
        "raw_sources": {
            "deterministic_validator_output": det,
            "mathematical_validator_report": math_val,
            "final_validation_report": fin
        }
    }
    
    # Save the evidence to disk
    out_path = evidences_dir / f"{evidence_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(historical_evidence, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Generated Historical Evidence -> {out_path}")

if __name__ == "__main__":
    generate_historical_evidence()
