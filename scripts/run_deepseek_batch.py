
import os
import sys
import argparse
from pathlib import Path
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deepseek_ocr_wrapper import DeepSeekOCRWrapper

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    # target_dir = Path("sorted_resumes/testing_extractor")
    # Using absolute path for safety based on current workspace
    target_dir = Path(r"c:\Users\asr26\OneDrive\Desktop\Reaper\Work_101\RaiyaRecuritment_Parser\phi 4\sorted_resumes\testing_extractor")
    output_base_dir = target_dir / "deepseek_output"
    output_base_dir.mkdir(exist_ok=True)
    
    logger.info(f"Checking for PDFs in {target_dir}")
    
    pdf_files = list(target_dir.glob("Abhinav_Tiwari_Resume (1).pdf"))
    if not pdf_files:
        logger.warning("No PDF files found.")
        return

    try:
        logger.info("Initializing DeepSeek OCR2...")
        wrapper = DeepSeekOCRWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files. Starting extraction...")

    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        try:
            extracted_text = wrapper.extract_from_file(str(pdf_file))
            
            # Save to file
            output_file = output_base_dir / f"{pdf_file.stem}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            
            logger.info(f"   -> Saved to {output_file.name}")
            logger.info(f"   -> Extracted {len(extracted_text)} chars")
            
            # Print a snippet
            snippet = extracted_text[:200].replace('\n', ' ')
            print(f"   Snippet: {snippet}...")
            print("-" * 50)
            
        except Exception as e:
            logger.error(f"   -> Failed to extract {pdf_file.name}: {e}")

    logger.info("Batch extraction complete.")
    logger.info(f"Outputs saved to {output_base_dir}")

if __name__ == "__main__":
    main()
