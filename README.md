# OCR

```
my-ocr-project/
├── data/
│   ├── raw/                # Store original images/PDFs (historical documents) here
│   ├── processed/          # Save processed images or intermediate files, if needed
│   └── output/             # Store the final OCR-processed data (e.g., CSV files)
├── scripts/
│   ├── ocr_main.py         # Main script for running OCR on documents
│   ├── preprocess.py       # Scripts for pre-processing images (e.g., resizing, thresholding)
│   ├── postprocess.py      # Post-processing scripts (e.g., formatting output for CSV)
│   └── utils.py            # Utility functions used across the project
├── notebooks/              # Jupyter notebooks for experimenting and testing OCR on documents
├── tests/                  # Unit tests for OCR functions and other scripts
├── requirements.txt        # Dependencies for the project (e.g., `pytesseract`, `opencv-python`)
├── README.md               # Project overview and instructions for use
└── .gitignore              # Files to ignore in version control (e.g., data/raw/*, *.pdf)
```
