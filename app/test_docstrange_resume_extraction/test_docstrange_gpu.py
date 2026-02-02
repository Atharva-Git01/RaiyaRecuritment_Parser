"""
Universal PDF Extraction Script using DocStrange with GPU OCR
==============================================================
This script processes any PDF file and extracts text content into markdown format.
Uses DocStrange's local GPU processing for OCR - no Tesseract required.

Features:
- Universal PDF extraction (text-based and image-based)
- Multi-page multi-layout handling with column-based extraction
- DocStrange GPU-accelerated OCR for image-based/scanned PDFs
- Automatic layout detection (single/multi-column)
- Proper markdown heading formatting
- Cross-platform compatibility (Windows, Linux, macOS)

Requirements:
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed
- PyTorch with CUDA support

Note: If no GPU is available, falls back to CPU processing (slower but works).
"""

import os
import re
import sys
import argparse
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Try to import required libraries with proper error handling
try:
    from docstrange import DocumentExtractor
except ImportError as e:
    logger.error("docstrange library not found. Install it with: pip install docstrange")
    sys.exit(1)

try:
    import fitz  # PyMuPDF - used for PDF analysis and layout detection
except ImportError as e:
    logger.error("PyMuPDF library not found. Install it with: pip install PyMuPDF")
    sys.exit(1)

# PIL for image handling
try:
    from PIL import Image, ImageFilter, ImageEnhance
except ImportError:
    logger.warning("Pillow not available. Install with: pip install Pillow")
    Image = None
    ImageFilter = None
    ImageEnhance = None

# Check for GPU availability
def check_gpu_availability() -> Tuple[bool, str]:
    """Check if CUDA GPU is available for processing."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            return True, f"{gpu_name} ({gpu_memory:.1f} GB)"
        else:
            return False, "No CUDA GPU available"
    except ImportError:
        return False, "PyTorch not installed - GPU detection unavailable"
    except Exception as e:
        return False, f"GPU detection error: {e}"

GPU_AVAILABLE, GPU_INFO = check_gpu_availability()

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc'}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters."""
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove the extension if present
    sanitized = os.path.splitext(sanitized)[0]
    
    return sanitized


def get_page_count(file_path: Path) -> int:
    """Get the number of pages in a PDF file."""
    try:
        doc = fitz.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def is_text_based_pdf(file_path: Path) -> bool:
    """
    Check if a PDF is text-based (has extractable text) or image-based.
    Returns True if text-based, False if image-based (needs OCR).
    """
    try:
        doc = fitz.open(str(file_path))
        total_text = 0
        pages_checked = min(3, len(doc))  # Check first 3 pages
        
        for page_num in range(pages_checked):
            page = doc[page_num]
            text = page.get_text().strip()
            total_text += len(text)
        
        doc.close()
        
        # If we have substantial text, it's text-based
        # Threshold: at least 100 chars per page on average
        return total_text > (pages_checked * 100)
    except Exception:
        return False


def detect_multi_column_layout(file_path: Path) -> bool:
    """
    Detect if a PDF has a multi-column layout (like resumes).
    Returns True if multi-column layout is detected.
    """
    try:
        doc = fitz.open(str(file_path))
        page = doc[0]  # Check first page
        
        # Get text blocks with positions
        blocks = page.get_text("dict").get("blocks", [])
        
        if not blocks:
            doc.close()
            return False
        
        # Get x-coordinates of text block starts
        x_positions = []
        for block in blocks:
            if block.get("type") == 0:  # Text block
                x_positions.append(block.get("bbox", [0])[0])
        
        if len(x_positions) < 2:
            doc.close()
            return False
        
        # Check if there's a significant gap between column positions
        x_positions.sort()
        page_width = page.rect.width
        
        # Look for gaps that indicate columns
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i-1]
            if gap > page_width * 0.2:  # 20% of page width gap
                doc.close()
                return True
        
        doc.close()
        return False
    except Exception:
        return False


