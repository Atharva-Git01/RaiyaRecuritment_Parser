import argparse
import sys
from src.core.pipeline import run_pipeline
from src.config import settings
from src.logging_config import logger

def main():
    parser = argparse.ArgumentParser(
        description="RAG Validation Pipeline — Main Orchestrator"
    )
    parser.add_argument(
        "--jd",
        help=f"Path to the raw Job Description JSON (default: {settings.DEFAULT_JD_INPUT})",
    )
    parser.add_argument(
        "--ai",
        help=f"Path to the AI scorer output JSON (default: {settings.DEFAULT_AI_INPUT})",
    )
    
    args = parser.parse_args()
    
    try:
        run_pipeline(jd_path=args.jd, ai_path=args.ai)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
