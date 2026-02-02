import os
import logging
import pdfplumber
from tqdm import tqdm

# Import the new wrapper
try:
    from app.deepseek_ocr_wrapper import DeepSeekOCRWrapper
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
    print("⚠️ DeepSeekOCRWrapper not found or failed to import.")

# Lazy loader for the model
_DEEPSEEK_INSTANCE = None

def get_deepseek_instance():
    global _DEEPSEEK_INSTANCE
    if _DEEPSEEK_INSTANCE is None:
        print("🤖 Initializing DeepSeek-OCR-2 Model (Lazy Load)...")
        _DEEPSEEK_INSTANCE = DeepSeekOCRWrapper()
    return _DEEPSEEK_INSTANCE

def detect_pdf_type(pdf_path):
    """Determine whether PDF is text-based or scanned (image)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return "scanned"
            
            # Check first few pages
            total_text_len = 0
            pages_to_check = min(3, len(pdf.pages))
            
            for i in range(pages_to_check):
                text = pdf.pages[i].extract_text()
                if text:
                    total_text_len += len(text.strip())
            
            # Heuristic: if very little text, treat as scanned
            if total_text_len < 50: 
                return "scanned"
                
            return "digital"
    except Exception as e:
        print(f"⚠️ Error detecting PDF type: {e}")
        return "scanned"

def extract_text_pdfplumber(pdf_path):
    """Extract text from digital (text-based) PDFs."""
    text_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(tqdm(pdf.pages, desc="Extracting with pdfplumber")):
                text = page.extract_text() or ""
                text_data.append(text.strip())
        return "\n".join(text_data)
    except Exception as e:
        print(f"⚠️ pdfplumber extraction failed: {e}")
        return ""

def extract_text_deepseek(pdf_path):
    """Extract text using DeepSeek-OCR-2."""
    if not DEEPSEEK_AVAILABLE:
        return "DeepSeek OCR not available."
    
    try:
        extractor = get_deepseek_instance()
        return extractor.extract_from_file(pdf_path)
    except Exception as e:
        print(f"⚠️ DeepSeek extraction failed: {e}")
        return ""

def extract_resume_text(pdf_path):
    """
    Main function to detect PDF type and extract text.
    Strategies:
    1. Detect if digital. If digital => pdfplumber (Fast, usually accurate for simple docs).
    2. If scanned or pdfplumber fails => DeepSeek OCR 2 (Slower, handles complex layout/scans).
    """
    print(f"📄 Extracting from: {os.path.basename(pdf_path)}")

    pdf_type = detect_pdf_type(pdf_path)
    print(f"🔍 Detected PDF type: {pdf_type}")

    text = ""
    
    if pdf_type == "digital":
        print("⚡ Using fast extraction (pdfplumber)...")
        text = extract_text_pdfplumber(pdf_path)
        
        # Validation: If extracted text is garbage or empty, fallback
        if len(text.strip()) < 50:
             print("⚠️ extracted text too short, falling back to DeepSeek OCR...")
             pdf_type = "scanned" # Force fallback
    
    if pdf_type == "scanned" or not text.strip():
        if DEEPSEEK_AVAILABLE:
            print("👁️ Using Intelligent extraction (DeepSeek-OCR-2)...")
            text = extract_text_deepseek(pdf_path)
        else:
             print("❌ Scanned document detected but DeepSeek OCR is not available.")
             # Fallback to legacy OCR if needed, or return empty
             # For now, we assume DeepSeek IS the OCR engine.

    print(f"✅ Extraction complete ({len(text)} chars).")
    return text
