# scripts/ocr_main.py

import os
import sys
import logging
from pathlib import Path
import argparse

# Add the scripts directory to the path if needed
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from other modules
from preprocess import preprocess_document
from table_detector import detect_table_structure
from postprocess import save_to_csv
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ocr_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def process_document(input_path, output_csv, max_pages=None):
    """
    Process a document using OCR and table structure detection.
    
    Args:
        input_path: Path to the input PDF file
        output_csv: Path to save the extracted data as CSV
        max_pages: Maximum number of pages to process (None for all)
    """
    # Load the document
    logger.info(f"Loading document: {input_path}")
    doc = DocumentFile.from_pdf(input_path)
    total_pages = len(doc)
    
    # Determine pages to process
    if max_pages is not None:
        pages_to_process = min(max_pages, total_pages)
        logger.info(f"Processing first {pages_to_process} out of {total_pages} pages.")
    else:
        pages_to_process = total_pages
        logger.info(f"Processing all {total_pages} pages.")
    
    # Load OCR model
    logger.info("Loading OCR model")
    model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
    
    # Process each page
    all_table_data = []
    
    for page_num in range(pages_to_process):
        logger.info(f"Processing page {page_num+1}/{pages_to_process}")
        
        # Get page image and preprocess
        page_img = doc[page_num]
        processed_img = preprocess_document(page_img, page_num)
        
        # Perform OCR
        logger.info(f"Running OCR on page {page_num+1}")
        result = model([processed_img])
        
        # Extract table structure
        logger.info(f"Detecting table structure on page {page_num+1}")
        table_data = detect_table_structure(result, 0)  # 0 because we're processing one page at a time
        
        if table_data:
            all_table_data.extend(table_data)
            logger.info(f"Found {len(table_data)} table rows on page {page_num+1}")
        else:
            logger.warning(f"No table data detected on page {page_num+1}")
    
    # Save results to CSV
    logger.info(f"Saving {len(all_table_data)} total rows to {output_csv}")
    save_to_csv(all_table_data, output_csv)
    logger.info(f"OCR processing complete. Results saved to {output_csv}")

def main():
    parser = argparse.ArgumentParser(description="OCR processing for historical postal service tables")
    parser.add_argument('--input', type=str, required=True, help='Path to the input PDF file')
    parser.add_argument('--output', type=str, required=True, help='Path to the output CSV file')
    parser.add_argument('--max_pages', type=int, default=None, help='Maximum number of pages to process')
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Process the document
    process_document(args.input, args.output, args.max_pages)

if __name__ == "__main__":
    main()

    

# import os
# import sys
# import logging 
# from pathlib import Path
# import argparse

# # Add the scripts directory to the path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from preprocess import preprocess_document
# from postprocess import save_to_csv
# from doctr.io import DocumentFile
# from doctr.models import ocr_predictor

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# def main(input_path, output_csv, max_pages=None):
#     # Load the document (PDF with multiple pages)
#     doc = DocumentFile.from_pdf(input_path)
#     total_pages = len(doc)

#     # Update logging information
#     if max_pages is not None:
#         logging.info(f"Processing first {max_pages} out of {total_pages} pages.")
#     else:
#         logging.info(f"Processing all {total_pages} pages.")
    
#     # Preprocess each page and store processed images
#     processed_pages = []
#     for page_num, page in enumerate(doc):
        
#         # For testing with single page
#         if max_pages is not None and page_num >= max_pages:
#             break
#         processed_img = preprocess_document(page, page_num)
#         processed_pages.append(processed_img)
    
#     # Perform OCR
#     model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
#     result = model(processed_pages)
    
#     # Extract text and save to CSV
#     save_to_csv(result, output_csv)
#     print(f"OCR results saved to {output_csv}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="OCR processing of documents")
#     parser.add_argument('--input', type=str, required=True, help='Path to the input PDF file')
#     parser.add_argument('--output', type=str, required=True, help='Path to the output CSV file')
#     parser.add_argument('--max_pages', type=int, default=None, help='Maximum number of pages to process')
    
#     args = parser.parse_args()
#     main(args.input, args.output, args.max_pages)
