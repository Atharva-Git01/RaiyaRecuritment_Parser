"""
RAIYA Resume Extraction — Streamlit GUI
=========================================
Premium interface for extracting structured JSON from resumes using 
docstrange with OCR text fallback logic.

Uses hashing for caching and pipeline traceability.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

# ── Paths & Imports ──────────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(_BASE_DIR))

try:
    from modules import Config, get_resume_files, sha256_bytes, validate_resume, ValidationReport
    from main import process_single_resume
except ImportError:
    st.error("❌ Failed to import modules. Ensure you are running from the project root.")
    st.stop()

# Load environment variables
load_dotenv(_BASE_DIR / ".env")

# Ensure directories exist
Config.ensure_directories()


# =====================================================================
# Streamlit Page Config
# =====================================================================

st.set_page_config(
    page_title="Resume Extraction — RAIYA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (RAIYA Premium) ───────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* Gradient header */
    .hero-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2.5rem 3rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 12px 40px rgba(0,0,0,0.4);
    }
    .hero-header h1 {
        color: #fff;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 0.5rem 0;
        letter-spacing: -1px;
    }
    .hero-header p {
        color: rgba(255,255,255,0.7);
        font-size: 1.1rem;
        margin: 0;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* Result Card */
    .result-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .result-card:hover {
        border-color: rgba(124, 58, 237, 0.4);
        transform: translateY(-2px);
    }

    /* Status Badges */
    .stStatus {
        font-weight: 600;
        font-size: 0.9rem;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem;
    }

    /* JSON Viewer Container */
    .json-container {
        max-height: 400px;
        overflow-y: auto;
        border-radius: 8px;
        background: #0d1117;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# Session State Initialisation
# =====================================================================

if "processing_queue" not in st.session_state:
    st.session_state.processing_queue = []
if "extraction_results" not in st.session_state:
    st.session_state.extraction_results = {}
if "running" not in st.session_state:
    st.session_state.running = False


# =====================================================================
# UI Helpers
# =====================================================================

def display_pdf(file_path: Path, height: int = 800):
    """Embed a PDF file in an iframe using base64 encoding."""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        
        # Using a data URI in an iframe
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf" style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading PDF preview: {e}")


# =====================================================================
# Header
# =====================================================================

st.markdown("""
<div class="hero-header">
    <h1>📄 Resume Extraction & Normalization</h1>
    <p>Convert unstructured resume PDFs into highly structured candidate JSON data</p>