def is_multi_page_multi_layout(file_path: Path) -> bool:
    """Check if PDF is multi-page with multi-column layout."""
    page_count = get_page_count(file_path)
    is_multi_column = detect_multi_column_layout(file_path)
    
    return page_count > 1 and is_multi_column


# ============================================================================
# GPU-ENABLED DOCSTRANGE OCR FUNCTIONS
# ============================================================================
def create_gpu_extractor() -> DocumentExtractor:
    """
    Create a DocumentExtractor with GPU acceleration enabled.
    Falls back to CPU if GPU is not available.
    """
    if GPU_AVAILABLE:
        print(f"    [GPU] Using GPU acceleration: {GPU_INFO}")
        try:
            # Enable GPU processing for local OCR
            extractor = DocumentExtractor(gpu=True)
            return extractor
        except Exception as e:
            print(f"    [WARNING] GPU initialization failed: {e}, falling back to CPU")
            return DocumentExtractor()
    else:
        print(f"    [CPU] GPU not available ({GPU_INFO}), using CPU processing")
        return DocumentExtractor()


def extract_text_with_docstrange_gpu(file_path: Path, extractor: DocumentExtractor = None) -> str:
    """
    Extract text from image-based PDF using DocStrange's GPU-accelerated OCR.
    
    Args:
        file_path: Path to the PDF file
        extractor: Optional DocumentExtractor instance to reuse
        
    Returns:
        Extracted text content as string
    """
    try:
        if extractor is None:
            extractor = create_gpu_extractor()
        
        print(f"    [DOCSTRANGE-GPU] Processing {file_path.name}...")
        
        # Extract using DocStrange's GPU OCR capabilities
        result = extractor.extract(str(file_path))
        
        # Get markdown output (includes OCR for image-based content)
        markdown = result.extract_markdown()
        
        if markdown and markdown.strip():
            # Clean up the extracted content
            text_content = re.sub(r'<img>.*?</img>', '', markdown, flags=re.IGNORECASE | re.DOTALL)
            text_content = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', text_content, flags=re.IGNORECASE | re.DOTALL)
            text_content = text_content.strip()
            
            print(f"    [DOCSTRANGE-GPU] Extracted {len(text_content)} characters")
            return text_content
        else:
            print("    [WARNING] DocStrange GPU returned empty content")
            return ""
            
    except Exception as e:
        print(f"    [WARNING] DocStrange GPU OCR extraction failed: {e}")
        return ""


