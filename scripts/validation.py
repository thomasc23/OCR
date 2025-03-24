import os
import pandas as pd
import argparse
import logging
from pathlib import Path
import re
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_csv_file(csv_path: str) -> Dict:
    """
    Validate a single CSV file extracted from postal tables.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Dict containing validation results and issues found
    """
    result = {
        "file": csv_path,
        "valid": True,
        "issues": [],
        "warnings": [],
        "row_count": 0
    }
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        result["row_count"] = len(df)
        
        # Expected columns
        expected_columns = {
            "Name", "Where born", "Whence appointed", "Post-office", 
            "Compensation per annum", "State"
        }
        
        # Check column presence
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            result["valid"] = False
            result["issues"].append(f"Missing columns: {', '.join(missing_columns)}")
        
        # Check for empty values
        for col in df.columns:
            empty_count = df[col].isna().sum()
            if empty_count > 0:
                result["warnings"].append(f"Column '{col}' has {empty_count} empty values")
        
        # Check for unresolved "do" values
        for col in df.columns:
            if df[col].dtype == 'object':  # Only check string columns
                do_count = df[df[col].str.lower().str.strip() == "do"].shape[0]
                if do_count > 0:
                    result["valid"] = False
                    result["issues"].append(f"Found {do_count} unresolved 'do' values in column '{col}'")
        
        # Validate specific columns
        if "Compensation per annum" in df.columns:
            # Clean the compensation column
            comp_col = df["Compensation per annum"].astype(str)
            
            # Check for invalid compensation values (should contain dollar sign or be empty)
            invalid_comp = ~comp_col.str.contains(r'^\$|\bp\.m\.|^nan$', regex=True, na=True)
            invalid_count = invalid_comp.sum()
            
            if invalid_count > 0:
                result["warnings"].append(f"{invalid_count} rows have suspicious compensation values")
                # Log a few examples
                examples = df.loc[invalid_comp, "Compensation per annum"].head(3).tolist()
                result["warnings"].append(f"Examples of suspicious values: {examples}")
        
        # Check state consistency
        if "State" in df.columns and "Where born" in df.columns:
            state_mismatch = 0
            for _, row in df.iterrows():
                state = str(row.get("State", "")) if not pd.isna(row.get("State", "")) else ""
                born = str(row.get("Where born", "")) if not pd.isna(row.get("Where born", "")) else ""
                
                if born != "do" and state and born and state.lower() != born.lower():
                    # There might be legitimate reasons for this, so just count as warning
                    state_mismatch += 1
            
            if state_mismatch > 0:
                result["warnings"].append(f"{state_mismatch} rows have potential state/birthplace mismatches")
                
    except Exception as e:
        result["valid"] = False
        result["issues"].append(f"Error processing file: {str(e)}")
        logger.error(f"Validation error for {csv_path}: {str(e)}", exc_info=True)
    
    return result

def validate_directory(input_dir: str, report_path: str = None) -> pd.DataFrame:
    """
    Validate all CSV files in the directory and generate a report.
    
    Args:
        input_dir: Directory containing CSV files to validate
        report_path: Path to save the validation report (optional)
        
    Returns:
        DataFrame with validation results
    """
    input_path = Path(input_dir)
    all_files = list(input_path.glob("*.csv"))
    
    if not all_files:
        logger.warning(f"No CSV files found in {input_dir}")
        return pd.DataFrame()
    
    logger.info(f"Validating {len(all_files)} CSV files")
    
    # Validate each file
    validation_results = []
    for file_path in all_files:
        logger.info(f"Validating {file_path}")
        result = validate_csv_file(str(file_path))
        validation_results.append(result)
    
    # Create report DataFrame
    report_df = pd.DataFrame(validation_results)
    
    # Save report if requested
    if report_path:
        report_df.to_csv(report_path, index=False)
        logger.info(f"Validation report saved to {report_path}")
    
    # Print summary
    valid_count = sum(1 for r in validation_results if r["valid"])
    total_rows = sum(r["row_count"] for r in validation_results)
    logger.info(f"Validation complete: {valid_count}/{len(validation_results)} files valid")
    logger.info(f"Total rows: {total_rows}")
    
    # Print issues for invalid files
    invalid_files = [r for r in validation_results if not r["valid"]]
    if invalid_files:
        logger.warning(f"{len(invalid_files)} files have validation issues:")
        for r in invalid_files:
            logger.warning(f"  {r['file']}: {'; '.join(r['issues'])}")
    
    return report_df

def main():
    parser = argparse.ArgumentParser(description="Validate extracted CSV files from historical postal tables")
    parser.add_argument('--input_dir', type=str, required=True, help='Directory containing CSV files to validate')
    parser.add_argument('--report', type=str, default="validation_report.csv", help='Path to save validation report')
    
    args = parser.parse_args()
    validate_directory(args.input_dir, args.report)

if __name__ == "__main__":
    main()