import os
from app.extractor import extract_resume_text

pdf_path = r"c:\Users\asr26\OneDrive\Desktop\Reaper\work_101\My_Resume_Checker\phi 4\uploads\ResumeSuhasNikrad.pdf"

if __name__ == "__main__":
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
    else:
        print(f"Extracting text from {pdf_path}...")
        text = extract_resume_text(pdf_path)
        output_path = "storage/debug_suhas_text.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved text to {output_path}")
