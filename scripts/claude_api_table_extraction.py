import anthropic
import base64
import os
import pandas as pd
import io
import time
import re
from pdf2image import convert_from_path
import tempfile
import argparse
from typing import List, Optional, Dict, Any, Tuple

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
    
    def _clean_csv_text(self, csv_text: str) -> str:
        """
        Clean the CSV text to handle common parsing issues.
        
        Args:
            csv_text: Raw CSV text from Claude
            
        Returns:
            Cleaned CSV text ready for parsing
        """
        # Replace spaces in monetary values with empty strings
        # This handles cases like "p.m. 900 00" -> "p.m.90000"
        cleaned_text = re.sub(r'(\$?\d+)\s+(\d{2})', r'\1\2', csv_text)
        
        # If there are dollar signs, make sure they're properly formatted
        cleaned_text = re.sub(r'(\$)(\d+)', r'\1\2', cleaned_text)
        
        # Remove any extra quotes that might cause parsing issues
        cleaned_text = cleaned_text.replace('""', '"')
        
        return cleaned_text
    
    def _parse_csv_with_confidence(self, csv_text: str) -> Tuple[pd.DataFrame, float]:
        """
        Parse CSV text and assign a confidence score based on parsing success.
        
        Args:
            csv_text: CSV text to parse
            
        Returns:
            Tuple of (DataFrame, confidence_score)
        """
        # Clean the CSV text
        cleaned_text = self._clean_csv_text(csv_text)
        
        # Try parsing with standard CSV parser first
        try:
            df = pd.read_csv(io.StringIO(cleaned_text))
            return df, 1.0  # High confidence if standard parsing works
        except Exception as e:
            # If standard parsing fails, try a more flexible approach
            try:
                # Try parsing with the Python engine which is more flexible
                df = pd.read_csv(io.StringIO(cleaned_text), sep=None, engine='python')
                return df, 0.8  # Good confidence but not perfect
            except Exception:
                pass
        
        # If both methods failed, try parsing line by line
        lines = cleaned_text.strip().split('\n')
        if len(lines) <= 1:
            # Not enough data to parse
            return pd.DataFrame(), 0.0
        
        # Get the header
        header = lines[0].split(',')
        
        # Parse each line manually
        data = []
        row_confidences = []
        
        for line in lines[1:]:
            fields = line.split(',')
            
            # Calculate confidence for this row based on field count match
            field_count_confidence = min(len(fields) / len(header), 1.0)
            row_confidences.append(field_count_confidence)
            
            # Truncate or pad the row to match header length
            if len(fields) > len(header):
                # If too many fields, combine extra fields into the last column
                combined_extra = ','.join(fields[len(header)-1:])
                fields = fields[:len(header)-1] + [combined_extra]
            elif len(fields) < len(header):
                # If too few fields, pad with empty strings
                fields = fields + [''] * (len(header) - len(fields))
            
            data.append(fields)
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=header)
        
        # Calculate overall confidence
        avg_confidence = sum(row_confidences) / len(row_confidences) if row_confidences else 0.5
        
        # Add confidence column to DataFrame
        df['extraction_confidence'] = row_confidences + [1.0] * (len(df) - len(row_confidences))
        
        return df, avg_confidence
    
    def extract_table_from_pdf_page(self, pdf_path: str, page_number: int, 
                                    retry_count: int = 3, retry_delay: int = 2) -> Tuple[pd.DataFrame, float]:
        """
        Extract a table from a specific page of a PDF using Claude.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to extract (1-indexed)
            retry_count: Number of times to retry on failure
            retry_delay: Delay in seconds between retries
            
        Returns:
            Tuple of (DataFrame containing the extracted table, confidence score)
        """
        # Convert PDF page to image
        image_path = self._convert_pdf_page_to_image(pdf_path, page_number)
        
        try:
            # Encode the image
            base64_image = self._encode_image(image_path)
            
            # Make multiple attempts in case of API errors
            best_df = pd.DataFrame()
            best_confidence = 0.0
            
            for attempt in range(retry_count):
                try:
                    # Create the message to Claude with the image
                    message = self.client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        max_tokens=4000,
                        temperature=0.2,  # Lower temperature for more consistent extraction
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "This image contains a table with postal clerk data. Extract all data from the table and provide it in CSV format. Include these columns: Name, Where born, Whence appointed, Post-office, Compensation per annum, State, Postmaster (1 for yes, 0 for no).\n\nImportant: For compensation values, combine any spaces between dollars and cents (e.g., '$100 00' should be '$10000'). Only respond with the raw CSV data, no explanations or markdown formatting."
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
                    
                    # Parse the CSV data with confidence score
                    df, confidence = self._parse_csv_with_confidence(csv_text)
                    
                    if confidence > best_confidence and not df.empty:
                        best_df = df
                        best_confidence = confidence
                    
                    # If we got a good result, no need to retry
                    if confidence > 0.9:
                        break
                    
                    # If we have a usable result but not perfect, continue to next attempt
                    if confidence > 0.5 and attempt < retry_count - 1:
                        print(f"Got usable result (confidence {confidence:.2f}), but trying again for better quality...")
                        time.sleep(retry_delay)
                        continue
                        
                except Exception as api_error:
                    if attempt < retry_count - 1:
                        print(f"Attempt {attempt + 1} failed: {str(api_error)}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise api_error
            
            if best_df.empty:
                raise Exception("Failed to extract any usable data after multiple attempts")
                
            return best_df, best_confidence
            
        finally:
            # Clean up the temporary image file
            if os.path.exists(image_path):
                os.remove(image_path)
    
    def process_pdf_document(self, pdf_path: str, output_dir: str = ".",
                             start_page: int = 1, end_page: Optional[int] = None) -> List[Tuple[pd.DataFrame, float]]:
        """
        Process multiple pages of a PDF document and extract tables.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save the CSV files
            start_page: First page to process (1-indexed)
            end_page: Last page to process (inclusive), or None to process till the end
            
        Returns:
            List of tuples (DataFrame, confidence), one per page
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
                df, confidence = self.extract_table_from_pdf_page(pdf_path, page_num)
                results.append((df, confidence))
                
                # Save individual page result
                output_path = os.path.join(output_dir, f"{file_base}_page_{page_num}.csv")
                df.to_csv(output_path, index=False)
                print(f"Saved extracted table to {output_path} (confidence: {confidence:.2f})")
                
                # Also save a metadata file with the confidence score
                meta_path = os.path.join(output_dir, f"{file_base}_page_{page_num}_meta.json")
                pd.Series({
                    'page': page_num,
                    'confidence': confidence,
                    'rows': len(df),
                    'columns': len(df.columns)
                }).to_json(meta_path)
                
            except Exception as e:
                print(f"Error processing page {page_num}: {str(e)}")
                # Create an empty DataFrame with the expected structure to maintain continuity
                empty_df = pd.DataFrame(columns=['Name', 'Where born', 'Whence appointed', 
                                                'Post-office', 'Compensation per annum', 
                                                'State', 'Postmaster', 'extraction_confidence'])
                results.append((empty_df, 0.0))
                
                # Save the empty DataFrame to maintain file sequence
                output_path = os.path.join(output_dir, f"{file_base}_page_{page_num}_error.csv")
                empty_df.to_csv(output_path, index=False)
                print(f"Saved empty placeholder for page {page_num} due to error")
        
        # Save combined results if we have any
        valid_results = [(df, conf) for df, conf in results if not df.empty]
        if valid_results:
            # Extract just the DataFrames for combining
            valid_dfs = [df for df, _ in valid_results]
            
            # Check if all DataFrames have similar columns (ignoring extraction_confidence)
            base_cols = set(valid_dfs[0].columns) - {'extraction_confidence'}
            if all(set(df.columns) - {'extraction_confidence'} == base_cols for df in valid_dfs):
                # Combine the DataFrames
                combined_df = pd.concat(valid_dfs, ignore_index=True)
                combined_path = os.path.join(output_dir, f"{file_base}_combined.csv")
                combined_df.to_csv(combined_path, index=False)
                print(f"Saved combined table to {combined_path}")
                
                # Also save a filtered version with only high-confidence rows
                if 'extraction_confidence' in combined_df.columns:
                    high_conf_df = combined_df[combined_df['extraction_confidence'] > 0.7]
                    high_conf_path = os.path.join(output_dir, f"{file_base}_combined_high_confidence.csv")
                    high_conf_df.to_csv(high_conf_path, index=False)
                    print(f"Saved high-confidence rows to {high_conf_path}")
            else:
                print("Tables have different structures, not combining them.")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Extract tables from PDF documents using Claude API')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output_dir', default='./data/output', help='Directory to save the CSV files')
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