def extract_columns_with_docstrange_gpu(file_path: Path, extractor: DocumentExtractor = None) -> Tuple[str, str]:
    """
    Extract text from left and right columns of a PDF using DocStrange's GPU OCR.
    For multi-column layouts, splits the page and uses DocStrange GPU to OCR each part.
    
    Extraction order:
    - Right column: All pages (page 1 to last)
    - Left column: All pages (page 1 to last)
    
    Args:
        file_path: Path to the PDF file
        extractor: Optional DocumentExtractor instance to reuse
        
    Returns:
        Tuple of (left_text, right_text) where each contains text from all pages
    """
    if Image is None:
        print("    [WARNING] PIL not available. Install Pillow.")
        return "", ""
    
    try:
        if extractor is None:
            extractor = create_gpu_extractor()
        
        doc = fitz.open(str(file_path))
        all_left_text = []
        all_right_text = []
        
        # Create temp directory for column images
        temp_dir = tempfile.mkdtemp(prefix="docstrange_gpu_")
        
        for page_num, page in enumerate(doc):
            print(f"    [DOCSTRANGE-GPU-COLUMN] Processing page {page_num + 1}/{len(doc)}...")
            
            try:
                # Get page dimensions
                page_rect = page.rect
                page_width = page_rect.width
                page_height = page_rect.height
                
                # Calculate appropriate zoom factor for good OCR quality
                max_page_dim = max(page_width, page_height)
                
                if max_page_dim > 5000:
                    target_dim = 2500
                    zoom = target_dim / max_page_dim
                elif max_page_dim > 1000:
                    target_dim = 3000
                    zoom = target_dim / max_page_dim
                else:
                    zoom = 2.0
                
                zoom = max(0.1, min(zoom, 4.0))
                
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                img_width = pix.width
                img_height = pix.height
                print(f"    [DOCSTRANGE-GPU-COLUMN] Image size: {img_width}x{img_height} (zoom: {zoom:.2f})")
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [img_width, img_height], pix.samples)
                
                # Calculate column split point (35% from left for sidebar)
                split_x = int(img_width * 0.35)
                
                # Extract left column (sidebar - first 35%)
                left_img = img.crop((0, 0, split_x, img_height))
                
                # Extract right column (main content - remaining 65%)
                right_img = img.crop((split_x, 0, img_width, img_height))
                
                # Save column images as temporary files
                left_path = os.path.join(temp_dir, f"page_{page_num + 1}_left.png")
                right_path = os.path.join(temp_dir, f"page_{page_num + 1}_right.png")
                
                left_img.save(left_path, "PNG")
                right_img.save(right_path, "PNG")
                
                # OCR left column with DocStrange GPU
                try:
                    left_result = extractor.extract(left_path)
                    left_markdown = left_result.extract_markdown()
                    if left_markdown:
                        left_text = re.sub(r'<img>.*?</img>', '', left_markdown, flags=re.IGNORECASE | re.DOTALL)
                        left_text = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', left_text, flags=re.IGNORECASE | re.DOTALL)
                        left_text = re.sub(r'#.*\n', '', left_text)  # Remove headers
                        left_text = re.sub(r'---', '', left_text)
                        left_text = left_text.strip()
                        if left_text:
                            all_left_text.append(left_text)
                except Exception as e:
                    print(f"    [WARNING] Left column OCR failed on page {page_num + 1}: {e}")
                
                # OCR right column with DocStrange GPU
                try:
                    right_result = extractor.extract(right_path)
                    right_markdown = right_result.extract_markdown()
                    if right_markdown:
                        right_text = re.sub(r'<img>.*?</img>', '', right_markdown, flags=re.IGNORECASE | re.DOTALL)
                        right_text = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', right_text, flags=re.IGNORECASE | re.DOTALL)
                        right_text = re.sub(r'#.*\n', '', right_text)  # Remove headers
                        right_text = re.sub(r'---', '', right_text)
                        right_text = right_text.strip()
                        if right_text:
                            all_right_text.append(right_text)
                except Exception as e:
                    print(f"    [WARNING] Right column OCR failed on page {page_num + 1}: {e}")
                
                # Clean up temp files
                try:
                    os.remove(left_path)
                    os.remove(right_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"    [WARNING] DocStrange GPU column error on page {page_num + 1}: {e}")
        
        doc.close()
        
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        left_combined = "\n\n".join(all_left_text)
        right_combined = "\n\n".join(all_right_text)
        
        print(f"    [DOCSTRANGE-GPU-COLUMN] Left column: {len(left_combined)} chars, Right column: {len(right_combined)} chars")
        
        return left_combined, right_combined
        
    except Exception as e:
        print(f"    [WARNING] DocStrange GPU column extraction failed: {e}")
        return "", ""


# ============================================================================
# CONTENT FORMATTING FUNCTIONS
# ============================================================================
def fix_markdown_formatting(text: str) -> str:
    """Fix common markdown formatting issues."""
    if not text:
        return ""
    
    # Fix common OCR errors in markdown
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix bullet points
        line = re.sub(r'^[°©®]\s*', '* ', line)
        line = re.sub(r'^[⌐░]\s*', '* ', line)
        
        # Fix dashes used as bullets
        line = re.sub(r'^[-–—]\s+', '* ', line)
        
        # Clean up extra spaces
        line = re.sub(r'\s+', ' ', line)
        
        fixed_lines.append(line.strip())
    
    return '\n'.join(fixed_lines)


