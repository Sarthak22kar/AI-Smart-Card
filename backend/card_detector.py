"""
Automatic Visiting Card Detection and Background Removal
=========================================================
Detects the card boundary and crops out background noise
"""

import cv2
import numpy as np
from PIL import Image
import io


def detect_and_crop_card(image_bytes: bytes) -> bytes:
    """
    Detect visiting card in image and crop out background.
    
    Process:
    1. Convert to grayscale
    2. Apply edge detection
    3. Find largest rectangular contour (the card)
    4. Perspective transform to get clean card image
    5. Return cropped card as bytes
    """
    try:
        # Load image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("  ⚠️ Card detection: Failed to decode image")
            return image_bytes
        
        original = img.copy()
        height, width = img.shape[:2]
        
        # Step 1: Preprocessing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Step 2: Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to close gaps
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Step 3: Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print("  ⚠️ Card detection: No contours found")
            return image_bytes
        
        # Sort contours by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Step 4: Find the card (largest rectangular contour)
        card_contour = None
        for contour in contours[:10]:  # Check top 10 largest contours
            area = cv2.contourArea(contour)
            
            # Card should be at least 20% of image area
            if area < (width * height * 0.2):
                continue
            
            # Approximate contour to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Card should have 4 corners (rectangle)
            if len(approx) == 4:
                card_contour = approx
                print(f"  ✅ Card detected: {len(approx)} corners, area={area:.0f}")
                break
        
        # If no perfect rectangle found, use largest contour's bounding box
        if card_contour is None:
            largest = contours[0]
            x, y, w, h = cv2.boundingRect(largest)
            
            # Check if bounding box is reasonable
            if w * h < (width * height * 0.2):
                print("  ⚠️ Card detection: Contour too small, using original")
                return image_bytes
            
            card_contour = np.array([
                [[x, y]],
                [[x + w, y]],
                [[x + w, y + h]],
                [[x, y + h]]
            ])
            print(f"  ✅ Card detected: Using bounding box {w}x{h}")
        
        # Step 5: Order points (top-left, top-right, bottom-right, bottom-left)
        pts = card_contour.reshape(4, 2)
        rect = order_points(pts)
        
        # Step 6: Perspective transform to get clean rectangular card
        (tl, tr, br, bl) = rect
        
        # Calculate width and height of card
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        
        # Ensure reasonable aspect ratio (visiting cards are typically 3.5:2 or similar)
        aspect_ratio = maxWidth / maxHeight if maxHeight > 0 else 1
        if aspect_ratio < 1:  # Card is vertical, swap dimensions
            maxWidth, maxHeight = maxHeight, maxWidth
        
        # Destination points for perspective transform
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # Compute perspective transform matrix and apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(original, M, (maxWidth, maxHeight))
        
        # Step 7: Post-processing - enhance contrast
        warped = enhance_card_image(warped)
        
        # Convert back to bytes
        _, buffer = cv2.imencode('.jpg', warped, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cropped_bytes = buffer.tobytes()
        
        print(f"  ✅ Card cropped: {maxWidth}x{maxHeight} (aspect ratio: {aspect_ratio:.2f})")
        return cropped_bytes
        
    except Exception as e:
        print(f"  ⚠️ Card detection error: {e}")
        return image_bytes


def order_points(pts):
    """
    Order points in clockwise order: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # Top-left point has smallest sum, bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # Top-right has smallest difference, bottom-left has largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect


def enhance_card_image(img):
    """
    Enhance card image for better OCR
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Merge channels
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return enhanced


def simple_crop_card(image_bytes: bytes, margin_percent: float = 0.05) -> bytes:
    """
    Simple fallback: crop margins to remove background edges
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_bytes
        
        height, width = img.shape[:2]
        
        # Calculate margins
        margin_h = int(height * margin_percent)
        margin_w = int(width * margin_percent)
        
        # Crop
        cropped = img[margin_h:height-margin_h, margin_w:width-margin_w]
        
        # Convert back to bytes
        _, buffer = cv2.imencode('.jpg', cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buffer.tobytes()
        
    except Exception as e:
        print(f"  ⚠️ Simple crop error: {e}")
        return image_bytes


def auto_rotate_card(image_bytes: bytes) -> bytes:
    """
    Detect and correct card rotation using text orientation
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_bytes
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect text orientation using moments
        # This is a simple heuristic - text lines are usually horizontal
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
        
        if lines is None:
            return image_bytes
        
        # Calculate average angle of detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            angles.append(angle)
        
        if not angles:
            return image_bytes
        
        median_angle = np.median(angles)
        
        # If card is significantly rotated, correct it
        if abs(median_angle) > 5:  # More than 5 degrees
            height, width = img.shape[:2]
            center = (width // 2, height // 2)
            
            # Rotate image
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(img, M, (width, height), 
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            
            # Convert back to bytes
            _, buffer = cv2.imencode('.jpg', rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print(f"  ✅ Card rotated: {median_angle:.1f}°")
            return buffer.tobytes()
        
        return image_bytes
        
    except Exception as e:
        print(f"  ⚠️ Auto-rotate error: {e}")
        return image_bytes


def preprocess_card_image(image_bytes: bytes, enable_detection: bool = True) -> bytes:
    """
    Main preprocessing pipeline:
    1. Detect and crop card (remove background)
    2. Auto-rotate if needed
    3. Enhance for OCR
    
    Args:
        image_bytes: Original image bytes
        enable_detection: If True, use advanced detection. If False, use simple crop.
    
    Returns:
        Preprocessed image bytes
    """
    print("  🔍 Preprocessing card image...")
    
    if enable_detection:
        # Advanced: Detect card boundary and perspective transform
        image_bytes = detect_and_crop_card(image_bytes)
    else:
        # Simple: Just crop margins
        image_bytes = simple_crop_card(image_bytes)
    
    # Auto-rotate if needed
    image_bytes = auto_rotate_card(image_bytes)
    
    return image_bytes


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python card_detector.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Load image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"Processing: {image_path}")
    print(f"Original size: {len(image_bytes)} bytes")
    
    # Process
    processed = preprocess_card_image(image_bytes, enable_detection=True)
    
    print(f"Processed size: {len(processed)} bytes")
    
    # Save result
    output_path = image_path.replace('.', '_cropped.')
    with open(output_path, 'wb') as f:
        f.write(processed)
    
    print(f"✅ Saved to: {output_path}")
