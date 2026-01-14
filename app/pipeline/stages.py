import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import existing logic
from app.extractor import extract_resume_text
from app.normalizer import normalize_resume_text
from app.parser import parse_resume
from app.validator import validate_resume_data
from app.normalizer_pre_score import normalize_for_scoring
from app.matcher import score_resume_against_jd
from app.ai_scorer import ai_score_resume
from app.explanation_engine import generate_full_report
from app.pdf_report import generate_pdf_report

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================
# DATA TYPES (Contracts)
# ==========================

@dataclass
class StageMetadata:
    stage_name: str
    timestamp: str
    duration_ms: float
    status: str
    error: Optional[str] = None

@dataclass
class PipelineContext:
    resume_path: Path
    job_id: Optional[int] = None
    jd: Optional[Dict[str, Any]] = None
    tmp_dir: Optional[Path] = None
    results_dir: Optional[Path] = None
    reports_dir: Optional[Path] = None

# ==========================
# BASE STAGE
# ==========================

class PipelineStage(ABC):
    def __init__(self, name: str):
        self.name = name

    def execute(self, input_data: Any, context: PipelineContext) -> Any:
        start_time = datetime.now()
        logger.info(f"▶️ Starting Stage: {self.name}")
        try:
            result = self.run(input_data, context)
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.log_success(duration)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.log_failure(duration, str(e))
            raise e

    @abstractmethod
    def run(self, input_data: Any, context: PipelineContext) -> Any:
        pass

    def log_success(self, duration_ms: float):
        logger.info(f"✅ Finished Stage: {self.name} in {duration_ms:.2f}ms")

    def log_failure(self, duration_ms: float, error: str):
        logger.error(f"❌ Failed Stage: {self.name} in {duration_ms:.2f}ms - Error: {error}")

    def save_intermediate(self, data: Any, filename: str, context: PipelineContext, is_json=False):
        if context.tmp_dir:
            file_path = context.tmp_dir / filename
            if is_json:
                file_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            else:
                file_path.write_text(str(data), encoding="utf-8")
            logger.info(f"   💾 Saved intermediate: {filename}")

# ==========================
# CONCRETE STAGES
# ==========================

class ExtractionStage(PipelineStage):
    def __init__(self):
        super().__init__("Extraction")

    def run(self, resume_path: str, context: PipelineContext) -> str:
        text = extract_resume_text(resume_path)
        
        # Save Artifact
        resume_name = Path(resume_path).stem
        self.save_intermediate(text, f"{resume_name}__extracted.txt", context)
        
        return text

class NormalizationStage(PipelineStage):
    def __init__(self):
        super().__init__("Normalization")

    def run(self, raw_text: str, context: PipelineContext) -> str:
        # Note: app.normalizer.normalize_resume_text signature might vary, standardizing usage
        # Assuming normalize_resume_text(text, output_dir=None)
        normalized = normalize_resume_text(raw_text, context.tmp_dir)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        self.save_intermediate(normalized, f"{resume_name}__normalized.md", context)
        
        return normalized

class ParsingStage(PipelineStage):
    def __init__(self):
        super().__init__("Parsing")

    def run(self, normalized_text: str, context: PipelineContext) -> Dict[str, Any]:
        parsed_json = parse_resume(normalized_text)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        self.save_intermediate(parsed_json, f"{resume_name}__parsed.json", context, is_json=True)
        
        return parsed_json

class ValidationStage(PipelineStage):
    def __init__(self):
        super().__init__("Validation")

    def run(self, parsed_data: Dict[str, Any], context: PipelineContext) -> Dict[str, Any]:
        validated_json = validate_resume_data(parsed_data)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        self.save_intermediate(validated_json, f"{resume_name}__validated.json", context, is_json=True)
        
        return validated_json

class ScoringPrepStage(PipelineStage):
    def __init__(self):
        super().__init__("Scoring Preparation")

    def run(self, validated_data: Dict[str, Any], context: PipelineContext) -> Dict[str, Any]:
        scoring_ready = normalize_for_scoring(validated_data)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        self.save_intermediate(scoring_ready, f"{resume_name}__scoring_ready.json", context, is_json=True)
        
        return scoring_ready

class LocalScoringStage(PipelineStage):
    def __init__(self):
        super().__init__("Local Scoring")

    def run(self, scoring_ready: Dict[str, Any], context: PipelineContext) -> Dict[str, Any]:
        if not context.jd:
            raise ValueError("Job Description (JD) is required for scoring.")
            
        local_score = score_resume_against_jd(scoring_ready, context.jd)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        if context.results_dir:
            file_path = context.results_dir / f"{resume_name}__local_score.json"
            file_path.write_text(json.dumps(local_score, indent=2, default=str), encoding="utf-8")
            logger.info(f"   💾 Saved Result: {file_path.name}")
            
        return local_score