def format_multicolumn_content(filename: str, right_text: str, left_text: str, method: str) -> str:
    """
    Format multi-column extracted content with proper structure:
    - Right side (main content) first, all pages
    - Left side (sidebar) second, all pages
    
    Applies proper markdown heading formatting for resume content.
    """
    # Clean up text
    right_text = right_text.strip() if right_text else ""
    left_text = left_text.strip() if left_text else ""
    
    # Apply markdown formatting fixes
    right_text = fix_markdown_formatting(right_text)
    left_text = fix_markdown_formatting(left_text)
    
    # Detect document type
    doc_type = detect_document_type(right_text + " " + left_text, filename)
    
    # Build formatted output
    output_lines = [
        f"<!-- Source: {filename} -->",
        f"<!-- Extraction Method: {method} -->",
        f"<!-- Document Type: {doc_type} -->",
        "",
        f"# {doc_type}",
        "",
    ]
    
    # Add right side content (main content - usually experience, skills, etc.)
    if right_text:
        output_lines.extend([
            "## Right Side (First till last page)",
            "",
            format_section_content(right_text),
            "",
        ])
    
    # Add left side content (sidebar - usually contact, education, etc.)
    if left_text:
        output_lines.extend([
            "## Left Side (First till last page)",
            "",
            format_section_content(left_text),
        ])
    
    return "\n".join(output_lines)


def format_section_content(text: str) -> str:
    """Format section content with proper markdown headings."""
    if not text:
        return ""
    
    lines = text.split('\n')
    formatted_lines = []
    
    # Common section headers for resumes
    section_keywords = [
        'experience', 'education', 'skills', 'contact', 'summary', 'objective',
        'projects', 'certifications', 'awards', 'languages', 'interests',
        'tools', 'personal', 'analog', 'digital', 'hobbies', 'references'
    ]
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            formatted_lines.append("")
            continue
        
        # Check if this looks like a section header
        lower_stripped = stripped.lower()
        is_section_header = any(keyword in lower_stripped for keyword in section_keywords)
        
        # Check if it's already a heading
        if stripped.startswith('#'):
            formatted_lines.append(stripped)
        elif is_section_header and len(stripped) < 50:
            # Make it a heading
            formatted_lines.append(f"### {stripped}")
        elif re.match(r'^[A-Z][A-Z\s]+$', stripped) and len(stripped) < 40:
            # All caps text - likely a header
            formatted_lines.append(f"## {stripped.title()}")
        else:
            formatted_lines.append(stripped)
    
    return '\n'.join(formatted_lines)


def detect_document_type(content: str, filename: str) -> str:
    """Detect the type of document based on content and filename."""
    content_lower = content.lower()
    filename_lower = filename.lower()
    
    # Check filename first
    if 'resume' in filename_lower or 'cv' in filename_lower:
        return "Resume"
    
    # Check content
    resume_keywords = ['experience', 'education', 'skills', 'employment', 'work history']
    resume_score = sum(1 for keyword in resume_keywords if keyword in content_lower)
    
    if resume_score >= 2:
        return "Resume"
    
    return "Untitled Document"


def format_extracted_content(filename: str, content: str, method: str) -> str:
    """Format extracted content with metadata header."""
    doc_type = detect_document_type(content, filename)
    
    output = f"""<!-- Source: {filename} -->
<!-- Extraction Method: {method} -->
<!-- Document Type: {doc_type} -->

# {doc_type}

{content}
"""
    return output


