"""
Configuration for AI Smart Visiting Card System
"""

import os

# ── Card Detection Settings ──────────────────────────────────────────────────

# Enable automatic card detection and background removal
# Set to False if you want to process images as-is
ENABLE_CARD_DETECTION = os.environ.get('ENABLE_CARD_DETECTION', 'true').lower() == 'true'

# Card detection method: 'advanced' or 'simple'
# - 'advanced': Uses contour detection and perspective transform (best quality)
# - 'simple': Just crops margins (faster but less accurate)
CARD_DETECTION_METHOD = os.environ.get('CARD_DETECTION_METHOD', 'advanced')

# Minimum card area as percentage of image (0.0 to 1.0)
# Cards smaller than this will be rejected
MIN_CARD_AREA_PERCENT = float(os.environ.get('MIN_CARD_AREA_PERCENT', '0.2'))

# Simple crop margin percentage (used when method='simple')
SIMPLE_CROP_MARGIN = float(os.environ.get('SIMPLE_CROP_MARGIN', '0.05'))

# Auto-rotate cards based on text orientation
ENABLE_AUTO_ROTATE = os.environ.get('ENABLE_AUTO_ROTATE', 'true').lower() == 'true'

# ── Image Preprocessing Settings ──────────────────────────────────────────────

# Enable advanced image preprocessing (background removal, denoising, enhancement)
ENABLE_ADVANCED_PREPROCESSING = os.environ.get('ENABLE_ADVANCED_PREPROCESSING', 'true').lower() == 'true'

# Enable shadow removal
ENABLE_SHADOW_REMOVAL = os.environ.get('ENABLE_SHADOW_REMOVAL', 'true').lower() == 'true'

# Enable denoising
ENABLE_DENOISING = os.environ.get('ENABLE_DENOISING', 'true').lower() == 'true'

# Enable sharpening
ENABLE_SHARPENING = os.environ.get('ENABLE_SHARPENING', 'true').lower() == 'true'

# Enable adaptive thresholding for low contrast images
ENABLE_ADAPTIVE_THRESHOLD = os.environ.get('ENABLE_ADAPTIVE_THRESHOLD', 'true').lower() == 'true'

# ── OCR Settings ──────────────────────────────────────────────────────────────

# OCR engine priority (comma-separated)
# Options: google_vision, easyocr, tesseract
OCR_ENGINE_PRIORITY = os.environ.get('OCR_ENGINE_PRIORITY', 'google_vision,easyocr,tesseract')

# Maximum image resolution for OCR (pixels)
MAX_OCR_RESOLUTION = int(os.environ.get('MAX_OCR_RESOLUTION', '1200'))

# EasyOCR confidence threshold (0.0 to 1.0)
EASYOCR_CONFIDENCE = float(os.environ.get('EASYOCR_CONFIDENCE', '0.4'))

# ── Extraction Settings ───────────────────────────────────────────────────────

# Minimum extraction confidence to save contact (0.0 to 1.0)
MIN_EXTRACTION_CONFIDENCE = float(os.environ.get('MIN_EXTRACTION_CONFIDENCE', '0.3'))

# Enable spaCy NER for name extraction (requires spacy model installed)
ENABLE_SPACY_NER = os.environ.get('ENABLE_SPACY_NER', 'true').lower() == 'true'

# ── Validation Settings ───────────────────────────────────────────────────────

# Enable field validation (phone, email, name, etc.)
ENABLE_FIELD_VALIDATION = os.environ.get('ENABLE_FIELD_VALIDATION', 'true').lower() == 'true'

# Strict validation mode (reject invalid fields vs. try to clean them)
STRICT_VALIDATION_MODE = os.environ.get('STRICT_VALIDATION_MODE', 'false').lower() == 'true'

# Minimum phone digits (Indian mobile: 10)
MIN_PHONE_DIGITS = int(os.environ.get('MIN_PHONE_DIGITS', '10'))

# Maximum phone digits (with country code: 12)
MAX_PHONE_DIGITS = int(os.environ.get('MAX_PHONE_DIGITS', '12'))

# Require valid email domain
REQUIRE_VALID_EMAIL_DOMAIN = os.environ.get('REQUIRE_VALID_EMAIL_DOMAIN', 'false').lower() == 'true'

# Minimum name words
MIN_NAME_WORDS = int(os.environ.get('MIN_NAME_WORDS', '2'))

# Maximum name words
MAX_NAME_WORDS = int(os.environ.get('MAX_NAME_WORDS', '5'))

# ── Debug Settings ────────────────────────────────────────────────────────────

# Save preprocessed images for debugging
SAVE_DEBUG_IMAGES = os.environ.get('SAVE_DEBUG_IMAGES', 'false').lower() == 'true'

# Debug image output directory
DEBUG_IMAGE_DIR = os.environ.get('DEBUG_IMAGE_DIR', 'debug_images')

# Verbose logging
VERBOSE_LOGGING = os.environ.get('VERBOSE_LOGGING', 'true').lower() == 'true'


def print_config():
    """Print current configuration"""
    print("\n" + "="*70)
    print("AI SMART VISITING CARD - CONFIGURATION")
    print("="*70)
    print("\n📸 Card Detection:")
    print(f"  Enabled:              {ENABLE_CARD_DETECTION}")
    print(f"  Method:               {CARD_DETECTION_METHOD}")
    print(f"  Min card area:        {MIN_CARD_AREA_PERCENT:.0%}")
    print(f"  Auto-rotate:          {ENABLE_AUTO_ROTATE}")
    
    print("\n🎨 Image Preprocessing:")
    print(f"  Advanced preprocessing: {ENABLE_ADVANCED_PREPROCESSING}")
    print(f"  Shadow removal:       {ENABLE_SHADOW_REMOVAL}")
    print(f"  Denoising:            {ENABLE_DENOISING}")
    print(f"  Sharpening:           {ENABLE_SHARPENING}")
    print(f"  Adaptive threshold:   {ENABLE_ADAPTIVE_THRESHOLD}")
    
    print("\n🔍 OCR:")
    print(f"  Engine priority:      {OCR_ENGINE_PRIORITY}")
    print(f"  Max resolution:       {MAX_OCR_RESOLUTION}px")
    print(f"  EasyOCR confidence:   {EASYOCR_CONFIDENCE:.0%}")
    
    print("\n📝 Extraction:")
    print(f"  Min confidence:       {MIN_EXTRACTION_CONFIDENCE:.0%}")
    print(f"  spaCy NER:            {ENABLE_SPACY_NER}")
    
    print("\n✅ Validation:")
    print(f"  Enabled:              {ENABLE_FIELD_VALIDATION}")
    print(f"  Strict mode:          {STRICT_VALIDATION_MODE}")
    print(f"  Phone digits:         {MIN_PHONE_DIGITS}-{MAX_PHONE_DIGITS}")
    print(f"  Name words:           {MIN_NAME_WORDS}-{MAX_NAME_WORDS}")
    
    print("\n🐛 Debug:")
    print(f"  Save debug images:    {SAVE_DEBUG_IMAGES}")
    print(f"  Verbose logging:      {VERBOSE_LOGGING}")
    print("="*70 + "\n")


if __name__ == '__main__':
    print_config()
