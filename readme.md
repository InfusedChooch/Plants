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
python Static/Python_lite/PDFScraper.py \
    --in_pdf Templates/Plant\ Guide\ 2025\ Update.pdf \
    --out_csv Outputs/Plants_NeedLinks.csv \
    --img_dir Outputs/pdf_images \
    --map_csv Outputs/image_map.csv
```

### GeneratePDF

Generate a styled PDF from your filled CSV and images.

```bash
python Static/Python_lite/GeneratePDF.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_pdf Outputs/Plant_Guide_EXPORT.pdf \
    --img_dir Outputs/pdf_images/jpeg \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### Excelify2

Export a formatted Excel workbook for easy filtering and review.

```bash
python Static/Python_lite/Excelify2.py \
    --in_csv Outputs/Plants_Linked_Filled.csv \
    --out_xlsx Outputs/Plants_Linked_Filled_Review.xlsx \
    --template_csv Templates/Plants_Linked_Filled_Master.csv
```

### Launcher GUI

Provides a simple GUI interface for the tools above:

```bash
python Launcher_lite.py
```

---

## Building Executables (Optional)

If you'd like to build standalone executables using PyInstaller:

```bash
pyinstaller --onefile --distpath helpers Static/Python_lite/PDFScraper.py
pyinstaller --onefile --distpath helpers Static/Python_lite/GeneratePDF.py
pyinstaller --onefile --distpath helpers Static/Python_lite/Excelify2.py

pyinstaller Launcher_lite.py --onedir --noconfirm --windowed \
  --add-data "Static;Static" \
  --add-data "Templates;Templates" \
  --add-data "helpers;helpers" \
  --icon "Static/themes/leaf.ico"
```

---

## Folder Layout

```
├── Launcher_lite.py
├── Static/
│   └── Python_lite/
│   │    ├── PDFScraper.py
│   │    ├── GeneratePDF.py
│   │    └── Excelify2.py
│   └── Python_full/
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
│   │   │    └── leaf.ico
│   │   └── Python_full/
│   │       ├── PDFScraper.py
│   │       ├── GeneratePDF.py
│   │       ├── Excelify2.py
│   │       ├── FillMissingData.py
│   │       └── GetLinks.py
│   ├── helpers/
│   │   ├── PDFScraper.exe
│   │   ├── GeneratePDF.exe
│   │   └── Excelify2.exe
├── Templates/
│   ├── Plants_Linked_Filled_Master.csv
│   ├── Plant Guide 2025 Update.pdf
│   └── MASTER_MASTER_20250605.csv
├── Outputs/
│   ├── pdf_images/
│   ├── Plants_Linked_Filled.csv
│   ├── Plant_Guide_EXPORT.pdf
│   └── Plants_Linked_Filled_Review.xlsx
```


This is a representation of where to get the data and how it is stored
| **Column**                      | **Data Hierarchy**                        | **Formatting / Notes**                                     |
| ------------------------------- | ----------------------------------------- | ---------------------------------------------------------- |
| Plant Type                      | Given                                     |                                                            |
| Key                             | generated from Botanical Name             |                                                            |
| Botanical Name                  | Given                                     | Italics                                                    |
| Common Name                     | Given                                     | stored in ALL CAPS                                         |
| Height (ft)                     | MBG → Wildflower                          | `X - Y`                                                    |
| Spread (ft)                     | MBG → Wildflower                          | `X - Y`                                                    |
| Bloom Color                     | Wildflower → MBG → Pinelands/New Moon     | `Color1, Color2, ...`                                      |
| Bloom Time                      | Wildflower → MBG → Pinelands/New Moon     | `Month1, Month2, ...`                                      |
| Sun                             | MBG → Wildflower                          | `Full sun, Part sun, Part Shade, Full Shade`               |
| Water                           | MBG → Wildflower                          | `Low, Medium, High`                                        |
| AGCP Regional Status            | Wildflower                                | from "National Wetland Indicator Status"                   |
| Distribution Zone               | MBG                                       |                                                            |
| Attracts                        | Pleasant Run + WF + MBG + Pinelands       |                                                            |
| Tolerates                       | MBG + Pleasant Run + New Moon + Pinelands | comma-separated list                                       |
| Soil Description                | Wildflower                                |                                                            |
| Condition Comments              | Wildflower                                |                                                            |
| Maintenance                     | MBG                                       | `Low, Medium, High`                                        |
| Native Habitats                 | Wildflower                                | comma-separated list                                       |
| Culture                         | MBG                                       |                                                            |
| Uses                            | MBG                                       |                                                            |
| UseXYZ                          | Wildflower                                | **Under Benefits List:"Use "X": X, Use"Y":Y..."**         |
| Propagation\:Maintenance        | Wildflower                                | optional: Might not exist, Under Proptional fieldopagation |
| Problems                        | MBG                                       |                                                            |
| Link: Missouri Botanical Garden | from GetLinks                             |                                                            |
| Link: Wildflower.org            | from GetLinks                             |                                                            |
| Link: Pleasantrunnursery.com    | from GetLinks                             |                                                            |
| Link: Newmoonnursery.com        | from GetLinks                             |                                                            |
| Link: Pinelandsnursery.com      | from GetLinks                             |                                                            |

