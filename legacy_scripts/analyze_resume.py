
import os
import sys
import json
from pathlib import Path
from app.extractor import extract_resume_text
from app.parser import parse_resume
from app.normalizer import normalize_resume_text

# Configure console encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

resume_path = Path("uploads/ResumePriyankaAgarwal.pdf")
log_path = Path("resume_analysis.log")

def log_msg(msg):
    print(msg)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# Initialize log
with open(log_path, "w", encoding="utf-8") as f:
    f.write(f"Analyzing {resume_path}\n")

print(f"📄 Analyzing: {resume_path}")

if not resume_path.exists():
    log_msg("❌ File not found!")
    sys.exit(1)

# 1. File Size
size_bytes = resume_path.stat().st_size
log_msg(f"📊 File Size: {size_bytes / 1024:.2f} KB")

# 2. Extract Text
try:
    log_msg("⏳ Extracting text...")
    text = extract_resume_text(str(resume_path))
    log_msg(f"✅ Text extraction successful. Length: {len(text)} chars")
    
    char_count = len(text)
    word_count = len(text.split())
    
    log_msg(f"📝 Character Count: {char_count}")
    log_msg(f"📝 Word Count: {word_count}")
    log_msg("-" * 40)
    log_msg("🔎 First 500 characters:")
    log_msg(text[:500])
    log_msg("-" * 40)
    
    # 3. Parsing
    log_msg("⏳ Parsing resume...")
    normalized_text = normalize_resume_text(text)
    parsed_data = parse_resume(normalized_text)
    
    json_str = json.dumps(parsed_data, ensure_ascii=False)
    json_len = len(json_str)
    
    log_msg(f"📦 Parsed JSON Size: {json_len} chars ({json_len/1024:.2f} KB)")
    
    if json_len > 100000:
        log_msg("⚠️ WARNING: JSON payload is very large! This might cause AI timeout.")
    else:
        log_msg("✅ JSON payload size is reasonable.")
        
except Exception as e:
    log_msg(f"❌ Analysis failed: {e}")