# ============================================================================
# PAGE-LEVEL EXTRACTION FUNCTIONS
# ============================================================================
def extract_columns_from_page(doc, page_num: int) -> Tuple[str, str]:
    """
    Extract text from left and right columns of a specific page.
    For text-based PDFs, uses PyMuPDF's text extraction.
    """
    try:
        page = doc[page_num]
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        
        if not blocks:
            return "", ""
        
        # Get x-coordinates of all text blocks
        x_positions = []
        block_data = []
        
        for block in blocks:
            if block.get("type") != 0:
                continue
            
            bbox = block.get("bbox", [0, 0, 0, 0])
            x0 = bbox[0]
            x_positions.append(x0)
            block_data.append((x0, block))
        
        if len(x_positions) < 2:
            # Not enough blocks for column detection
            return extract_full_text_from_page(page), ""
        
        # Sort blocks by x-coordinate
        block_data.sort(key=lambda x: x[0])
        x_positions.sort()
        
        # Find the largest gap to separate columns
        gaps = []
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i-1]
            gaps.append((gap, i))
        
        if not gaps:
            return extract_full_text_from_page(page), ""
        
        # Find the gap that separates columns
        max_gap_index = max(gaps, key=lambda x: x[0])[1]
        split_x = (x_positions[max_gap_index - 1] + x_positions[max_gap_index]) / 2
        
        left_text = []
        right_text = []
        
        for x0, block in block_data:
            block_text = []
            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                if line_text.strip():
                    block_text.append(line_text.strip())
            
            block_text_str = "\n".join(block_text)
            if x0 < split_x:
                left_text.append(block_text_str)
            else:
                right_text.append(block_text_str)
        
        return "\n".join(left_text), "\n".join(right_text)
        
    except Exception as e:
        print(f"    [WARNING] Error extracting columns from page {page_num}: {e}")
        return "", ""


def extract_full_text_from_page(page) -> str:
    """Extract full text from a page (fallback method)."""
    try:
        text = page.get_text()
        return text.strip()
    except Exception:
        return ""


def multipage_multi_layout_extraction(extractor: DocumentExtractor, file_path: Path) -> str:
    """
    Extract content from multi-page multi-layout PDF (universal for any file).
    Uses DocStrange GPU OCR for image-based PDFs.
    Dynamically detects columns and extracts text from each column.
    
    Extraction order for multi-column layouts:
    - Right column (main content): All pages first
    - Left column (sidebar): All pages second
    """
    is_text_pdf = is_text_based_pdf(file_path)
    is_multi_column = detect_multi_column_layout(file_path)
    print(f"    [PDF TYPE] {'Text-based' if is_text_pdf else 'Image-based'}, {'Multi-column' if is_multi_column else 'Single-column'}")
    
    # For image-based PDFs, use DocStrange GPU OCR column extraction
    if not is_text_pdf:
        print("    [EXTRACT] Image-based PDF detected, using DocStrange GPU OCR column extraction...")
        
        # First try direct docstrange extraction
        try:
            result = extractor.extract(str(file_path))
            markdown = result.extract_markdown()
            
            if markdown:
                text_content = re.sub(r'<img>.*?</img>', '', markdown, flags=re.IGNORECASE | re.DOTALL)
                text_content = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', text_content, flags=re.IGNORECASE | re.DOTALL)
                text_content = re.sub(r'#.*\n', '', text_content)
                text_content = re.sub(r'---', '', text_content)
                text_content = text_content.strip()
                
                if len(text_content) > 500:  # Good amount of content from docstrange
                    print("    [SUCCESS] DocStrange GPU extraction successful")
                    return format_extracted_content(file_path.name, markdown, "docstrange-gpu")
                else:
                    print(f"    [INFO] DocStrange returned only {len(text_content)} chars, trying column-based GPU OCR...")
        except Exception as e:
            print(f"    [INFO] DocStrange failed: {e}, using column-based GPU OCR...")
        
        # Use DocStrange GPU OCR for column-based extraction
        left_text, right_text = extract_columns_with_docstrange_gpu(file_path, extractor)
        
        if right_text or left_text:
            print("    [SUCCESS] DocStrange GPU column-based extraction successful")
            return format_multicolumn_content(file_path.name, right_text, left_text, "docstrange-gpu-columns")
        else:
            # Final fallback - try direct GPU OCR on whole file
            print("    [INFO] Column extraction returned empty, trying full-page GPU OCR...")
            gpu_result = extract_text_with_docstrange_gpu(file_path, extractor)
            if gpu_result and len(gpu_result.strip()) > 100:
                print("    [SUCCESS] DocStrange GPU full-page OCR successful")
                return format_extracted_content(file_path.name, gpu_result, "docstrange-gpu")
            else:
                print("    [ERROR] All GPU extraction methods failed")
                return format_extracted_content(file_path.name, "No content could be extracted. GPU OCR failed.", "extraction-failed")
    
    # For text-based PDFs, use dynamic column extraction
    print("    [EXTRACT] Using dynamic column-based extraction...")
    
    try:
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        
        all_left_columns = []
        all_right_columns = []
        
        for page_num in range(page_count):
            left_text, right_text = extract_columns_from_page(doc, page_num)
            if left_text.strip():
                all_left_columns.append(left_text)
            if right_text.strip():
                all_right_columns.append(right_text)
        
        doc.close()
        
        # Combine text from all pages for each column
        left_combined = "\n\n".join(all_left_columns)
        right_combined = "\n\n".join(all_right_columns)
        
        if right_combined or left_combined:
            print("    [SUCCESS] Column-based extraction successful")
            # Use multicolumn format: Right side first, Left side second
            return format_multicolumn_content(file_path.name, right_combined, left_combined, "column-extraction")
        else:
            print("    [WARNING] Column extraction empty, falling back to docstrange...")
            result = extractor.extract(str(file_path))
            markdown = result.extract_markdown()
            return format_extracted_content(file_path.name, markdown, "docstrange-gpu-fallback")
            
    except Exception as e:
        print(f"    [WARNING] Column extraction failed: {e}, falling back to docstrange...")
        try:
            result = extractor.extract(str(file_path))
            markdown = result.extract_markdown()
            return format_extracted_content(file_path.name, markdown, "docstrange-gpu-fallback")
        except Exception as e2:
            return format_extracted_content(file_path.name, f"Extraction failed: {e2}", "failed")


