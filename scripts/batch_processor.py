import os
import logging
import argparse
import concurrent.futures
import pandas as pd
import time
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict

# Add parent directory to path if needed
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the document processing function
from ocr_main import process_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_single_file(file_path: str, output_dir: Path) -> Dict:
    """
    Process a single document file and return results.
    
    Args:
        file_path: Path to the input PDF file
        output_dir: Directory to save the output CSV
        
    Returns:
        Dictionary containing processing results and metadata
    """
    start_time = time.time()
    
    try:
        file_name = os.path.basename(file_path)
        output_file = output_dir / f"{os.path.splitext(file_name)[0]}.csv"
        
        logger.info(f"Starting processing of {file_path}")
        process_document(file_path, str(output_file))
        
        # Check if output was created and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            # Count rows in CSV (subtract 1 for header)
            with open(output_file, 'r') as f:
                row_count = sum(1 for _ in f) - 1
                
            processing_time = time.time() - start_time
            
            logger.info(f"Successfully processed {file_path} - extracted {row_count} rows in {processing_time:.2f}s")
            return {
                "file": file_path,
                "status": "success",
                "rows": row_count,
                "processing_time": processing_time
            }
        else:
            logger.error(f"Processing completed but no output generated for {file_path}")
            return {
                "file": file_path,
                "status": "empty_output",
                "rows": 0,
                "processing_time": time.time() - start_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
        return {
            "file": file_path,
            "status": "error",
            "error": str(e),
            "rows": 0,
            "processing_time": processing_time
        }

def batch_process(input_dir: str, output_dir: str, max_workers: int = 4, file_pattern: str = "*.pdf") -> None:
    """
    Process all matching files in the input directory.
    
    Args:
        input_dir: Directory containing input PDF files
        output_dir: Directory to save output CSV files
        max_workers: Number of parallel workers
        file_pattern: File pattern to match (e.g., "*.pdf")
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Find all matching files
    all_files = list(input_path.glob(file_pattern))
    total_files = len(all_files)
    
    if total_files == 0:
        logger.warning(f"No {file_pattern} files found in {input_dir}")
        return
        
    logger.info(f"Found {total_files} files to process")
    
    # Create a summary file to track progress
    summary_file = output_path / "processing_summary.csv"
    results = []
    
    # Process files with parallel workers
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, str(file_path), output_path): file_path 
            for file_path in all_files
        }
        
        # Process results as they complete
        for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(all_files), desc="Processing files"):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                
                # Update summary file regularly
                pd.DataFrame(results).to_csv(summary_file, index=False)
                
            except Exception as e:
                logger.error(f"Exception processing {file_path}: {str(e)}", exc_info=True)
                results.append({
                    "file": str(file_path),
                    "status": "executor_error",
                    "error": str(e),
                    "rows": 0,
                    "processing_time": 0
                })
    
    # Create final summary report
    summary_df = pd.DataFrame(results)
    summary_df.to_csv(summary_file, index=False)
    
    # Print summary statistics
    success_count = len(summary_df[summary_df['status'] == 'success'])
    total_rows = summary_df['rows'].sum()
    avg_time = summary_df['processing_time'].mean()
    
    logger.info(f"Batch processing complete: {success_count}/{total_files} files successful")
    logger.info(f"Total rows extracted: {total_rows}")
    logger.info(f"Average processing time per file: {avg_time:.2f}s")
    
    if success_count < total_files:
        logger.warning(f"Failed files: {total_files - success_count}")
        for _, row in summary_df[summary_df['status'] != 'success'].iterrows():
            logger.warning(f"  {row['file']} - {row['status']}: {row.get('error', 'Unknown error')}")

def main():
    parser = argparse.ArgumentParser(description="Batch OCR processing for historical postal service tables")
    parser.add_argument('--input_dir', type=str, required=True, help='Directory containing input PDF files')
    parser.add_argument('--output_dir', type=str, required=True, help='Directory for output CSV files')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--pattern', type=str, default="*.pdf", help='File pattern to match (e.g., "*.pdf")')
    
    args = parser.parse_args()
    
    batch_process(args.input_dir, args.output_dir, args.workers, args.pattern)

if __name__ == "__main__":
    main()