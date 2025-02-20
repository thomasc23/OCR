# scripts/postprocess.py

import pandas as pd

def save_to_csv(ocr_result, output_csv):
    data = []
    
    # Iterate over pages
    for page_num, page in enumerate(ocr_result.pages):
        for block in page.blocks:
            for line in block.lines:
                # Combine all word values in the line into one string.
                line_text = " ".join(word.value for word in line.words)
                
                # Optionally, compute the average confidence for the line.
                if line.words:
                    line_confidence = sum(word.confidence for word in line.words) / len(line.words)
                else:
                    line_confidence = 0

                data.append({
                    'page_num': page_num + 1,
                    'text': line_text,
                    'confidence': line_confidence
                })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)

# def save_to_csv(ocr_result, output_csv):
#     """
#     Extracts text data from OCR result and saves it to a CSV file.

#     Args:
#         ocr_result: The result object from the OCR model.
#         output_csv: Path to the output CSV file.
#     """
#     data = []
    
#     # Iterate over pages
#     for page_num, page in enumerate(ocr_result.pages):
#         for block in page.blocks:
#             for line in block.lines:
#                 for word in line.words:
#                     data.append({
#                         'page_num': page_num + 1,
#                         'text': word.value,
#                         'confidence': word.confidence
#                     })
    
#     # Create DataFrame
#     df = pd.DataFrame(data)
    
#     # Save to CSV
#     df.to_csv(output_csv, index=False)
