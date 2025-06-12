# Plant Guide Toolchain (EXE Edition)

## Features in this Version

❌**PDF Scraper**: **Broken** **OLD** Going to be Phased out / Retooled. 

❌**Generate PDF**: **Broken** **Updating** Creates a printable plant guide with sections, photos, and formatting. Needs to be updated to fit new CSV Layout. 

✅**Export to Excel**: Produces a styled Excel file with filters, highlights, and version notes uses python from Static\Python_full for source relevance.

❌**Find Links (GetLinks.py)**: **Broken**. Needs to Update Link Finding Logic to suit ""Genus species 'Variety'""

✅**Fill Missing Data (FillMissingData.py)**: **Updating** Fills based on Scraped HTML and Grabs, Need to refine column grabs for long chains. 

---
### 🔄 How to Run Clean & Merge

This script supports two modes: `clean` and `merge`.
Use it to prepare and merge plant data into the masterlist.

---

#### 📦 Default Behavior (Clean Mode)

```
python CleanMerge.py
```

* Cleans `Outputs/Plants_Linked_Filled_Reviewed.csv`
* Outputs cleaned file to: `Outputs/Plants_Linked_Filled_Reviewed_Clean.csv`
* Logs all changes to: `Outputs/NewMaster/Plants_Linked_Filled_Reviewed_Clean_log.md`

---

#### 🔁 To Run Merge Mode

```
python CleanMerge.py --mode merge
```

* Merges `Outputs/Plants_Linked_Filled_Reviewed_Clean.csv`
  into `Templates/0612_Masterlist_RO.csv`
* Outputs merged file to: `Outputs/NewMaster/YYYYMMDD_Masterlist_Merged.csv`
* Logs all merge actions to: `Outputs/NewMaster/YYYYMMDD_Masterlist_Merged_merge_log.md`

---

#### ⚙️ Optional Arguments

| Flag         | Description                                     |
| ------------ | ----------------------------------------------- |
| `--mode`     | `clean` (default) or `merge`                    |
| `--input`    | Source file for cleaning (default reviewed CSV) |
| `--verified` | File to merge into master (default cleaned CSV) |
| `--master`   | Target masterlist file                          |
| `--template` | CSV defining column structure                   |
| `--out`      | Output filename for merged CSV                  |

> **Tip:** Make sure you are in the same folder as `CleanMerge.py` when running commands. Otherwise, use the full path to the script.


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
## Master CSV Headers
```
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Rev
```
## Important Note
```
Any pd.read_csv needs to have "keep_default_na=False" added to work! 

  df = ( pd.read_csv(CSV_FILE, dtype=str, encoding="utf-8-sig", keep_default_na=False,  ).fillna("") )
```

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
```
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

## Folder Layout
```
├── agents.md
├── Launcher.py
├── readme.md
├── requirements.txt
├── .github/
│ └── workflows/
│ └── tests.yml
├── NEW/
│ ├── 0611_Masterlist_New_Beta_Nodata_NEW.csv
│ └── 0611_Masterlist_New_Beta_Nodata_NEW_merge_log.md
├── Outputs/
│ ├── 0611_Masterlist_Nodata.csv
│ ├── 20250612_Plants_Linked_Filled_JG.csv
│ ├── Fixed_Plant_Guide_EXPORT_JG_TimesLogos.pdf
│ ├── Plants_Linked.csv
│ ├── Plants_Linked_30.csv
│ ├── Plants_Linked_Filled_Review_30Rev.xlsx
│ ├── html_cache/
│ └── Images/
│ ├── NJAES_Logo.jpeg
│ ├── Rutgers_Logo.png
│ └── Plants/
├── SampleTest/
│ ├── Plants_Linked_FIlled_Manual.csv
│ ├── Plants_Linked_Filled_Test.csv
│ └── SampleTestvManual.py
├── Static/
│ ├── GoogleChromePortable/
│ ├── Python_full/
│ │ ├── chromedriver.exe
│ │ ├── Excelify2.py
│ │ ├── FillMissingData.py
│ │ ├── GeneratePDF.py
│ │ ├── GetLinks.py
│ │ ├── PDFScraper_depreciate.py
│ │ └── requirements_full.txt
│ └── themes/
│ ├── leaf.ico
│ └── rutgers.json
├── Templates/
│ ├── 0611_Masterlist_Nodata_Readonly.csv
│ ├── 20250612_Plants_Linked_Filled_Review_JG.xlsx
│ ├── Plant Guide 2025 Update.pdf
│ ├── Plants_Linked_Verified.csv
│ ├── Plants_Template.csv
│ ├── ReviewedLinks.csv
│ └── style_rules.yaml
├── Tools/
│ ├── list_files.py
│ └── merge_masterlist.py
```

## Expected EXE Folder Layout
```
RU Plant Guide/
├── Launcher.exe                     # ← main GUI
├── _internal/
│   ├── Static/
│   │   ├── themes/
│   │   │   └── leaf.ico
│   │   └── Python_full/
│   │       ├── chromedriver.exe
│   │       ├── Excelify2.py
│   │       ├── FillMissingData.py
│   │       ├── GeneratePDF.py
│   │       ├── GetLinks.py
│   │       ├── PDFScraper_depreciate.py
│   ├── helpers/
│   │   ├── PDFScraper.exe
│   │   ├── GeneratePDF.exe
│   │   ├── Excelify2.exe
│   │   └── FillMissingData.exe      # ← if compiled
├── Templates/
│   ├── DATE_Masterlist_Nodata_Readonly.csv
│   ├── Plant Guide 2025 Update.pdf
│   ├── Plants_Template.csv
│   ├── ReviewedLinks.csv
│   └── style_rules.yaml
├── Outputs/
│   ├── pdf_images/
│   ├── html_cache/
│   ├── Images/
│   │   ├── NJAES_Logo.jpeg
│   │   ├── Rutgers_Logo.png
│   │   └── Plants/
│   ├── Plants_Linked.csv
```