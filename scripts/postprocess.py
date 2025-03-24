import pandas as pd
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def save_to_csv(table_data, output_csv):
    """
    Save processed table data to CSV.
    
    Args:
        table_data: List of dictionaries containing table row data
        output_csv: Path to output CSV file
    """
    if not table_data:
        logger.warning("No table data to save")
        return
        
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Clean up each column
    for col in df.columns:
        # Convert all values to string
        df[col] = df[col].astype(str)
        
        # Replace 'nan' with empty string
        df[col] = df[col].replace('nan', '')
        
        # Remove leading/trailing spaces
        df[col] = df[col].str.strip()
        
        # Clean up common OCR errors - replace common patterns
        df[col] = df[col].str.replace(r'[,;:"\']', '', regex=True)  # Remove punctuation
        df[col] = df[col].str.replace(r'\s+', ' ', regex=True)      # Normalize whitespace
        
    # Clean up monetary values in the compensation column
    if "Compensation per annum" in df.columns:
        df["Compensation per annum"] = df["Compensation per annum"].apply(clean_compensation)
    
    # Clean up state names
    if "State" in df.columns:
        df["State"] = df["State"].apply(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Filter out rows where Name contains header text
    if "Name" in df.columns:
        df = df[~df["Name"].str.contains("CLERK|POST|OFFICE", case=False, regex=True)]
    
    # Additional clean-up: Remove rows where all values except State are empty
    non_state_cols = [col for col in df.columns if col != "State"]
    if non_state_cols:
        df = df[df[non_state_cols].replace('', pd.NA).notna().any(axis=1)]
    
    # Save to CSV
    df.to_csv(output_csv, index=False)
    logger.info(f"Saved {len(df)} rows to {output_csv}")

def clean_compensation(value):
    """
    Clean up compensation values.
    
    Args:
        value: Raw compensation value string
        
    Returns:
        Cleaned compensation value
    """
    if not isinstance(value, str):
        return value
        
    # Remove any text that's not part of the monetary value
    value = value.strip()
    
    # Handle special case of "p.m." notation (postmaster fee)
    is_pm = False
    if "p.m." in value.lower():
        is_pm = True
        value = value.lower().replace("p.m.", "").strip()
    
    # Extract numeric part with dollar sign
    match = re.search(r'\$?[\d,\.]+', value)
    if match:
        clean_value = match.group(0)
        # Ensure dollar sign is present
        if not clean_value.startswith('$'):
            clean_value = '$' + clean_value
        
        # Add p.m. back if it was present
        if is_pm:
            clean_value = f"{clean_value} p.m."
            
        return clean_value
        
    return value

def merge_csv_files(input_files, output_file):
    """
    Merge multiple CSV files into a single file.
    
    Args:
        input_files: List of input CSV file paths
        output_file: Path to the output merged CSV file
    """
    if not input_files:
        logger.warning("No input files to merge")
        return
        
    # Read all dataframes
    dfs = []
    for file in input_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
            logger.info(f"Read {len(df)} rows from {file}")
        except Exception as e:
            logger.error(f"Error reading {file}: {str(e)}")
    
    if not dfs:
        logger.error("No data to merge")
        return
        
    # Concatenate dataframes
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # Drop duplicates if needed
    # merged_df = merged_df.drop_duplicates()
    
    # Save merged data
    merged_df.to_csv(output_file, index=False)
    logger.info(f"Merged {len(merged_df)} rows into {output_file}")