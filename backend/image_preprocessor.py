"""
Image Preprocessing Layer  v3  –  Speed-optimised
===================================================
Two modes:

  fast_preprocess(image_bytes)   → bytes
    For Gemini: lightweight pipeline (~0.1s per image)
    Steps: EXIF fix → resize → CLAHE contrast → sharpen
    Gemini is smart enough to handle backgrounds/shadows itself.

  full_preprocess(image_bytes)   → bytes
    For EasyOCR/Tesseract fallback: heavier pipeline (~0.8s)
    Steps: EXIF fix → resize → contour crop → shadow removal
           → CLAHE → sharpen → adaptive threshold if low-contrast

Both have per-step try/except so a failure never breaks the pipeline.
"""

import io
import cv2
import numpy as np
from PIL import Image, ImageOps

JPEG_QUALITY = 92


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(image_bytes: bytes) -> np.ndarray:
    """Decode bytes → BGR ndarray, fix EXIF rotation."""
    pil = Image.open(io.BytesIO(image_bytes))
    try:
        pil = ImageOps.exif_transpose(pil)
    except Exception:
        pass
    if pil.mode not in ('RGB', 'RGBA'):
        pil = pil.convert('RGB')
    elif pil.mode == 'RGBA':
        pil = pil.convert('RGB')
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _encode(img: np.ndarray) -> bytes:
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes()


def _resize(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img
    scale = max_side / max(h, w)
    return cv2.resize(img, (int(w * scale), int(h * scale)),
                      interpolation=cv2.INTER_AREA)


def _clahe(img: np.ndarray) -> np.ndarray:
    """CLAHE contrast enhancement on LAB L-channel."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def _sharpen(img: np.ndarray) -> np.ndarray:
    """Unsharp mask — sharpens text edges."""
    blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=1.5)
    return cv2.addWeighted(img, 1.4, blurred, -0.4, 0)


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype='float32')
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect


def _contour_crop(img: np.ndarray) -> np.ndarray:
    """
    Find the largest rectangular contour (the card) and crop to it.
    Falls back to a small margin crop if no rectangle found.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 5, 50, 50)
    edges = cv2.Canny(blurred, 30, 120)
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img

    h, w = img.shape[:2]
    min_area = h * w * 0.15
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours[:5]:
        if cv2.contourArea(cnt) < min_area:
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype('float32')
            rect = _order_points(pts)
            tl, tr, br, bl = rect
            dst_w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
            dst_h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
            if dst_w < 50 or dst_h < 50:
                continue
            if dst_h > dst_w:
                dst_w, dst_h = dst_h, dst_w
            dst_pts = np.array([[0, 0], [dst_w-1, 0],
                                 [dst_w-1, dst_h-1], [0, dst_h-1]],
                                dtype='float32')
            M = cv2.getPerspectiveTransform(rect, dst_pts)
            return cv2.warpPerspective(img, M, (dst_w, dst_h))

    # Fallback: small margin crop
    mh, mw = int(h * 0.03), int(w * 0.03)
    cropped = img[mh:h-mh, mw:w-mw]
    return cropped if cropped.size > 0 else img


def _shadow_removal(img: np.ndarray) -> np.ndarray:
    """Divide each channel by its blurred self to normalise illumination."""
    result = np.zeros_like(img, dtype=np.float32)
    for i in range(3):
        ch = img[:, :, i].astype(np.float32)
        bg = cv2.GaussianBlur(ch, (0, 0), sigmaX=40)
        result[:, :, i] = cv2.divide(ch, bg, scale=255.0)
    return np.clip(result, 0, 255).astype(np.uint8)


def _is_low_contrast(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(np.std(gray)) < 40.0


def _adaptive_threshold(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=15, C=8
    )
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


# ── Public API ────────────────────────────────────────────────────────────────

def fast_preprocess(image_bytes: bytes) -> bytes:
    """
    Lightweight preprocessing for Gemini (~0.1s).
    Handles: normal cards, dark cards, colored cards, low-contrast cards.

    Key insight: Gemini is smart — we just need to give it a readable image.
    Don't over-process. Fix brightness, rotate, resize. That's it.
    """
    try:
        img = _load(image_bytes)
    except Exception:
        return image_bytes

    try:
        img = _resize(img, max_side=1400)
    except Exception:
        pass

    # Auto-rotate portrait images (visiting cards are landscape)
    try:
        h, w = img.shape[:2]
        if h > w * 1.2:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    except Exception:
        pass

    # Analyze image brightness
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(gray.mean())
        std_brightness  = float(gray.std())

        if mean_brightness < 60:
            # Very dark image — aggressive brightness boost
            # Use gamma correction (better than linear for dark images)
            gamma = 0.4  # < 1 brightens the image
            lut = np.array([
                min(255, int(((i / 255.0) ** gamma) * 255))
                for i in range(256)
            ], dtype=np.uint8)
            img = cv2.LUT(img, lut)
            print(f"  🔆 Very dark image corrected (brightness={mean_brightness:.0f})")

        elif mean_brightness < 100 and std_brightness < 50:
            # Dark AND low contrast — boost + CLAHE
            img = cv2.convertScaleAbs(img, alpha=1.8, beta=20)
            img = _clahe(img)
            print(f"  🔆 Dark low-contrast image corrected (brightness={mean_brightness:.0f})")

        else:
            # Normal image — just CLAHE for contrast enhancement
            img = _clahe(img)

    except Exception:
        try:
            img = _clahe(img)
        except Exception:
            pass

    try:
        img = _sharpen(img)
    except Exception:
        pass

    return _encode(img)


def full_preprocess(image_bytes: bytes) -> bytes:
    """
    Full preprocessing for EasyOCR/Tesseract fallback (~0.8s).
    These engines need cleaner images than Gemini.

    Steps: EXIF fix → resize to 1200px → contour crop
           → shadow removal → CLAHE → sharpen
           → adaptive threshold (only if low-contrast)
    """
    try:
        img = _load(image_bytes)
    except Exception:
        return image_bytes

    try:
        img = _resize(img, max_side=1200)
    except Exception:
        pass

    try:
        img = _contour_crop(img)
    except Exception:
        pass

    try:
        img = _shadow_removal(img)
    except Exception:
        pass

    try:
        img = _clahe(img)
    except Exception:
        pass

    try:
        img = _sharpen(img)
    except Exception:
        pass

    try:
        if _is_low_contrast(img):
            img = _adaptive_threshold(img)
    except Exception:
        pass

    return _encode(img)


# Keep old name as alias for backward compatibility
def preprocess_image(image_bytes: bytes, verbose: bool = False) -> bytes:
    """Alias for full_preprocess (backward compatibility)."""
    return full_preprocess(image_bytes)
