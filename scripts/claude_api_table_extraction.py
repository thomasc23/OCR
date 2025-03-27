import anthropic
import base64
import os
import pandas as pd
import io
import time
from pdf2image import convert_from_path
import tempfile
import argparse
from typing import List, Optional, Dict, Any

class TableExtractor:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TableExtractor with the Anthropic API key.
        
        Args:
            api_key: Anthropic API key. If None, it will try to get it from the environment variable.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Either pass it as an argument or set the ANTHROPIC_API_KEY environment variable.")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode an image file to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _convert_pdf_page_to_image(self, pdf_path: str, page_number: int) -> str:
        """
        Convert a specific page of a PDF to an image.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to convert (1-indexed)
            
        Returns:
            Path to the temporary image file
        """
        # Convert PDF page to image (1-indexed to 0-indexed)
        images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
        
        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
            images[0].save(temp_path, 'PNG')
        
        return temp_path
    
    def extract_table_from_pdf_page(self, pdf_path: str, page_number: int, 
                                    retry_count: int = 3, retry_delay: int = 2) -> pd.DataFrame:
        """
        Extract a table from a specific page of a PDF using Claude.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to extract (1-indexed)
            retry_count: Number of times to retry on failure
            retry_delay: Delay in seconds between retries
            
        Returns:
            Pandas DataFrame containing the extracted table
        """
        # Convert PDF page to image
        image_path = self._convert_pdf_page_to_image(pdf_path, page_number)
        
        try:
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            # Make multiple attempts in case of API errors
            for attempt in range(retry_count):
                try:
                    # Create the message to Claude with the image
                    message = self.client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        max_tokens=4000,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": """Extract tabular data from the image into CSV format with the following specifications:
                                                   1. The image shows employee records organized by state
                                                   2. Each employee row contains: Name, Where born, Whence appointed, Post-office, Compensation per annum
                                                   3. Add "State" as a sixth column for each row based on the state headings
                                                   4. Handle special cases:
                                                        - Replace "do" values with the value from the cell above
                                                        - Replace dotted lines with empty values
                                                        - When 'p.m.' is included in salary add 1 to a seventh column called 'Postmaster' and leave it as 0 otherwise
                                                   5. Ensure proper field separation with commas
                                                   6. Include a header row with the six column names
                                                   7. Include all data from the image with no rows or columns omitted
                                                   Output format: Raw CSV only, no explanations, no markdown formatting"""
                                    },
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": base64_image
                                        }
                                    }
                                ]
                            }
                        ]
                    )
                    
                    # Get Claude's response
                    csv_text = message.content[0].text
                    
                    # Try to parse the CSV data
                    try:
                        df = pd.read_csv(io.StringIO(csv_text))
                        return df
                    except Exception as parse_error:
                        print(f"CSV parsing error: {str(parse_error)}")
                        print(f"Raw CSV text: {csv_text[:500]}...")
                        
                        # Try a more flexible parser if standard CSV parsing fails
                        try:
                            df = pd.read_csv(io.StringIO(csv_text), sep=None, engine='python')
                            return df
                        except Exception:
                            # If we're out of retries, raise the original error
                            if attempt == retry_count - 1:
                                raise parse_error
                    
                except Exception as api_error:
                    if attempt < retry_count - 1:
                        print(f"Attempt {attempt + 1} failed: {str(api_error)}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise api_error
            
            # This should never be reached due to the exception handling above
            raise Exception("Failed to extract table after multiple attempts")
            
        finally:
            # Clean up the temporary image file
            if os.path.exists(image_path):
                os.remove(image_path)
    
    def process_pdf_document(self, pdf_path: str, output_dir: str = ".",
                             start_page: int = 1, end_page: Optional[int] = None) -> List[pd.DataFrame]:
        """
        Process multiple pages of a PDF document and extract tables.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save the CSV files
            start_page: First page to process (1-indexed)
            end_page: Last page to process (inclusive), or None to process till the end
            
        Returns:
            List of DataFrames, one per page
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get file basename for output files
        file_base = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Get total number of pages in PDF
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        total_pages = len(convert_from_path(pdf_path, first_page=1, last_page=None))
        
        if end_page is None or end_page > total_pages:
            end_page = total_pages
        
        results = []
        for page_num in range(start_page, end_page + 1):
            print(f"Processing page {page_num} of {total_pages}...")
            try:
                df = self.extract_table_from_pdf_page(pdf_path, page_num)
                results.append(df)
                
                # Save individual page result
                output_path = os.path.join(output_dir, f"{file_base}_page_{page_num}.csv")
                df.to_csv(output_path, index=False)
                print(f"Saved extracted table to {output_path}")
                
            except Exception as e:
                print(f"Error processing page {page_num}: {str(e)}")
        
        # Save combined results if we have any
        if results:
            # Check if all DataFrames have the same columns
            first_df_cols = results[0].columns
            if all(df.columns.equals(first_df_cols) for df in results):
                combined_df = pd.concat(results, ignore_index=True)
                combined_path = os.path.join(output_dir, f"{file_base}_combined.csv")
                combined_df.to_csv(combined_path, index=False)
                print(f"Saved combined table to {combined_path}")
            else:
                print("Tables have different structures, not combining them.")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Extract tables from PDF documents using Claude API')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output_dir', default='.', help='Directory to save the CSV files')
    parser.add_argument('--start_page', type=int, default=1, help='First page to process (1-indexed)')
    parser.add_argument('--end_page', type=int, help='Last page to process (inclusive)')
    parser.add_argument('--api_key', help='Anthropic API key (optional if set as environment variable)')
    
    args = parser.parse_args()
    
    extractor = TableExtractor(api_key=args.api_key)
    extractor.process_pdf_document(
        pdf_path=args.pdf_path,
        output_dir=args.output_dir,
        start_page=args.start_page,
        end_page=args.end_page
    )


if __name__ == "__main__":
    main()