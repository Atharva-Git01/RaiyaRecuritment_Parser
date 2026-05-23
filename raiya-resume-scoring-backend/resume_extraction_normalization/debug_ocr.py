import os
import sys
import numpy as np
from pdf2image import convert_from_path
import easyocr
from PIL import Image

# Add poppler to path
os.environ["PATH"] = r"C:\poppler\poppler-24.08.0\Library\bin;" + os.environ["PATH"]

pdf_path = r"c:\Users\Gurjas Gandhi\Desktop\RAIYA_RECRUITING_SOLUTION_RESUME_SCORING\resume_extraction_normalization\resumes\Sakshi's Resume (1)-compressed - converted (3).pdf"

print(f"Testing OCR on: {os.path.basename(pdf_path)}")

try:
    # 1. Convert at higher DPI to see if it helps
    print("Converting PDF to images at 300 DPI...")
    images = convert_from_path(pdf_path, dpi=300)
    
    reader = easyocr.Reader(['en'], gpu=True)
    
    for i, img in enumerate(images):
        img_array = np.array(img)
        print(f"Page {i+1} shape: {img_array.shape}")
        
        # Test 1: Standard paragraph mode
        results = reader.readtext(img_array, detail=0, paragraph=True)
        print(f"  Standard Paragraph Mode: {len(results)} blocks")
        
        # Test 2: Standard word mode
        results_word = reader.readtext(img_array, detail=0, paragraph=False)
        print(f"  Standard Word Mode: {len(results_word)} blocks")
        
        # Test 3: High contrast adjustment
        results_contrast = reader.readtext(img_array, detail=0, paragraph=False, contrast_ths=0.1, adjust_contrast=0.7)
        print(f"  Adjusted Contrast Mode: {len(results_contrast)} blocks")

        if results_word:
            print(f"  Sample text: {results_word[:5]}")

except Exception as e:
    print(f"Error during debug: {e}")
