
import os
import torch
import logging
import fitz  # PyMuPDF
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # Disable DecompressionBombError for large images
from transformers import AutoModel, AutoTokenizer
from transformers import GenerationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeepSeekOCRWrapper:
    """
    Wrapper for DeepSeek-OCR-2 to handle PDF/Image text extraction.
    """
    
    def __init__(self, model_path="deepseek-ai/DeepSeek-OCR-2", device=None):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        
        # Determine device
        if device:
            self.device = device
        else:
            if torch.cuda.is_available():
                self.device = "cuda"
                # Check VRAM - RTX 2050 has 4GB, model needs 6GB+ for FP16
                # We will trust accelerate/transformers to handle offloading if needed
                # or we might need to load in 8bit if possible. 
                # For now, standard load.
            else:
                self.device = "cpu"
        
        logger.info(f"Initializing DeepSeekOCR using device: {self.device}")
        self._load_model()

    def _load_model(self):
        """Load the model and tokenizer."""
        try:
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, 
                trust_remote_code=True
            )
            
            logger.info("Loading model (this may take a while)...")
            # Using basic loading parameters. 
            # For 4GB VRAM, we might ideally want load_in_8bit=True if bitsandbytes was available/working,
            # otherwise we rely on device_map="auto" to offload to CPU riskily or just standard load if it fits.
            # Since it's 3B parameters:
            # FP32 = 12GB
            # FP16/BF16 = 6GB
            # We only have ~4GB. 
            # We will try to load with 'auto' device map to offload to CPU RAM.
            
            self.model = AutoModel.from_pretrained(
                self.model_path, 
                trust_remote_code=True,
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None 
            )
            
            if self.device == "cpu" and self.model.device.type != 'cpu':
                 self.model = self.model.to('cpu')
                 
            self.model.eval()
            logger.info("Model loaded successfully.")
            
        except Exception as e:
            logger.error(f"Failed to load DeepSeek-OCR-2 model: {e}")
            raise e

    def extract_from_file(self, file_path):
        """
        Extract text from a PDF or Image file.
        Returns: String (Markdown)
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._process_pdf(file_path)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def _process_image(self, image_path):
        """Run inference on a single image."""
        try:
            # Default prompts from README
            # document: <image>\n<|grounding|>Convert the document to markdown.
            prompt = "<image>\n<|grounding|>Convert the document to markdown."
            
            res = self.model.infer(
                self.tokenizer,
                prompt=prompt,
                image_file=image_path,
                base_size=1024,
                image_size=768,
                crop_mode=True, # Slower but better for high res
                save_results=True,
                output_path="deepseek_inference_output",
                eval_mode=False
            )
            
            # Read the result from the saved file
            result_path = os.path.join("deepseek_inference_output", "result.mmd")
            if os.path.exists(result_path):
                with open(result_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    print(f"DEBUG: Read {len(content)} chars from result.mmd")
                    return content
            print("DEBUG: result.mmd not found")
            return ""
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return ""

    def _process_pdf(self, pdf_path):
        """Convert PDF pages to images and process each."""
        full_text = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                logger.info(f"Processing page {page_num + 1}/{len(doc)}...")
                page = doc.load_page(page_num)
                
                # Convert to image
                # Zoom=2 for better resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Save temp image
                temp_img = f"temp_page_{page_num}.png"
                pix.save(temp_img)
                
                # Inference
                page_text = self._process_image(temp_img)
                full_text.append(page_text)
                
                # Cleanup
                if os.path.exists(temp_img):
                    os.remove(temp_img)
                    
            doc.close()
            return "\n\n".join(full_text)
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return ""

# Simple CLI test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        fpath = sys.argv[1]
        print(f"Testing on: {fpath}")
        wrapper = DeepSeekOCRWrapper()
        print("Extraction Result:")
        print("-" * 50)
        print(wrapper.extract_from_file(fpath))
        print("-" * 50)
    else:
        print("Usage: python deepseek_ocr_wrapper.py <path_to_file>")