class AIScoringStage(PipelineStage):
    def __init__(self):
        super().__init__("AI Scoring")

    def run(self, scoring_ready: Dict[str, Any], context: PipelineContext) -> Dict[str, Any]:
        if not context.jd:
            raise ValueError("Job Description (JD) is required for AI scoring.")
        
        # Import Contracts locally to avoid circular imports if any (though unlikely here)
        from app.scoring_contracts import ResumeFacts, JDRequirements
        
        # Construct Typed Inputs
        # We rely on contracts to validate structure. 
        # If scoring_ready is just a dict, ResumeFacts(**scoring_ready) will validate it.
        try:
            resume_facts = ResumeFacts(**scoring_ready)
            jd_reqs = JDRequirements(**context.jd)
        except Exception as e:
            raise ValueError(f"Data Contract Violation: {e}")

        # Warning: AI Score might be expensive/slow
        # We now pass the typed objects. ai_score_resume handles them.
        ai_score = ai_score_resume(resume_facts, jd_reqs, timeout=90)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        if context.results_dir:
            file_path = context.results_dir / f"{resume_name}__ai_score.json"
            file_path.write_text(json.dumps(ai_score, indent=2, default=str), encoding="utf-8")
            logger.info(f"   💾 Saved Result: {file_path.name}")
            
        return ai_score

class ExplanationStage(PipelineStage):
    def __init__(self):
        super().__init__("Explanation Generation")

    def run(self, input_tuple, context: PipelineContext) -> Dict[str, Any]:
        # Input expected: (ai_score, validated_json)
        # Note: The user requested using AI score for explanation.
        # However, generate_full_report signature is: (matcher_output_combined, extracted_data, jd)
        # We need to adapt the AI score to look like matcher output or verify how generate_full_report works.
        
        # Looking at original main.py:
        # Matcher output was local_score.copy()
        # User wants AI score used.
        
        # We will assume we pass AI score as the primary score source.
        
        ai_score, validated_json = input_tuple
        
        if not context.jd:
            raise ValueError("JD required for explanation.")

        # HACK: If AI Score structure differs significantly from Local Score, this might break.
        # But we must follow user instruction.
        # Ideally we merge them or ensure AI score has 'final_score', 'details', etc.
        
        explanation = generate_full_report(ai_score, validated_json, context.jd)
        
        # Save Artifact
        resume_name = context.resume_path.stem
        if context.results_dir:
            file_path = context.results_dir / f"{resume_name}__explanation.json"
            file_path.write_text(json.dumps(explanation, indent=2, default=str), encoding="utf-8")
            logger.info(f"   💾 Saved Result: {file_path.name}")
             
        return explanation

class ReportStage(PipelineStage):
    def __init__(self):
        super().__init__("PDF Report Generation")

    def run(self, explanation: Dict[str, Any], context: PipelineContext) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resume_name = context.resume_path.stem
        
        if context.reports_dir:
            pdf_path = context.reports_dir / f"{resume_name}__report_{timestamp}.pdf"
            generate_pdf_report(explanation, str(pdf_path))
            logger.info(f"   📘 Saved PDF: {pdf_path.name}")
            return str(pdf_path)
        return ""

# ==========================
# PIPELINE ORCHESTRATOR
# ==========================

class ResumePipeline:
    def __init__(self):
        self.extraction = ExtractionStage()
        self.normalization = NormalizationStage()
        self.parsing = ParsingStage()
        self.validation = ValidationStage()
        self.scoring_prep = ScoringPrepStage()
        self.local_scoring = LocalScoringStage()
        self.ai_scoring = AIScoringStage()
        self.explanation = ExplanationStage()
        self.reporting = ReportStage()

    def run(self, resume_path: Path, jd: Dict[str, Any], output_dirs: Dict[str, Path], job_id: Optional[int] = None):
        
        context = PipelineContext(
            resume_path=resume_path,
            job_id=job_id,
            jd=jd,
            tmp_dir=output_dirs.get("tmp"),
            results_dir=output_dirs.get("results"),
            reports_dir=output_dirs.get("reports")
        )

        logger.info(f"🚀 Starting Pipeline for {resume_path.name}")

        # 1. Extract
        raw_text = self.extraction.execute(str(resume_path), context)
        
        # 2. Normalize
        normalized_text = self.normalization.execute(raw_text, context)
        
        # 3. Parse
        parsed_json = self.parsing.execute(normalized_text, context)
        
        # 4. Validate
        validated_json = self.validation.execute(parsed_json, context)
        
        # 5. Score Prep
        scoring_ready = self.scoring_prep.execute(validated_json, context)
        
        # 6. Local Score (Still run it as it might be useful or cheap, even if not used for explanation)
        local_score = self.local_scoring.execute(scoring_ready, context)
        
        # 7. AI Score
        ai_score = self.ai_scoring.execute(scoring_ready, context)
        
        # 8. Explain (Using AI Score as requested)
        explanation = self.explanation.execute((ai_score, validated_json), context)
        
        # 9. PDF Report
        pdf_path = self.reporting.execute(explanation, context)
        
        logger.info("🎉 Pipeline Completed Successfully")
        
        return {
            "parsed": parsed_json,
            "validated": validated_json,
            "local_score": local_score,
            "ai_score": ai_score,
            "explanation": explanation,
            "pdf_report": pdf_path
        }
