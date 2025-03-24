# scripts/preprocess.py

import cv2
import numpy as np
import os
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

def preprocess_document(page_image, page_num):
    """
    Enhanced preprocessing specifically for historical table documents.
    
    Args:
        page_image: PIL Image or NumPy array representing the page.
        page_num: The page number (used for saving if needed).
    
    Returns:
        Preprocessed image ready for OCR.
    """
    # Convert PIL Image to NumPy array if necessary
    if not isinstance(page_image, (np.ndarray, np.generic)):
        page_image = np.array(page_image)
    
    # Handle different image modes
    if page_image.ndim == 2:  # Grayscale image
        page_image = cv2.cvtColor(page_image, cv2.COLOR_GRAY2RGB)
    elif page_image.shape[2] == 4:  # RGBA image
        page_image = cv2.cvtColor(page_image, cv2.COLOR_RGBA2RGB)
    elif page_image.shape[2] == 3:
        # Image is already RGB
        pass
    else:
        raise ValueError(f"Unexpected image shape: {page_image.shape}")
    
    # Convert to grayscale
    img_gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)
    
    # Apply image enhancements specifically for historical documents
    
    # Step 1: Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img_gray = clahe.apply(img_gray)
    
    # Step 2: Denoise the image
    img_gray = cv2.fastNlMeansDenoising(img_gray, None, 10, 7, 21)
    
    # Step 3: Apply adaptive thresholding - better for historical documents with uneven illumination
    binary_img = cv2.adaptiveThreshold(
        img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    
    # Step 4: Noise removal and connect broken characters
    kernel = np.ones((1, 1), np.uint8)
    binary_img = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel)
    
    # Deskewing if needed (uncomment if documents are skewed)
    # binary_img = deskew_image(binary_img)
    
    # Convert back to RGB for DocTR
    processed_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2RGB)
    
    # Debug: Save processed image
    debug_dir = Path('data/processed')
    debug_dir.mkdir(exist_ok=True, parents=True)
    debug_path = debug_dir / f'processed_page_{page_num}.png'
    cv2.imwrite(str(debug_path), binary_img)
    logger.debug(f"Saved processed image to {debug_path}")
    
    return processed_img

def deskew_image(image):
    """
    Deskew an image containing text.
    
    Args:
        image: Grayscale binary image.
        
    Returns:
        Deskewed image.
    """
    # Find all non-zero points
    coords = np.column_stack(np.where(image > 0))
    
    # Find the minimum area rectangle
    angle = cv2.minAreaRect(coords)[-1]
    
    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotate the image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated