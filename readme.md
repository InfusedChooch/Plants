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
CSV header               : data source path                : expected format
Plant Type               : Masterlist                      : Perennial | Shrub | …
Key                      : FillMissingData                 : 2-3 letter unique code
Botanical Name           : Masterlist                      : Genus species 'Variety' (italics)
Common Name              : Masterlist                      : ALL CAPS

Height (ft)              : MBG → WF → PL                   : X - Y
Spread (ft)              : MBG → WF → PL                   : X - Y
Bloom Color              : WF + MBG + PL/NM                : Color1, Color2, …
Bloom Time               : WF + MBG + PL/NM                : Jan, Feb, …
Sun                      : MBG → WF “Light Requirement”    : Full Sun, Part Sun, …
Water                    : MBG → WF “Soil Moisture”        : Low | Medium | High
AGCP Regional Status     : WF (Wetland Indicator)          : FACU | OBL | …
USDA Hardiness Zone      : MBG “Zone”                      : Zone X – Y

Attracts                 : PR + WF + MBG + Pinelands        : Bees, Butterflies, …
Tolerates                : MBG + PR + NM + Pinelands        : Deer, Salt, …
Soil Description         : WF “Soil Description”            : paragraph
Condition Comments       : WF “Condition Comments”          : paragraph
MaintenanceLevel         : MBG “Maintenance”                : Low | Medium | High
Native Habitats          : WF “Native Habitat”              : Prairie, Woodland, …
Culture                  : MBG “Culture” / “Growing Tips”   : paragraph
Uses                     : MBG “Uses”                       : paragraph
UseXYZ                   : WF Benefit list                  : Use Ornamental: …; Use Wildlife: …
WFMaintenance            : WF "Maintenance:"                : free-text
Problems                 : MBG “Problems”                   : paragraph

Link: MBG                : GetLinks                         : URL
Link: Wildflower.org     : GetLinks                         : URL
Link: Pleasant Run       : GetLinks                         : URL
Link: New Moon           : GetLinks                         : URL
Link: Pinelands          : GetLinks                         : URL
Link: Other              : [Tag,"URL","Label"]              : Entry list "[Tag,""URL"",""Label""]" : [T1,""https://Test.com"",""Test 1""];
Rev                      : User Input (YYYYMMDD_FL)         : "YYYYMMDD_FirstinitalLastinital" 
```

## Master CSV Headers
```
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Link: Others,Rev
```
## Important Note

Any pd.read_csv needs to have "keep_default_na=False" added to work, This is only needed to preserve the NA tag with pandas 

```
  df = ( pd.read_csv(CSV_FILE, dtype=str, encoding="utf-8-sig", keep_default_na=False,  ).fillna("") )
```

## Prerequisites
* Python dependencies from `requirements.txt`

beautifulsoup4  # Static/Python_full/GetLinks.py, Static/Python_full/FillMissingData.py
black  # Static/Python_full/Excelify2.py
customtkinter  # Launcher.py
fpdf2  # Static/Python_full/GeneratePDF.py
lxml  # Static/Python_full/GetLinks.py, Static/Python_full/FillMissingData.py
openpyxl  # Static/Python_full/Excelify2.py
pandas  # Static/Tools/CleanMerge.py, Static/Python_full/Excelify2.py, Static/Python_full/FillMissingData.py, Static/Python_full/GeneratePDF.py, Static/Python_full/GetLinks.py, Static/Python_full/PDFScraper_depreciate.py, ReviewFiles/SampleTest/SampleTestvManual.py
pdfplumber  # Static/Python_full/PDFScraper_depreciate.py
pillow  # Static/Python_full/GeneratePDF.py, Static/Python_full/PDFScraper_depreciate.py
pymupdf  # Static/Python_full/PDFScraper_depreciate.py
pytest  # tests
pyyaml  # Static/Python_full/GeneratePDF.py
requests  # Static/Python_full/GetLinks.py, Static/Python_full/FillMissingData.py
rich  # ReviewFiles/SampleTest/SampleTestvManual.py
selenium  # Static/Python_full/GetLinks.py
tqdm  # Static/Python_full/FillMissingData.py, Static/Python_full/PDFScraper_depreciate.py


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
├── Outputs/
| ├── NewMaster/
│ ├── html_cache/
│ └── Images/
│   ├── NJAES_Logo.jpeg
│   ├── Rutgers_Logo.png
│   └── Plants/
├── SampleTest/
│ ├── Plants_Linked_FIlled_Manual.csv
│ ├── Plants_Linked_Filled_Test.csv
│ └── SampleTestvManual.py
├── Static/
│ ├── GoogleChromePortable/
│ ├── Python_full/
| ├──Tools/
│ └── themes/
│ ├── leaf.ico
│ └── rutgers.json
├── Templates/

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
│   ├── helpers/
│   │   ├── PDFScraper.exe
│   │   ├── GeneratePDF.exe
│   │   ├── Excelify2.exe
│   │   └── FillMissingData.exe      # ← if compiled
├── Templates/
├── Outputs/
```



"[GM,""www.google.maps.com"",""Google Maps""];[YT,""https://youtube.com"",""YouTube""];[T1,""https://Test.com"",""Test 1""];[T2,""https://Test.com"",""Test 2""];[T3,""https://Test.com"",""Test 3""]"