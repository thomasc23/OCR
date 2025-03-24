import os
import re
import logging
import shutil
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def ensure_dir(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to check/create
    """
    os.makedirs(directory, exist_ok=True)

def merge_csvs(csv_files: List[str], output_file: str) -> None:
    """
    Merge multiple CSV files into a single file.
    
    Args:
        csv_files: List of CSV file paths
        output_file: Path to save the merged CSV
    """
    dfs = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception as e:
            logger.error(f"Error reading {file}: {str(e)}")
    
    if not dfs:
        logger.error("No CSV files could be read")
        return
    
    # Concatenate dataframes
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # Save merged file
    merged_df.to_csv(output_file, index=False)
    logger.info(f"Merged {len(merged_df)} rows from {len(dfs)} files into {output_file}")

def get_cleaned_state_name(state_text: str) -> Optional[str]:
    """
    Extract and clean a state name from text.
    
    Args:
        state_text: Text containing a state name
        
    Returns:
        Cleaned state name or None if not found
    """
    if not state_text or not isinstance(state_text, str):
        return None
    
    # Remove trailing period if present
    state = state_text.strip().rstrip(".")
    
    # List of valid US states and territories (historical context - 1880s)
    valid_states = {
        "Alabama", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
        "Dakota", "Delaware", "Florida", "Georgia", "Idaho", "Illinois", "Indiana",
        "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
        "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska",
        "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
        "Ohio", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "Tennessee",
        "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
        "Wisconsin", "Wyoming", "Alaska", "District of Columbia"
    }
    
    # Check if it's a valid state
    if state in valid_states:
        return state
    
    # Check for common abbreviations or misspellings
    state_mapping = {
        "Ala": "Alabama",
        "Ariz": "Arizona",
        "Ark": "Arkansas",
        "Cal": "California",
        "Calif": "California",
        "Col": "Colorado",
        "Colo": "Colorado",
        "Conn": "Connecticut",
        "Dak": "Dakota",
        "Del": "Delaware",
        "Fla": "Florida",
        "Ga": "Georgia",
        "Ill": "Illinois",
        "Ind": "Indiana",
        "Kan": "Kansas",
        "Ky": "Kentucky",
        "La": "Louisiana",
        "Md": "Maryland",
        "Mass": "Massachusetts",
        "Mich": "Michigan",
        "Minn": "Minnesota",
        "Miss": "Mississippi",
        "Mo": "Missouri",
        "Mont": "Montana",
        "Neb": "Nebraska",
        "Nev": "Nevada",
        "N.H": "New Hampshire",
        "N. H": "New Hampshire",
        "N.J": "New Jersey",
        "N. J": "New Jersey",
        "N.M": "New Mexico",
        "N. M": "New Mexico",
        "N.Y": "New York",
        "N. Y": "New York",
        "N.C": "North Carolina",
        "N. C": "North Carolina",
        "N.D": "North Dakota",
        "N. D": "North Dakota",
        "Okla": "Oklahoma",
        "Ore": "Oregon",
        "Pa": "Pennsylvania",
        "Penn": "Pennsylvania",
        "R.I": "Rhode Island",
        "R. I": "Rhode Island",
        "S.C": "South Carolina",
        "S. C": "South Carolina",
        "S.D": "South Dakota",
        "S. D": "South Dakota",
        "Tenn": "Tennessee",
        "Tex": "Texas",
        "Vt": "Vermont",
        "Va": "Virginia",
        "Wash": "Washington",
        "W.V": "West Virginia",
        "W. V": "West Virginia",
        "W.Va": "West Virginia",
        "W. Va": "West Virginia",
        "Wis": "Wisconsin",
        "Wyo": "Wyoming",
        "D.C": "District of Columbia",
        "D. C": "District of Columbia"
    }
    
    for abbr, full_name in state_mapping.items():
        if state.startswith(abbr):
            return full_name
    
    return state  # Return as-is if not recognized

def clean_compensation_value(value: str) -> str:
    """
    Clean and normalize compensation values.
    
    Args:
        value: Compensation value as string
        
    Returns:
        Cleaned compensation value
    """
    if not value or not isinstance(value, str):
        return value
    
    # Remove any text that's not part of the monetary value
    value = value.strip()
    
    # Handle "p.m." notation (postmaster fee)
    is_pm = False
    if "p.m." in value.lower() or "p. m." in value.lower():
        is_pm = True
        value = re.sub(r'p\.m\.|p\. m\.', '', value.lower(), flags=re.IGNORECASE).strip()
    
    # Extract numeric part with dollar sign
    match = re.search(r'\$?[\d,\.]+', value)
    if match:
        clean_value = match.group(0)
        
        # Remove commas in numbers
        clean_value = clean_value.replace(',', '')
        
        # Ensure dollar sign is present
        if not clean_value.startswith('$'):
            clean_value = '$' + clean_value
        
        # Add p.m. back if it was present
        if is_pm:
            clean_value = f"{clean_value} p.m."
            
        return clean_value
        
    return value

def backup_file(file_path: str, backup_dir: str = "backups") -> str:
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_dir: Directory to store backups
        
    Returns:
        Path to the backup file
    """
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return None
    
    # Create backup directory if it doesn't exist
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True, parents=True)
    
    # Create backup filename with timestamp
    file_name = os.path.basename(file_path)
    backup_file = backup_path / file_name
    
    # Copy file to backup
    shutil.copy2(file_path, backup_file)
    logger.info(f"Backed up {file_path} to {backup_file}")
    
    return str(backup_file)