# ============================================================================
# FILE MENU AND SELECTION FUNCTIONS
# ============================================================================
def get_files_in_directory(directory: Path) -> List[Path]:
    """Get all supported files in a directory."""
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(directory.glob(f"*{ext}"))
        files.extend(directory.glob(f"*{ext.upper()}"))
    return sorted(files, key=lambda x: x.name.lower())


def display_file_menu(files: List[Path]) -> None:
    """Display a numbered menu of files."""
    print("\n" + "=" * 60)
    print("AVAILABLE FILES")
    print("=" * 60)
    for idx, file in enumerate(files, 1):
        size_kb = file.stat().st_size / 1024
        print(f"   {idx:3}. {file.name} ({size_kb:.1f} KB)")
    print("=" * 60)


def get_user_selection(max_files: int) -> List[int]:
    """Get user selection of files to process."""
    print("\nEnter file numbers to process (comma-separated, or 'all' for all files):")
    print("Example: 1,3,5 or 1-10 or all")
    
    user_input = input("> ").strip().lower()
    
    if user_input == 'all':
        return list(range(1, max_files + 1))
    
    selected = []
    parts = user_input.replace(' ', '').split(',')
    
    for part in parts:
        if '-' in part:
            try:
                start, end = part.split('-')
                selected.extend(range(int(start), int(end) + 1))
            except ValueError:
                print(f"Invalid range: {part}")
        else:
            try:
                selected.append(int(part))
            except ValueError:
                print(f"Invalid number: {part}")
    
    # Filter valid selections
    return [s for s in selected if 1 <= s <= max_files]


def is_compressed_pdf(file_path: Path) -> bool:
    """Check if a PDF is likely compressed/optimized (may need more processing)."""
    try:
        file_size_kb = file_path.stat().st_size / 1024
        page_count = get_page_count(file_path)
        if page_count > 0:
            size_per_page = file_size_kb / page_count
            # If less than 50KB per page, might be heavily compressed
            if size_per_page < 50:
                return True
    except Exception:
        pass
    
    return False


