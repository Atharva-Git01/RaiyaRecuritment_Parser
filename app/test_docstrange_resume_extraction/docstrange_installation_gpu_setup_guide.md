# DocStrange GPU Installation & Setup Guide

A comprehensive guide to setting up DocStrange with GPU acceleration for PDF text extraction and OCR.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Step 1: Install NVIDIA Drivers](#step-1-install-nvidia-drivers)
4. [Step 2: Install CUDA Toolkit](#step-2-install-cuda-toolkit)
5. [Step 3: Install cuDNN](#step-3-install-cudnn)
6. [Step 4: Setup Python Environment](#step-4-setup-python-environment)
7. [Step 5: Install PyTorch with CUDA](#step-5-install-pytorch-with-cuda)
8. [Step 6: Install DocStrange & Dependencies](#step-6-install-docstrange--dependencies)
9. [Step 7: Verify Installation](#step-7-verify-installation)
10. [Step 8: Run the GPU Script](#step-8-run-the-gpu-script)
11. [Troubleshooting](#troubleshooting)
12. [Performance Optimization](#performance-optimization)

---

## System Requirements

### Target System Specifications

| Component | Specification |
|-----------|---------------|
| **CPU** | Intel Core i5 11th Gen (or equivalent AMD) |
| **GPU** | NVIDIA GeForce RTX 3060 (12GB VRAM) |
| **RAM** | 16GB+ recommended |
| **OS** | Windows 10/11 64-bit |
| **Python** | 3.10, 3.11, or 3.12 |
| **CUDA** | 11.8 or 12.1 |

### RTX 3060 GPU Specifications

| Feature | Value |
|---------|-------|
| CUDA Cores | 3584 |
| VRAM | 12GB GDDR6 |
| Compute Capability | 8.6 |
| Memory Bandwidth | 360 GB/s |
| TDP | 170W |

---

## Pre-Installation Checklist

Before starting, ensure you have:

- [ ] Administrator access to your computer
- [ ] Stable internet connection (for downloads)
- [ ] At least 20GB free disk space
- [ ] NVIDIA GPU properly installed in system
- [ ] Windows Update completed (for latest drivers)

### Verify GPU is Detected

1. Open **Device Manager** (Win + X → Device Manager)
2. Expand **Display adapters**
3. Confirm **NVIDIA GeForce RTX 3060** is listed

If not listed, check physical GPU installation and power connections.

---

## Step 1: Install NVIDIA Drivers

### Option A: Automatic (Recommended)

1. Download **GeForce Experience** from: https://www.nvidia.com/en-us/geforce/geforce-experience/
2. Install and launch GeForce Experience
3. Go to **Drivers** tab
4. Click **Check for updates**
5. Download and install the latest **Game Ready Driver**
6. Restart your computer

### Option B: Manual Installation

1. Go to: https://www.nvidia.com/Download/index.aspx
2. Select:
   - Product Type: **GeForce**
   - Product Series: **GeForce RTX 30 Series**
   - Product: **GeForce RTX 3060**
   - Operating System: **Windows 10/11 64-bit**
   - Download Type: **Game Ready Driver (GRD)**
3. Click **Search** and download the driver
4. Run the installer and follow prompts
5. Restart your computer

### Verify Driver Installation

Open Command Prompt and run:
```cmd
nvidia-smi
```

Expected output:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 537.xx       Driver Version: 537.xx       CUDA Version: 12.x    |
|-------------------------------+----------------------+----------------------+
| GPU  Name            TCC/WDDM | Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ... WDDM  | 00000000:01:00.0  On |                  N/A |
| 30%   45C    P8    20W / 170W |    500MiB / 12288MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

---

## Step 2: Install CUDA Toolkit

### Choose CUDA Version

| CUDA Version | PyTorch Support | Recommended For |
|--------------|-----------------|-----------------|
| **CUDA 11.8** | ✅ Full support | Most stable, recommended |
| **CUDA 12.1** | ✅ Full support | Latest features |

### Download CUDA Toolkit 11.8 (Recommended)

1. Go to: https://developer.nvidia.com/cuda-11-8-0-download-archive
2. Select:
   - Operating System: **Windows**
   - Architecture: **x86_64**
   - Version: **10** or **11**
   - Installer Type: **exe (local)** - recommended for offline install
3. Download the installer (~2.5 GB)

### Install CUDA Toolkit

1. Run the downloaded installer as Administrator
2. Accept the license agreement
3. Choose **Custom** installation
4. Select components:
   - ✅ **CUDA** (all sub-components)
   - ✅ **CUDA Documentation** (optional)
   - ❌ **Driver components** (uncheck if you already have latest drivers)
   - ❌ **Other components** (uncheck GeForce Experience if already installed)
5. Click **Next** and complete installation
6. Restart your computer

### Verify CUDA Installation

Open Command Prompt and run:
```cmd
nvcc --version
```

Expected output:
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2022 NVIDIA Corporation
Built on Wed_Sep_21_10:33:58_PDT_2022
Cuda compilation tools, release 11.8, V11.8.89
```

Also verify environment variables are set:
```cmd
echo %CUDA_PATH%
```

Expected output:
```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8
```

---

## Step 3: Install cuDNN

cuDNN is required for deep learning operations.

### Download cuDNN

1. Go to: https://developer.nvidia.com/cudnn
2. Click **Download cuDNN**
3. Create/Sign in to NVIDIA Developer account (free)
4. Select **cuDNN v8.9.x for CUDA 11.x** (match your CUDA version)
5. Download **cuDNN Library for Windows (x86_64)**

### Install cuDNN

1. Extract the downloaded ZIP file
2. Copy files to CUDA installation directory:

```cmd
# Copy bin files
copy "cudnn-windows-x86_64-8.9.x.x_cuda11-archive\bin\*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\"

# Copy include files
copy "cudnn-windows-x86_64-8.9.x.x_cuda11-archive\include\*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\"

# Copy lib files
copy "cudnn-windows-x86_64-8.9.x.x_cuda11-archive\lib\x64\*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\"
```

Or manually copy:
- `bin\*.dll` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\`
- `include\*.h` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\`
- `lib\x64\*.lib` → `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\`

### Verify cuDNN Installation

Check if `cudnn64_8.dll` exists in CUDA bin directory:
```cmd
dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\cudnn*.dll"
```

---

## Step 4: Setup Python Environment

### Install Python (if not already installed)

1. Download Python from: https://www.python.org/downloads/
2. Choose Python **3.10**, **3.11**, or **3.12**
3. During installation:
   - ✅ Check **Add Python to PATH**
   - ✅ Check **Install pip**
4. Complete installation

### Verify Python Installation

```cmd
python --version
pip --version
```

### Create Virtual Environment

Navigate to your project directory and create a virtual environment:

```cmd
cd C:\Users\YourUsername\Desktop\speedtechai_internship_docs

# Create virtual environment
python -m venv venv_gpu

# Activate virtual environment (Windows)
venv_gpu\Scripts\activate
```

Your prompt should now show `(venv_gpu)` prefix.

### Upgrade pip

```cmd
python -m pip install --upgrade pip
```

---

## Step 5: Install PyTorch with CUDA

**⚠️ IMPORTANT: Install PyTorch BEFORE other packages**

### For CUDA 11.8 (Recommended)

```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### For CUDA 12.1

```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Verify PyTorch CUDA Installation

```cmd
python -c "import torch; print(f'PyTorch Version: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Version: {torch.version.cuda}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected output:
```
PyTorch Version: 2.1.0+cu118
CUDA Available: True
CUDA Version: 11.8
GPU: NVIDIA GeForce RTX 3060
```

---

## Step 6: Install DocStrange & Dependencies

### Install from Requirements File

```cmd
pip install -r docstrange_gpu_requirements.txt
```

### Or Install Manually

```cmd
# Core packages
pip install docstrange
pip install PyMuPDF
pip install Pillow

# ML/OCR packages
pip install transformers
pip install accelerate
pip install safetensors

# Utility packages
pip install requests
pip install tqdm
pip install numpy

# Optional (recommended)
pip install opencv-python
```

### Verify DocStrange Installation

```cmd
python -c "from docstrange import DocumentExtractor; print('DocStrange installed successfully!')"
```

---

## Step 7: Verify Installation

### Complete Verification Script

Create a file `verify_gpu_setup.py`:

```python
"""Verify GPU setup for DocStrange."""
import sys

def check_python():
    print(f"Python Version: {sys.version}")
    return sys.version_info >= (3, 10)

def check_torch():
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA Version: {torch.version.cuda}")
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            return True
        return False
    except ImportError:
        print("PyTorch not installed!")
        return False

def check_docstrange():
    try:
        from docstrange import DocumentExtractor
        print("DocStrange: Installed ✓")
        return True
    except ImportError:
        print("DocStrange: Not installed ✗")
        return False

def check_dependencies():
    packages = ['fitz', 'PIL', 'transformers', 'numpy']
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"{pkg}: Installed ✓")
        except ImportError:
            print(f"{pkg}: Not installed ✗")

def main():
    print("=" * 50)
    print("GPU SETUP VERIFICATION")
    print("=" * 50)
    
    print("\n[1] Python Check")
    check_python()
    
    print("\n[2] PyTorch & CUDA Check")
    gpu_ok = check_torch()
    
    print("\n[3] DocStrange Check")
    doc_ok = check_docstrange()
    
    print("\n[4] Dependencies Check")
    check_dependencies()
    
    print("\n" + "=" * 50)
    if gpu_ok and doc_ok:
        print("✅ All checks passed! Ready for GPU processing.")
    else:
        print("⚠️  Some checks failed. Review the output above.")
    print("=" * 50)

if __name__ == "__main__":
    main()
```

Run the verification:
```cmd
python verify_gpu_setup.py
```

---

## Step 8: Run the GPU Script

### Basic Usage

```cmd
# Process all files in default directory
python test_docstrange_gpu.py --all

# Process specific file
python test_docstrange_gpu.py "resumes/prev_resume/SomeResume.pdf"

# Custom output directory
python test_docstrange_gpu.py -o my_output_folder --all

# Interactive file selection
python test_docstrange_gpu.py
```

### Expected Output

```
============================================================
UNIVERSAL PDF EXTRACTION TOOL (DocStrange GPU)
============================================================
🎮 GPU Detected: NVIDIA GeForce RTX 3060 (12.0 GB)
Input: resumes/prev_resume
Output Directory: resume_extraction_gpu_output

[OK] Found 50 file(s)

[PROCESSING] 1 file(s)...

[1] Processing SampleResume.pdf...
    [PDF TYPE] Image-based, Multi-column
    [EXTRACT] Image-based PDF detected, using DocStrange GPU OCR column extraction...
    [DOCSTRANGE-GPU-COLUMN] Processing page 1/2...
    [DOCSTRANGE-GPU-COLUMN] Image size: 1819x2500 (zoom: 2.00)
    [DOCSTRANGE-GPU-COLUMN] Processing page 2/2...
    [DOCSTRANGE-GPU-COLUMN] Left column: 1200 chars, Right column: 4500 chars
    [SUCCESS] DocStrange GPU column-based extraction successful
    [SUCCESS] Saved to: resume_extraction_gpu_output\SampleResume.md

============================================================
EXTRACTION SUMMARY
============================================================
  Successful: 1
  Failed: 0
  Total processed: 1
============================================================
```

---

## Troubleshooting

### Issue: "CUDA not available" in PyTorch

**Symptoms:**
```python
>>> import torch
>>> torch.cuda.is_available()
False
```

**Solutions:**

1. **Verify NVIDIA driver:**
   ```cmd
   nvidia-smi
   ```
   If this fails, reinstall NVIDIA drivers.

2. **Check CUDA Toolkit installation:**
   ```cmd
   nvcc --version
   ```
   If this fails, reinstall CUDA Toolkit.

3. **Reinstall PyTorch with correct CUDA version:**
   ```cmd
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

4. **Check PATH environment variable:**
   Ensure these are in your PATH:
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin`
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\libnvvp`

---

### Issue: "Out of memory" (OOM) Error

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**

1. **Close other GPU applications** (games, video editors, etc.)

2. **Reduce image resolution** in the script (lower zoom factor)

3. **Process smaller batches** of files

4. **Clear GPU cache:**
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

---

### Issue: "Module not found: docstrange"

**Solutions:**

1. **Ensure virtual environment is activated:**
   ```cmd
   venv_gpu\Scripts\activate
   ```

2. **Reinstall docstrange:**
   ```cmd
   pip install docstrange --upgrade
   ```

---

### Issue: Slow Performance / Using CPU Instead of GPU

**Check if GPU is being used:**
```python
import torch
print(torch.cuda.is_available())  # Should be True
print(torch.cuda.current_device())  # Should be 0
```

**Solutions:**

1. Ensure PyTorch is installed with CUDA support
2. Verify GPU drivers are up to date
3. Check if another process is using the GPU

---

## Performance Optimization

### GPU Memory Usage

The RTX 3060 has 12GB VRAM. For optimal performance:

| Operation | Estimated VRAM Usage |
|-----------|---------------------|
| Small PDF (1-2 pages) | ~2-3 GB |
| Medium PDF (5-10 pages) | ~4-6 GB |
| Large PDF (20+ pages) | ~6-10 GB |

### Tips for Best Performance

1. **Keep GPU drivers updated** - Use GeForce Experience for automatic updates

2. **Close unnecessary applications** - Free up GPU memory

3. **Use SSD for file storage** - Faster file I/O

4. **Process files in batches** - For large volumes, process 10-20 files at a time

5. **Monitor GPU usage:**
   ```cmd
   nvidia-smi -l 1  # Updates every 1 second
   ```

---

## Quick Reference Commands

```cmd
# Activate virtual environment
venv_gpu\Scripts\activate

# Check GPU status
nvidia-smi

# Check CUDA version
nvcc --version

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Run extraction script
python test_docstrange_gpu.py --all

# Deactivate virtual environment
deactivate
```

---

## Support & Resources

- **DocStrange GitHub:** https://github.com/NanoNets/docstrange
- **PyTorch Installation:** https://pytorch.org/get-started/locally/
- **CUDA Toolkit Archive:** https://developer.nvidia.com/cuda-toolkit-archive
- **cuDNN Download:** https://developer.nvidia.com/cudnn
- **NVIDIA Driver Download:** https://www.nvidia.com/Download/index.aspx

---

*Last Updated: January 2026*
*Target System: Intel i5 11th Gen + NVIDIA RTX 3060*
