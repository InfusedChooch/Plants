# Plant Guide Toolchain (EXE Edition)

## Features in this Version

✅ **PDF Scraper**: Still available to extract plant data from a guide PDF.

✅ **Generate PDF**: Creates a printable plant guide with sections, photos, and formatting.

✅ **Export to Excel**: Produces a styled Excel file with filters, highlights, and version notes uses python from Static\Python_full for source relevance.

🚫 **Find Links (GetLinks.py)**: **Removed** in this branch. It is assumed your master list already contains necessary links.

🚫 **Fill Missing Data (FillMissingData.py)**: **Removed** in this branch. No online enrichment is performed.

---

## Prerequisites

```bash
pip install -r requirements.txt
```
* `pip` for installing packages
* Python dependencies from `requirements.txt`
        pandas
        openpyxl
        black
        tqdm
        pillow
        fpdf2
        pdfplumber
        pymupdf
        customtkinter
        pyinstaller
        pyyaml
        pytest
        beautifulsoup4
        lxml
        requests


## Building Executables (Optional)


```bash
pyinstaller --onefile --distpath helpers Static/Python_full/PDFScraper.py
pyinstaller --onefile --distpath helpers Static/Python_full/GeneratePDF.py
pyinstaller --onefile --distpath helpers Static/Python_full/Excelify2.py
pyinstaller --onefile --distpath helpers Static/Python_full/FillMissingData.py

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
│        ├── PDFScraper.py
│        ├── GeneratePDF.py
│        └── Excelify2.py
├── Templates/
├── Outputs/
│   
```

## Expected EXE Folder Layout

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

**CSV → Source chain (left‑to‑right = first place we look, fallbacks follow, + means append to previous entry)**
```
CSV header               : data source path                              : expected format
Plant Type               : Masterlist                                    : Perennial | Shrub | …
Key                      : FillMissingData                               : 2-3 letter unique code
Botanical Name           : Masterlist                                    : Genus species 'Variety' (italics)
Common Name              : Masterlist                                    : ALL CAPS

Height (ft)              : MBG → Wildflower.org → Pinelands              : X - Y
Spread (ft)              : MBG → Wildflower.org → Pinelands              : X - Y
Bloom Color              : Wildflower.org + MBG + Pinelands/New Moon     : Color1, Color2, …
Bloom Time               : Wildflower.org + MBG + Pinelands/New Moon     : Jan, Feb, …
Sun                      : MBG → WF “Light Requirement”                  : Full Sun, Part Sun, …
Water                    : MBG → WF “Soil Moisture”                      : Low | Medium | High
AGCP Regional Status     : WF (Wetland Indicator)                        : FACU | OBL | …
USDA Hardiness Zone      : MBG “Zone”                                    : Zone X – Y

Attracts                 : PR + WF + MBG + Pinelands                     : Bees, Butterflies, …
Tolerates                : MBG + PR + NM + Pinelands                     : Deer, Salt, …
Soil Description         : WF “Soil Description”                         : paragraph
Condition Comments       : WF “Condition Comments”                       : paragraph
MaintenanceLevel         : MBG “Maintenance”                             : Low | Medium | High
Native Habitats          : WF “Native Habitat”                           : Prairie, Woodland, …
Culture                  : MBG “Culture” / “Growing Tips”                : paragraph
Uses                     : MBG “Uses”                                    : paragraph
UseXYZ                   : WF Benefit list                               : Use Ornamental: …; Use Wildlife: …
WFMaintenance            : WF "Maintenance:"                             : free-text
Problems                 : MBG “Problems”                                : paragraph

Link: MBG                : GetLinks (MBG ID)                             : URL
Link: Wildflower.org     : GetLinks (USDA ID)                            : URL
Link: Pleasant Run       : GetLinks (name match)                         : URL
Link: New Moon           : GetLinks (name match)                         : URL
Link: Pinelands          : GetLinks (name match)                         : URL
Rev                      : User Input (YYYYMMDD_FL)                      : "YYYYMMDD_FirstinitalLastinital"

```

```
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Rev
```