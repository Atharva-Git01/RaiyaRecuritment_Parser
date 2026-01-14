import os

import pdfplumber
from paddleocr import PaddleOCR
from tqdm import tqdm


def detect_pdf_type(pdf_path):
    """Determine whether PDF is text-based or scanned (image)."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                return "digital"
    return "scanned"


def extract_text_pdfplumber(pdf_path):
    """Extract text from digital (text-based) PDFs."""
    text_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(tqdm(pdf.pages, desc="Extracting with pdfplumber")):
            text = page.extract_text() or ""
            text_data.append(text.strip())
    return "\n".join(text_data)


def extract_text_ocr(pdf_path):
    """Extract text using PaddleOCR for scanned PDFs."""
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    pages = []
    for page_num in tqdm(range(1, 6), desc="Extracting with OCR"):  # Limit for test
        try:
            result = ocr.ocr(pdf_path, cls=True)
            text = "\n".join([line[1][0] for page in result for line in page])
            pages.append(text)
        except Exception as e:
            print(f"⚠️ OCR failed on page {page_num}: {e}")
            break
    return "\n".join(pages)


def extract_resume_text(pdf_path):
    """Main function to detect PDF type and extract text."""
    print(f"📄 Extracting from: {os.path.basename(pdf_path)}")

    pdf_type = detect_pdf_type(pdf_path)
    print(f"🔍 Detected PDF type: {pdf_type}")

    if pdf_type == "digital":
        text = extract_text_pdfplumber(pdf_path)
    else:
        text = extract_text_ocr(pdf_path)

    print(f"✅ Extraction complete ({len(text)} chars).")
    return text
