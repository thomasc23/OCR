import logging
from typing import List, Dict, Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)

def detect_table_structure(ocr_result, page_num):
    """
    Detect table structure from OCR results.
    Specifically designed for postal clerk tables with fixed column structure.
    
    Args:
        ocr_result: The OCR result from DocTR
        page_num: The page number being processed
        
    Returns:
        A list of dictionaries with structured table data
    """
    # Get all text lines with their positions for the current page
    lines = []
    page = ocr_result.pages[page_num]
    
    for block in page.blocks:
        for line in block.lines:
            line_text = " ".join(word.value for word in line.words).strip()
            
            # Skip empty lines
            if not line_text:
                continue
                
            # Get line position (use left-most word and top position)
            if line.words:
                x_min = min(word.geometry[0][0] for word in line.words)
                y_min = min(word.geometry[0][1] for word in line.words)
            else:
                continue
                
            lines.append({
                "text": line_text,
                "x": x_min,
                "y": y_min
            })
    
    # Sort lines by y-position (top to bottom)
    lines.sort(key=lambda l: l["y"])
    
    # Extract table headings
    column_names = ["Name", "Where born", "Whence appointed", "Post-office", "Compensation per annum"]
    
    # Identify column boundaries - for this specific table format
    # This assumes a relatively consistent structure across pages
    columns = []
    if lines:
        # Based on typical table structure, define approximate column positions
        page_width = 1.0  # DocTR uses normalized coordinates (0-1)
        column_positions = [0.0, 0.36, 0.47, 0.59, 0.7, 1.0]  # Estimated positions based on example
        
        for i in range(len(column_positions) - 1):
            columns.append((column_positions[i], column_positions[i+1]))
    
    # Process table rows
    table_data = []
    current_state = None
    last_values = {col: "" for col in column_names}
    
    for line_idx, line in enumerate(lines):
        # Skip header lines and empty lines
        if line_idx < 5 or "CLERKS IN POST-OFFICES" in line["text"].upper():
            continue
            
        # Check if this is a state heading (e.g., "Alabama." or "Arizona.")
        if line["x"] < 0.3 and line["text"].endswith(".") and len(line["text"].split()) <= 2:
            current_state = line["text"].rstrip(".")
            logger.info(f"Detected state heading: {current_state}")
            continue
            
        # Try to categorize this line into columns based on x-position
        col_idx = None
        for i, (start, end) in enumerate(columns):
            if start <= line["x"] < end:
                col_idx = i
                break
                
        if col_idx is None:
            continue
            
        # If this is the first column, start a new row
        if col_idx == 0:
            row = {col: "" for col in column_names}
            row[column_names[col_idx]] = line["text"]
            table_data.append(row)
        elif table_data:  # Add to current row
            table_data[-1][column_names[col_idx]] = line["text"]
    
    # Post-process: Replace "do" indicators and add state context
    processed_data = []
    for row in table_data:
        # Add state information if available
        row["State"] = current_state
        
        # Replace "do" with the value from the previous row
        for col in column_names:
            if row[col].lower().strip() == "do":
                row[col] = last_values[col]
            else:
                last_values[col] = row[col]
                
        processed_data.append(row)
    
    logger.info(f"Extracted {len(processed_data)} table rows from page {page_num}")
    return processed_data

def calibrate_column_positions(ocr_result, page_num=0):
    """
    Helper function to analyze and calibrate column positions.
    This is useful when processing a new batch of documents.
    
    Args:
        ocr_result: OCR result from DocTR
        page_num: Page number to analyze
        
    Returns:
        Dictionary with stats about x-positions of detected text
    """
    lines = []
    page = ocr_result.pages[page_num]
    
    for block in page.blocks:
        for line in block.lines:
            line_text = " ".join(word.value for word in line.words).strip()
            
            # Skip empty lines
            if not line_text:
                continue
                
            # Get line position (use left-most word)
            if line.words:
                x_min = min(word.geometry[0][0] for word in line.words)
            else:
                continue
                
            lines.append({
                "text": line_text,
                "x": x_min
            })
    
    # Group by x position (rounded to 2 decimal places)
    x_positions = {}
    for line in lines:
        x_rounded = round(line["x"], 2)
        if x_rounded not in x_positions:
            x_positions[x_rounded] = []
        x_positions[x_rounded].append(line["text"])
    
    # Sort by x position
    sorted_positions = sorted(x_positions.items())
    
    # Calculate potential column boundaries
    breakpoints = []
    if len(sorted_positions) > 1:
        for i in range(len(sorted_positions) - 1):
            x1 = sorted_positions[i][0]
            x2 = sorted_positions[i + 1][0]
            if x2 - x1 > 0.05:  # Significant gap
                breakpoints.append((x1 + x2) / 2)
    
    return {
        "positions": sorted_positions,
        "potential_breakpoints": breakpoints
    }