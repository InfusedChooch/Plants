RU Plant Guide/
├── Launcher.exe                     # <- main GUI
├── _internal/
│   ├── Static/
│   │   └── themes/
│   │       └── leaf.ico
│   ├── Templates/
│   │   ├── Plants_Linked_Filled_Master.csv
│   │   ├── Plant Guide 2025 Update.pdf
│   │   └── MASTER_MASTER_20250605.csv
│   ├── helpers/
│   │   ├── PDFScraper.exe
│   │   ├── GeneratePDF.exe
│   │   └── Excelify2.exe
├── Outputs/
│   ├── pdf_images/
│   ├── Plants_Linked_Filled.csv
│   ├── Plant_Guide_EXPORT.pdf
│   └── Plants_Linked_Filled_Review.xlsx

We need to make sure this is getting setup and works as expected, requirements.txt needs to be updated for the lite scripts.

excelify needs to be updated with pulling from Static/Python_full