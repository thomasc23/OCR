# scripts/preprocess.py

import cv2
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
    
    # Convert to grayscale
    img_gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding (original preprocessing)
    _, binary_img = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Optional: Save the processed image (commented out, can be enabled for debugging)
    # processed_img_path = Path('../data/processed') / f'processed_page_{page_num}.png'
    # cv2.imwrite(str(processed_img_path), binary_img)
    
    return binary_img
