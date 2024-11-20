# scripts/ocr_main.py

import os
import sys
from pathlib import Path
import argparse

# Add the scripts directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess import preprocess_document
from postprocess import save_to_csv
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

def main(input_path, output_csv):
    # Load the document (PDF with multiple pages)
    doc = DocumentFile.from_pdf(input_path)
    
    # Preprocess each page and store processed images
    processed_pages = []
    for page_num, page in enumerate(doc):
        processed_img = preprocess_document(page, page_num)
        processed_pages.append(processed_img)
    
    # Perform OCR
    model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
    result = model(processed_pages)
    
    # Extract text and save to CSV
    save_to_csv(result, output_csv)
    print(f"OCR results saved to {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR processing of documents")
    parser.add_argument('--input', type=str, required=True, help='Path to the input PDF file')
    parser.add_argument('--output', type=str, required=True, help='Path to the output CSV file')
    
    args = parser.parse_args()
    main(args.input, args.output)