</div>
""", unsafe_allow_html=True)


# =====================================================================
# Sidebar — Controls
# =====================================================================

with st.sidebar:
    st.markdown("### 📂 Selection")
    
    available_files = get_resume_files()
    if not available_files:
        st.warning("No resumes found in `resumes/` folder.")
        selected_files = []
    else:
        file_options = {f.name: f for f in available_files}
        selected_names = st.multiselect(
            "Select resumes to process",
            options=list(file_options.keys()),
            default=None,
            help="You can select multiple files for batch processing."
        )
        selected_files = [file_options[name] for name in selected_names]

    st.divider()
    
    st.markdown("### ⚙️ Actions")
    start_btn = st.button(
        "🚀 Start Extraction", 
        type="primary", 
        use_container_width=True,
        disabled=not selected_files or st.session_state.running
    )
    
    if start_btn:
        st.session_state.processing_queue = selected_files
        st.session_state.running = True
        st.session_state.extraction_results = {}

    st.divider()
    
    st.markdown("### 🛠️ Config Summary")
    st.caption(f"**Input:** `{Config.INPUT_DIR.relative_to(_BASE_DIR)}`")
    st.caption(f"**Output:** `{Config.OUTPUT_DIR.relative_to(_BASE_DIR)}`")
    st.caption(f"**Cache:** `{Config.HASHED_OUTPUT_DIR.relative_to(_BASE_DIR)}`")


# =====================================================================
# Main Content — Processing Logic
# =====================================================================

if st.session_state.running and st.session_state.processing_queue:
    st.markdown("### ⚡ Processing Batch")
    
    total_files = len(selected_files)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, file_path in enumerate(selected_files):
        # UI column layout for this file's status
        file_col1, file_col2 = st.columns([3, 1])
        
        with file_col1:
            st.markdown(f"**Processing:** `{file_path.name}`")
        
        # Log container for the specific file
        log_expander = st.expander("Show detailed logs", expanded=False)
        log_anchor = log_expander.empty()
        detailed_logs = []

        def ui_callback(msg: str):
            detailed_logs.append(msg)
            log_anchor.code("\n".join(detailed_logs))

        try:
            status_text.text(f"Processing {idx+1}/{total_files}: {file_path.name}...")
            
            success, result_data = process_single_resume(
                file_path, 
                Config.OUTPUT_DIR, 
                Config.HASHED_OUTPUT_DIR,
                status_callback=ui_callback
            )
            
            if success:
                st.session_state.extraction_results[file_path.name] = {
                    "status": "Success",
                    "data": result_data,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
            else:
                st.session_state.extraction_results[file_path.name] = {
                    "status": "Failed",
                    "data": result_data,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                
        except Exception as e:
            st.error(f"Critical error on {file_path.name}: {e}")
            st.session_state.extraction_results[file_path.name] = {
                "status": "Error",
                "error": str(e),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        # Update global progress
        progress_val = int((idx + 1) / total_files * 100)
        progress_bar.progress(progress_val)

    st.session_state.running = False
    st.success(f"✅ Batch processing complete! {len(st.session_state.extraction_results)} files recorded.")
    st.rerun()


# =====================================================================
# Main Content — Results Display
# =====================================================================

elif st.session_state.extraction_results:
    st.markdown("### 📊 Extraction Results")
    
    # Summary Metrics
    m1, m2, m3 = st.columns(3)
    success_count = sum(1 for r in st.session_state.extraction_results.values() if r["status"] == "Success")
    fail_count = len(st.session_state.extraction_results) - success_count
    
    m1.metric("Processed", len(st.session_state.extraction_results))
    m2.metric("Succeeded", success_count, delta=None)
    m3.metric("Failed", fail_count, delta=None, delta_color="inverse")

    st.divider()

    for filename, result in st.session_state.extraction_results.items():
        with st.container():
            st.markdown(f"""<div class="result-card">""", unsafe_allow_html=True)
            
            rc1, rc2, rc3 = st.columns([4, 2, 2])
            
            with rc1:
                st.markdown(f"#### 📄 {filename}")
                st.caption(f"Completed at: {result['timestamp']}")
            
            with rc2:
                if result["status"] == "Success":
                    st.markdown('<span class="badge-pass" style="background: linear-gradient(135deg, #059669, #10b981); color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">✅ SUCCESS</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-fail" style="background: linear-gradient(135deg, #dc2626, #ef4444); color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">❌ FAILED</span>', unsafe_allow_html=True)
            
            with rc3:
                if result["status"] == "Success":
                    json_str = json.dumps(result["data"], indent=4, ensure_ascii=False)
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_str,
                        file_name=f"{Path(filename).stem}_extracted.json",
                        mime="application/json",
                        key=f"dl_{filename}"
                    )

            if result["status"] == "Success":
                # ── Schema Validation ─────────────────────────────
                data = result["data"]
                validated_resume, v_report = validate_resume(data)

                with st.expander("🛡️ Schema Validation Report", expanded=False):
                    if validated_resume:
                        vcol1, vcol2, vcol3 = st.columns(3)
                        vcol1.metric("Fields Populated", f"{v_report.populated_fields}/{v_report.total_fields}")
                        vcol2.metric("Source Format", v_report.source_format)
                        vcol3.metric("Coerced Fields", v_report.coerced_fields)

                        if v_report.warnings:
                            for w in v_report.warnings:
                                st.warning(w, icon="⚠️")

                        # Field-level status table
                        field_rows = []
                        for fr in v_report.field_reports:
                            status_icon = {
                                "ok": "✅", "coerced": "🔄", "empty": "⬜",
                                "missing": "❌", "invalid": "🚫"
                            }.get(fr.status.value, "❓")
                            field_rows.append({
                                "Field": fr.field,
                                "Status": f"{status_icon} {fr.status.value}",
                                "Detail": fr.message
                            })
                        st.dataframe(field_rows, use_container_width=True, hide_index=True)

                        st.markdown('<span style="background: linear-gradient(135deg, #059669, #10b981); color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">🛡️ SCHEMA VALID</span>', unsafe_allow_html=True)
                    else:
                        st.error("Schema validation failed")
                        for e in v_report.errors:
                            st.error(e)

                # ── Download Validated JSON ───────────────────────
                if validated_resume:
                    validated_dict = validated_resume.model_dump(exclude_none=True)
                    validated_json_str = json.dumps(validated_dict, indent=4, ensure_ascii=False)
                    st.download_button(
                        label="🛡️ Download Validated JSON",
                        data=validated_json_str,
                        file_name=f"{Path(filename).stem}_validated.json",
                        mime="application/json",
                        key=f"dl_validated_{filename}",
                    )

                with st.expander("🔍 Preview Extracted Data"):
                    # Use validated schema for clean preview
                    if validated_resume:
                        pcol1, pcol2 = st.columns(2)
                        pcol1.markdown(f"**Name:** {validated_resume.name or 'N/A'}")
                        pcol2.markdown(f"**Email:** {validated_resume.email or 'N/A'}")
                        st.json(validated_resume.model_dump(exclude_none=True))
                    else:
                        # Fallback: show raw data
                        content = data
                        if "structured_data" in data and isinstance(data["structured_data"], dict):
                            inner = data["structured_data"]
                            if "content" in inner and isinstance(inner["content"], dict):
                                content = inner["content"]
                            else:
                                content = inner
                        pcol1, pcol2 = st.columns(2)
                        pcol1.markdown(f"**Name:** {content.get('name', 'N/A')}")
                        pcol2.markdown(f"**Email:** {content.get('email', 'N/A')}")
                        st.json(data)
                
                with st.expander("📄 View Original PDF"):
                    # Find the original file
                    orig_path = Config.INPUT_DIR / filename
                    if orig_path.exists():
                        display_pdf(orig_path, height=600)
                    else:
                        st.warning("Original source file could not be found for preview.")
            else:
                st.error(f"Error details: {result.get('error', 'Extraction yielded no data.')}")

            st.markdown("</div>", unsafe_allow_html=True)

else:
    # Empty state / Preview state
    if selected_files and not st.session_state.running:
        st.markdown(f"### 🧐 Preview: `{selected_files[0].name}`")
        if len(selected_files) > 1:
            st.caption(f"Showing first of {len(selected_files)} selected files.")
        
        display_pdf(selected_files[0], height=800)
    else:
        st.info("👈 Select resumes from the sidebar and click 'Start Extraction' to begin.")
        
        st.markdown("### 📋 How it works")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 1. Analyze & Extract")
            st.write("The system fingerprints the PDF and extracts structured data using the DocStrange engine.")
        with c2:
            st.markdown("#### 2. Validate & Normalize")
            st.write("Pydantic models strictly validate the extraction and normalize it into a clean, canonical JSON schema.")
