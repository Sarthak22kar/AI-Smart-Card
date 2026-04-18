"""
Multi-Engine OCR for Visiting Cards  –  Fallback engines
==========================================================
EasyOCR and Tesseract are used only when Gemini is unavailable.
The main pipeline in main.py handles preprocessing and orchestration.
"""

import os, io, time
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps
from concurrent.futures import ThreadPoolExecutor

from gemini_ocr import gemini_ocr, GEMINI_API_KEY

# ── EasyOCR (lazy loaded) ─────────────────────────────────────────────────────
_easyocr_reader = None
EASYOCR_LOADED = False

def load_easyocr():
    """Load EasyOCR reader once"""
    global _easyocr_reader, EASYOCR_LOADED
    if EASYOCR_LOADED:
        return True
    try:
        import easyocr
        print("  Loading EasyOCR...")
        t0 = time.time()
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print(f"  ✅ EasyOCR loaded in {round(time.time()-t0,2)}s")
        EASYOCR_LOADED = True
        return True
    except Exception as e:
        print(f"  ⚠️ EasyOCR not available: {e}")
        return False

# ── Tesseract path ────────────────────────────────────────────────────────────
for _p in ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/usr/bin/tesseract"]:
    if os.path.exists(_p):
        pytesseract.pytesseract.tesseract_cmd = _p
        break

TESSERACT_CONFIG = r'--oem 3 --psm 6'


# ── Image utilities ───────────────────────────────────────────────────────────

def load_pil(image_bytes: bytes) -> Image.Image:
    pil = Image.open(io.BytesIO(image_bytes))
    try:
        pil = ImageOps.exif_transpose(pil)
    except Exception:
        pass
    if pil.mode not in ('RGB', 'L'):
        pil = pil.convert('RGB')
    return pil


def resize_pil(pil: Image.Image, max_w: int = 1200) -> Image.Image:
    if pil.width > max_w:
        ratio = max_w / pil.width
        # LANCZOS replaces ANTIALIAS in Pillow 10+
        pil = pil.resize((max_w, int(pil.height * ratio)), Image.LANCZOS)
    return pil


def pil_to_bgr(pil: Image.Image) -> np.ndarray:
    arr = np.array(pil.convert('RGB'))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


# ── EasyOCR Scene Text Recognition ────────────────────────────────────────────

def easyocr_extract(image_bytes: bytes) -> str:
    """Extract text using EasyOCR - production quality"""
    if not load_easyocr():
        return ''
    
    try:
        # Load image with good resolution
        pil = load_pil(image_bytes)
        pil = resize_pil(pil, 1200)  # Good balance
        
        img_array = np.array(pil)
        detections = _easyocr_reader.readtext(img_array)
        
        texts = []
        for (bbox, text, conf) in detections:
            if conf > 0.4:  # Balanced confidence
                text = text.strip()
                if len(text) >= 2:
                    # Filter obvious garbage
                    alpha_count = sum(c.isalpha() or c.isdigit() for c in text)
                    if alpha_count >= len(text) * 0.3:  # At least 30% alphanumeric
                        texts.append(text)
        
        return '\n'.join(texts)
    except Exception as e:
        print(f"  EasyOCR error: {e}")
        return ''


def tesseract_extract(image_bytes: bytes) -> str:
    """Extract text using Tesseract with rotation handling."""
    try:
        pil = load_pil(image_bytes)
        pil = resize_pil(pil, 1200)

        # Auto-rotate portrait images (visiting cards are landscape)
        if pil.height > pil.width * 1.2:
            pil = pil.rotate(90, expand=True)

        bgr = pil_to_bgr(pil)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)

        # Try multiple PSM modes and pick the best result
        best_text = ''
        for psm in [6, 3, 4]:
            config = f'--oem 3 --psm {psm}'
            try:
                text = pytesseract.image_to_string(enhanced, config=config).strip()
                if len(text) > len(best_text):
                    best_text = text
            except Exception:
                continue

        return best_text if best_text else ''
    except Exception as e:
        print(f"  Tesseract error: {e}")
        return ''


# ── Main OCR Function ─────────────────────────────────────────────────────────

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Fallback OCR: EasyOCR → Tesseract.
    Called only when Gemini is unavailable.
    Image should already be preprocessed before calling this.
    """
    t0 = time.time()

    # 1. Try EasyOCR
    try:
        text = easyocr_extract(image_bytes)
        if text and len(text.strip()) > 10:
            print(f"  ✅ EasyOCR ({round(time.time()-t0,2)}s)")
            return text
    except Exception as e:
        print(f"  ⚠️ EasyOCR error: {str(e)[:50]}")

    # 2. Fallback to Tesseract
    try:
        text = tesseract_extract(image_bytes)
        if text and len(text.strip()) > 10:
            print(f"  ✅ Tesseract ({round(time.time()-t0,2)}s)")
            return text
    except Exception as e:
        print(f"  ⚠️ Tesseract error: {str(e)[:50]}")

    print(f"  ❌ All OCR engines failed ({round(time.time()-t0,2)}s)")
    return ''


# ── Parallel processing (used by fallback path) ───────────────────────────────

_executor = ThreadPoolExecutor(max_workers=2)


def extract_both_images(front_bytes: bytes, back_bytes: bytes) -> tuple:
    """Process both images in parallel using fallback OCR."""
    t0 = time.time()
    f = _executor.submit(extract_text_from_image, front_bytes)
    b = _executor.submit(extract_text_from_image, back_bytes)
    ft, bt = f.result(), b.result()
    print(f"  ⚡ Total OCR: {round(time.time()-t0, 2)}s")
    return ft, bt
