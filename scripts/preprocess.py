# scripts/preprocess.py

import cv2
import numpy as np
import os
from pathlib import Path

def preprocess_document(page_image, page_num):
    """
    Preprocess the page image.

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
        # Convert grayscale to RGB
        page_image = cv2.cvtColor(page_image, cv2.COLOR_GRAY2RGB)
    elif page_image.shape[2] == 4:  # RGBA image
        # Convert RGBA to RGB
        page_image = cv2.cvtColor(page_image, cv2.COLOR_RGBA2RGB)
    elif page_image.shape[2] == 3:
        # Image is already RGB
        pass
    else:
        raise ValueError(f"Unexpected image shape: {page_image.shape}")

    # Apply original preprocessing (if any)
    # For example, converting to grayscale and thresholding
    img_gray = cv2.cvtColor(page_image, cv2.COLOR_RGB2GRAY)
    _, binary_img = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Convert back to RGB
    processed_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2RGB)
    
    # Optional: Save the processed image (commented out, can be enabled for debugging)
    # processed_img_path = Path('../data/processed') / f'processed_page_{page_num}.png'
    # cv2.imwrite(str(processed_img_path), binary_img)
    
    return processed_img
