# Plant Guide Toolchain (Lite Edition)

This branch is a simplified version of the full Plant Guide toolchain. It is designed for users who already have a **master list** of plants and want to generate reviewable and printable outputs.

## Features in this Version

✅ **PDF Scraper**: Still available to extract plant data from a guide PDF.

✅ **Generate PDF**: Creates a printable plant guide with sections, photos, and formatting.

✅ **Export to Excel**: Produces a styled Excel file with filters, highlights, and version notes uses python from Static\Python_full for source relevance.

🚫 **Find Links (GetLinks.py)**: **Removed** in this branch. It is assumed your master list already contains necessary links.

🚫 **Fill Missing Data (FillMissingData.py)**: **Removed** in this branch. No online enrichment is performed.

---

## Prerequisites

* **Python** 3.10 or higher
* `pip` for installing packages
* Python dependencies from `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## Available Scripts

Each script can be run from the command line or through the included GUI launcher.

### PDFScraper

Extract plant names and images from a source PDF.

```bash
python Static/Python/PDFScraper.py \
    --in_pdf Templates/Plant\ Guide\ 2025\ Update.pdf \
    --out_csv Outputs/Plants_NeedLinks.csv \
    --img_dir Outputs/pdf_images \
    --map_csv Outputs/image_map.csv
```

### GeneratePDF

Generate a styled PDF from your filled CSV and images.

```bash
python Static/Python/GeneratePDF.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_pdf Outputs/Plant_Guide_EXPORT.pdf \
    --img_dir Outputs/pdf_images/jpeg \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### Excelify2

Export a formatted Excel workbook for easy filtering and review.

```bash
python Static/Python/Excelify2.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_xlsx Outputs/Plants_Linked_Filled_Review.xlsx \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### Launcher GUI

Provides a simple GUI interface for the tools above:

```bash
python Launcher.py
```

---

## Building Executables (Optional)

If you'd like to build standalone executables using PyInstaller:

```bash
pyinstaller --onefile --distpath helpers Static/Python/PDFScraper.py
pyinstaller --onefile --distpath helpers Static/Python/GeneratePDF.py
pyinstaller --onefile --distpath helpers Static/Python/Excelify2.py

pyinstaller Launcher.py --onedir --noconfirm --windowed \
  --add-data "Static;Static" \
  --add-data "Templates;Templates" \
  --add-data "helpers;helpers" \
  --icon "Static/themes/leaf.ico"
```

---

## Folder Layout

```
├── Launcher.py
├── Static/
│   └── Python/
│       ├── PDFScraper.py
│       ├── GeneratePDF.py
│       └── Excelify2.py
├── Templates/
│   └── Plants_Linked_Filled_Master.csv
│   └── Plant Guide 2025 Update.pdf
│   └── MASTER_MASTER_20250605.csv
├── Outputs/
│   ├── Plants_Linked_Filled.csv
│   ├── Plant_Guide_EXPORT.pdf
│   └── Plants_Linked_Filled_Review.xlsx
```

## EXE Folder Layout

```
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
```


This Lite version assumes your CSV is already prepared. If you need help generating it from scratch, refer to the full toolchain branch.
