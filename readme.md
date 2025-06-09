# Plant Guide Toolchain

This repository contains a set of helper scripts and a simple GUI for processing
PDF plant guides into CSV, PDF and Excel outputs. The scripts can be run
directly with Python or packaged into executables using PyInstaller.

## Prerequisites

* **Python** 3.10 or higher
* `pip` for installing packages
* Google Chrome and a matching `chromedriver` (required by `GetLinks.py` when
  automated browsing is needed)
* Python dependencies from `requirements.txt`:

```
$(cat requirements.txt)
```

Install them with:

```bash
pip install -r requirements.txt
```

## Running the Helper Scripts

Each script lives under `Static/Python/` and has sensible defaults so it can be
run directly from the repository root.

### PDFScraper

Extracts plant data and images from `Templates/Plant Guide 2025 Update.pdf`.

```bash
python Static/Python/PDFScraper.py \
    --in_pdf Templates/Plant\ Guide\ 2025\ Update.pdf \
    --out_csv Outputs/Plants_NeedLinks.csv \
    --img_dir Outputs/pdf_images \
    --map_csv Outputs/image_map.csv
```

### GetLinks

Looks up missing plant links. Chrome will only be launched when needed.
Specify the location of `chromedriver.exe` and `chrome.exe` when not detected
automatically.

```bash
python Static/Python/GetLinks.py \
    --in_csv Outputs/Plants_NeedLinks.csv \
    --out_csv Outputs/Plants_Linked.csv \
    --master_csv Templates/Plants_Linked_Filled_Master.csv \
    --chromedriver /path/to/chromedriver.exe \
    --chrome_binary /path/to/chrome.exe
```

### FillMissingData

Fills numeric fields and habitat descriptions from online resources.

```bash
python Static/Python/FillMissingData.py \
    --in_csv Outputs/Plants_Linked.csv \
    --out_csv Outputs/Plants_Linked_Filled.csv \
    --master_csv Templates/Plants_Linked_Filled_Master.csv
```

### GeneratePDF

Creates a printable guide PDF from the filled CSV.

```bash
python Static/Python/GeneratePDF.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_pdf Outputs/Plant_Guide_EXPORT.pdf \
    --img_dir Outputs/pdf_images/jpeg \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### Excelify2

Exports a styled Excel workbook for review.

```bash
python Static/Python/Excelify2.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_xlsx Outputs/Plants_Linked_Filled_Review.xlsx \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### GUI Launcher

For a simple GUI workflow run:

```bash
python Launcher.py
```

## Building Executables

Install PyInstaller (already listed in `requirements.txt`) and run the following
from the repository root. The helpers are placed in `helpers/` and the launcher
at the repository root.

```bash
pyinstaller --onefile --distpath helpers Static/Python/PDFScraper.py
pyinstaller --onefile --distpath helpers Static/Python/GetLinks.py
pyinstaller --onefile --distpath helpers Static/Python/FillMissingData.py
pyinstaller --onefile --distpath helpers Static/Python/GeneratePDF.py
pyinstaller --onefile --distpath helpers Static/Python/Excelify2.py
pyinstaller Launcher.py --onedir --noconfirm --windowed `
  --add-data "Static;Static" `
  --add-data "Templates;Templates" `
  --add-data "helpers;helpers" `
  --icon "Static/themes/leaf.ico"
```

## Verifying the Toolchain

Before packaging, ensure each step works with the provided sample files:

1. Run `PDFScraper.py` and confirm that `Outputs/Plants_NeedLinks.csv` and
   extracted images appear.
2. Run `GetLinks.py` to populate URLs in the CSV.
3. Run `FillMissingData.py` and verify the filled CSV is created.
4. Run `GeneratePDF.py` and check that the resulting PDF opens correctly.
5. Run `Excelify2.py` to produce the review spreadsheet.
6. Optionally launch `Launcher.py` and walk through the steps via the GUI.

If each script succeeds with the defaults, the toolchain is ready to package
with PyInstaller.