def extract_file_to_markdown(extractor: DocumentExtractor, file_path: Path, output_dir: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Extract content from any file and save as markdown.
    Uses DocStrange GPU OCR for image-based PDFs.
    For PDFs with multi-column layouts, extracts Right column (all pages) first,
    then Left column (all pages) for proper resume structure.
    """
    try:
        is_pdf = file_path.suffix.lower() == '.pdf'
        is_text_pdf = is_text_based_pdf(file_path) if is_pdf else False
        extraction_method = "docstrange-gpu"
        formatted_content = None
        
        # For image-based PDFs, use DocStrange GPU OCR
        if is_pdf and not is_text_pdf:
            print("    [INFO] Image-based PDF detected, using DocStrange GPU OCR for Right/Left column format...")
            
            # Use DocStrange GPU OCR for image-based PDFs
            left_text, right_text = extract_columns_with_docstrange_gpu(file_path, extractor)
            
            if right_text or left_text:
                print("    [SUCCESS] DocStrange GPU column-based extraction successful")
                formatted_content = format_multicolumn_content(file_path.name, right_text, left_text, "docstrange-gpu-columns")
                extraction_method = "docstrange-gpu-columns"
            else:
                print("    [WARNING] GPU column extraction returned empty, trying direct extraction...")
                try:
                    result = extractor.extract(str(file_path))
                    markdown = result.extract_markdown()
                    
                    if markdown:
                        text_content = re.sub(r'<img>.*?</img>', '', markdown, flags=re.IGNORECASE | re.DOTALL)
                        text_content = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', text_content, flags=re.IGNORECASE | re.DOTALL)
                        text_content = text_content.strip()
                        
                        if len(text_content) > 100:
                            print("    [SUCCESS] DocStrange GPU direct extraction successful")
                            formatted_content = format_extracted_content(file_path.name, markdown, "docstrange-gpu")
                except Exception as e:
                    print(f"    [INFO] DocStrange GPU failed: {e}")
        else:
            # For text-based PDFs or other files, use docstrange directly
            result = extractor.extract(str(file_path))
            markdown = result.extract_markdown()
            
            # For PDFs, check if we need GPU OCR fallback for compressed content
            if is_pdf:
                text_content = re.sub(r'<img>.*?</img>', '', markdown or '', flags=re.IGNORECASE | re.DOTALL)
                text_content = re.sub(r'&lt;img&gt;.*?&lt;/img&gt;', '', text_content, flags=re.IGNORECASE | re.DOTALL)
                text_content = re.sub(r'#.*\n', '', text_content)
                text_content = text_content.strip()
                
                is_compressed = is_compressed_pdf(file_path)
                if len(text_content) < 100 or (is_compressed and len(text_content) < 500):
                    print(f"    [INFO] DocStrange returned minimal content ({len(text_content)} chars), trying GPU column-based extraction...")
                    left_text, right_text = extract_columns_with_docstrange_gpu(file_path, extractor)
                    
                    if right_text or left_text:
                        total_ocr = len(right_text) + len(left_text)
                        if total_ocr > len(text_content):
                            print("    [SUCCESS] DocStrange GPU column-based extraction provided better extraction")
                            formatted_content = format_multicolumn_content(file_path.name, right_text, left_text, "docstrange-gpu-columns")
                            extraction_method = "docstrange-gpu-columns"
            
            if formatted_content is None:
                formatted_content = format_extracted_content(file_path.name, markdown or "", extraction_method)
        
        # If still no content, provide empty formatted content
        if formatted_content is None:
            formatted_content = format_extracted_content(file_path.name, "No content could be extracted.", "failed")
        
        # Save to file
        sanitized_name = sanitize_filename(file_path.name)
        output_filename = f"{sanitized_name}.md"
        output_path = Path(output_dir) / output_filename
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        
        return True, str(output_path), None
    
    except Exception as e:
        # If extraction fails completely, try GPU column extraction as last resort
        if file_path.suffix.lower() == '.pdf':
            print(f"    [WARNING] Extraction failed: {e}, trying GPU OCR fallback...")
            try:
                left_text, right_text = extract_columns_with_docstrange_gpu(file_path, extractor)
                
                if right_text or left_text:
                    formatted_content = format_multicolumn_content(file_path.name, right_text, left_text, "docstrange-gpu-fallback")
                    
                    sanitized_name = sanitize_filename(file_path.name)
                    output_filename = f"{sanitized_name}.md"
                    output_path = Path(output_dir) / output_filename
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(formatted_content)
                    
                    print("    [SUCCESS] DocStrange GPU fallback extraction successful")
                    return True, str(output_path), None
            except Exception as ocr_error:
                return False, None, f"Extraction: {e}, GPU fallback: {ocr_error}"
        
        return False, None, str(e)


# ============================================================================
# MAIN FUNCTION
# ============================================================================
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract content from any PDF file to markdown format using DocStrange GPU OCR",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Get script directory for default path
    script_dir = Path(__file__).parent
    default_input = script_dir / "resumes" / "prev_resume"
    
    parser.add_argument(
        "input",
        nargs="?",
        default=str(default_input),
        help=f"Input file or directory (default: {default_input})"
    )
    parser.add_argument(
        "-o", "--output",
        default="resume_extraction_gpu_output",
        help="Output directory (default: resume_extraction_gpu_output)"
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Process all files without menu selection"
    )
    return parser.parse_args()


def main():
    """Main entry point for the PDF extraction tool with GPU OCR."""
    args = parse_args()
    
    print("\n" + "=" * 60)
    print("UNIVERSAL PDF EXTRACTION TOOL (DocStrange GPU)")
    print("=" * 60)
    
    # Show GPU status
    if GPU_AVAILABLE:
        print(f"🎮 GPU Detected: {GPU_INFO}")
    else:
        print(f"⚠️  GPU Status: {GPU_INFO}")
        print("   Will use CPU processing (slower)")
    
    input_path = Path(args.input)
    output_dir = args.output
    
    print(f"Input: {input_path}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Create GPU-enabled extractor
    extractor = create_gpu_extractor()
    
    # Handle file or directory input
    if input_path.is_file():
        files = [input_path]
        selected_indices = [1]
    elif input_path.is_dir():
        files = get_files_in_directory(input_path)
        if not files:
            print(f"[ERROR] No supported files found in {input_path}")
            return
        
        print(f"\n[OK] Found {len(files)} file(s)")
        
        if args.all:
            selected_indices = list(range(1, len(files) + 1))
        else:
            display_file_menu(files)
            selected_indices = get_user_selection(len(files))
            
            if not selected_indices:
                print("[INFO] No files selected. Exiting.")
                return
    else:
        print(f"[ERROR] Input path not found: {input_path}")
        return
    
    # Process selected files
    results = {"success": [], "failed": []}
    
    print(f"\n[PROCESSING] {len(selected_indices)} file(s)...\n")
    
    for idx in selected_indices:
        file_path = files[idx - 1]
        print(f"[{idx}] Processing {file_path.name}...")
        
        success, output_path, error = extract_file_to_markdown(extractor, file_path, output_dir)
        
        if success:
            results["success"].append((file_path.name, output_path))
            print(f"    [SUCCESS] Saved to: {output_path}")
        else:
            results["failed"].append((file_path.name, error))
            print(f"    [FAILED] {error}")
        print()
    
    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"  Successful: {len(results['success'])}")
    print(f"  Failed: {len(results['failed'])}")
    print(f"  Total processed: {len(selected_indices)}")
    print(f"\nOutput files saved to: {Path(output_dir).absolute()}")
    
    if results["failed"]:
        print("\n" + "-" * 60)
        print("FAILED FILES:")
        for name, error in results["failed"]:
            print(f"  - {name}: {error}")
    
    print("-" * 60)
    print("DETAILED RESULTS:")
    print("-" * 60)
    for name, output in results["success"]:
        output_name = Path(output).name
        print(f"  [OK] {name} -> {output_name}")
    
    print("=" * 60)
    print("Extraction complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
