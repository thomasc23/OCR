"""
Configuration settings for the OCR processing pipeline.
These settings can be adjusted based on the specific documents being processed.
"""

# Table structure configuration
TABLE_CONFIG = {
    # Column positions (x-coordinates) for the table
    # Format: [start_col1, start_col2, start_col3, start_col4, start_col5, end_col5]
    "column_positions": [0.0, 0.36, 0.47, 0.59, 0.7, 1.0],
    
    # Column names matching the structure
    "column_names": ["Name", "Where born", "Whence appointed", "Post-office", "Compensation per annum"],
    
    # Minimum number of rows expected in a valid table
    "min_rows": 5,
    
    # Maximum y-distance between lines to consider them part of the same row
    "row_threshold": 0.015,
    
    # Keywords that indicate a state header
    "state_header_keywords": ["Alabama", "Arizona", "Arkansas", "California", "Colorado", 
                             "Connecticut", "Dakota", "Delaware", "Florida", "Georgia", 
                             "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", 
                             "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", 
                             "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", 
                             "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", 
                             "North Carolina", "Ohio", "Oregon", "Pennsylvania", "Rhode Island", 
                             "South Carolina", "Tennessee", "Texas", "Utah", "Vermont", 
                             "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
}

# OCR model configuration
OCR_CONFIG = {
    # DocTR model architecture
    "detection_model": "db_resnet50",
    "recognition_model": "crnn_vgg16_bn",
    
    # Use pretrained model
    "pretrained": True,
    
    # Confidence thresholds
    "detection_threshold": 0.5,
    "recognition_threshold": 0.7
}

# Image preprocessing configuration
PREPROCESSING_CONFIG = {
    # Thresholding parameters
    "adaptive_threshold_block_size": 11,
    "adaptive_threshold_constant": 2,
    
    # Morphological operations
    "morphology_kernel_size": (1, 1),
    
    # Apply deskewing
    "apply_deskew": False,
    
    # Apply denoising
    "apply_denoise": True,
    
    # Debug mode (save intermediate images)
    "debug_mode": True,
    
    # Debug directory
    "debug_dir": "data/processed"
}

# Batch processing configuration
BATCH_CONFIG = {
    # Default number of parallel workers
    "default_workers": 4,
    
    # Maximum number of workers
    "max_workers": 8,
    
    # Default file pattern
    "default_pattern": "*.pdf",
    
    # Create backups before processing
    "create_backups": True,
    
    # Backup directory
    "backup_dir": "data/backups"
}

# Post-processing configuration
POSTPROCESSING_CONFIG = {
    # Replace "do" placeholders
    "replace_do_placeholders": True,
    
    # Clean compensation values
    "clean_compensation": True,
    
    # Fix state names
    "normalize_state_names": True,
    
    # Normalize column names
    "normalize_column_names": True
}

# Validation configuration
VALIDATION_CONFIG = {
    # Required columns
    "required_columns": ["Name", "Where born", "Whence appointed", "Post-office", 
                         "Compensation per annum", "State"],
    
    # Maximum allowable empty values per column (%)
    "max_empty_percentage": 5,
    
    # Enable strict validation
    "strict_validation": False
}