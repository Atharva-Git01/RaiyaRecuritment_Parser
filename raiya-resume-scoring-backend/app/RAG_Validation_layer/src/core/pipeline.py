import os
import sys
import traceback
import json
from typing import Tuple, Dict, List

from src.config import settings
from src.logging_config import logger

def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Pipeline Steps ---

def step1_load_inputs(jd_path: str, ai_path: str) -> Tuple[dict, dict]:
    logger.info("STEP 1: LOADING INPUTS")
    for p, label in [(jd_path, "JD file"), (ai_path, "AI scorer file")]:
        if not os.path.exists(p):
            logger.error(f"{label} not found: {p}")
            raise FileNotFoundError(p)
    jd_raw = _load_json(jd_path)
    ai_score = _load_json(ai_path)
    logger.info(f"JD loaded          : {jd_path}")
    logger.info(f"AI scorer loaded   : {ai_path}")
    return jd_raw, ai_score

def step2_normalize_jd(jd_raw: dict) -> dict:
    logger.info("STEP 2: NORMALIZING & VALIDATING JD")
    from src.validators.jd_validator import validate_jd
    validated_jd = validate_jd(jd_raw)
    _save_json(str(settings.VALIDATED_JD_PATH), validated_jd)
    logger.info(f"Validated JD saved : {settings.VALIDATED_JD_PATH}")
    return validated_jd

def step3_deterministic(validated_jd: dict, ai_score: dict) -> dict:
    logger.info("STEP 3: DETERMINISTIC SEMANTIC VALIDATION")
    from src.validators.deterministic import DeterministicValidator
    validator = DeterministicValidator(validated_jd)
    det_report = validator.validate(ai_score)
    _save_json(str(settings.DET_OUT_PATH), det_report)
    logger.info(f"Report saved       : {settings.DET_OUT_PATH}")
    return det_report

def step4_mathematical(validated_jd: dict, ai_score: dict, det_report: dict) -> dict:
    logger.info("STEP 4: MATHEMATICAL ACCURACY VALIDATION")
    from src.validators.mathematical import MathematicalValidator
    mv = MathematicalValidator(validated_jd, ai_score, det_report)
    math_report = mv.calculate_ground_truth()
    _save_json(str(settings.MATH_OUT_PATH), math_report)
    logger.info(f"Report saved       : {settings.MATH_OUT_PATH}")
    return math_report

def step5_rule_based_evidence(validated_jd: dict, ai_score: dict) -> list:
    logger.info("STEP 5: RULE-BASED EVIDENCE GENERATION")
    from src.processing.rule_based_evidence_generation import generate_rule_based_evidence, save_rule_based_evidence
    evidence_list = generate_rule_based_evidence(validated_jd, ai_score)
    save_rule_based_evidence(evidence_list, str(settings.RULE_EVD_OUT_PATH))
    logger.info(f"Report saved       : {settings.RULE_EVD_OUT_PATH}")
    return evidence_list

def step6_final_report() -> dict:
    logger.info("STEP 6: FINAL CONSOLIDATED VALIDATION REPORT")
    from src.processing.final_report import generate_final_report
    # Update: generate_final_report might need to know paths, but we rely on its internal refactoring or global settings
    generate_final_report()
    final_report = _load_json(str(settings.FINAL_OUT_PATH))
    logger.info(f"Report saved       : {settings.FINAL_OUT_PATH}")
    return final_report

def step7_historical_evidence() -> None:
    logger.info("STEP 7: HISTORICAL EVIDENCE GENERATION")
    from src.processing.evidence_generation import generate_historical_evidence
    generate_historical_evidence()
    logger.info("Historical evidence entry created successfully.")

def step8_database_update() -> None:
    logger.info("STEP 8: PINECONE DATABASE UPDATE")
    from src.retrieval.database import run_database_update
    run_database_update()
    logger.info("Vector embeddings successfully upserted to Pinecone.")

def run_pipeline(jd_path: str = None, ai_path: str = None) -> None:
    jd_path = jd_path or str(settings.DEFAULT_JD_INPUT)
    ai_path = ai_path or str(settings.DEFAULT_AI_INPUT)
    
    logger.info("=" * 60)
    logger.info("   RAG VALIDATION PIPELINE — FULL RUN")
    logger.info("=" * 60)

    try:
        jd_raw, ai_score = step1_load_inputs(jd_path, ai_path)
        validated_jd = step2_normalize_jd(jd_raw)
        det_report = step3_deterministic(validated_jd, ai_score)
        math_report = step4_mathematical(validated_jd, ai_score, det_report)
        rule_evidence = step5_rule_based_evidence(validated_jd, ai_score)
        final_report = step6_final_report()
        step7_historical_evidence()
        step8_database_update()

        logger.info("=" * 60)
        logger.info("   PIPELINE COMPLETE")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Pipeline aborted: {e}")
        logger.debug(traceback.format_exc())
        raise
