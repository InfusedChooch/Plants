# 🌿 Rutgers Plant Guide – Portable Build Instructions

## 1. Prerequisites

* **Python 3.13** (only for building – not required on the USB)
* `pip install pyinstaller pandas openpyxl pdfplumber pillow selenium tqdm fitz`
  *(plus anything else listed in `requirements.txt`)*
* **PowerShell 7+** for the helper‑build script.

---

## 2. Folder Layout – Final USB Package

```
dist\
└─ Launcher\
   ├─ Launcher.exe                ← double‑click to start GUI
   ├─ _internal\
   │  ├─ helpers\                 ← compiled helper tools
   │  │  ├─ PDFScraper.exe
   │  │  ├─ GeneratePDF.exe
   │  │  └─ Excelify2.exe
   │  └─ Static\                  ← runtime assets
   │     ├─ themes\rutgers.json
   ├─ Outputs\                    ← created at runtime
   │  ├─ pdf_images\
   │  │  ├─ 001_*.png
   │  │  └─ jpeg\
   │  │     └─ *_0.jpg
   │  └─ Plants_Linked_Filled.csv
   └─ Templates\                  ← always shipped
      ├─ MASTER_MASTER_20250605.csv
      ├─ Plant Guide 2025 Update.pdf
      └─ Plants_Linked_Filled_Master.csv
```

---

## 3. Build Steps

### 3.1  Compile helper executables
.\.venv\Scripts\Activate.ps1

```powershell
# build_helpers.ps1  – run from repo root
$helpers = "PDFScraper.py","GeneratePDF.py","Excelify2.py"
$dest    = "dist/Launcher/_internal/helpers"
foreach ($h in $helpers) {
    pyinstaller "Python/$h" --onefile --noconfirm --windowed `
        --add-data "Static;Static" `
        --distpath  $dest
}
```

### 3.2  Compile the launcher (onedir)

```powershell
pyinstaller Launcher.py --onedir --noconfirm --windowed --name Launcher `
    --icon "Static/themes/leaf.ico" `
    --add-data "Static;_internal/Static" `
    --add-data "Static/Templates;Templates" `
    --add-data "Static/Outputs;Outputs" `
    --distpath "dist"

```

> **Hint:** run *3.1* first so PyInstaller scoops the helpers automatically.

---

## 4. Post‑build Checklist

1. Verify every helper exe exists in `_internal\helpers\`.
2. Confirm `chromedriver.exe` is inside `_internal\Static\Python\`.
3. Launch `Launcher.exe` & run **PDF → Excel** end‑to‑end.
4. `Outputs\pdf_images\jpeg\` should fill with `*.jpg` and appear in the final PDF.

---

## 5. Deploy to USB

1. Copy the entire `dist\Launcher` folder to the flash drive root.
2. Optionally rename the folder (e.g. `RU_Plant_Guide_2025`).
3. Double‑click **Launcher.exe** on any Windows PC – no Python needed.

---

## 6. Runtime Notes

* **Image path logic**
  `PDFScraper.py` writes PNGs to `Outputs/pdf_images/`, then converts them to JPEGs under the `jpeg/` subfolder. `GeneratePDF.py` is configured (via Launcher) to read images from that `jpeg/` directory automatically.
* **Updating templates**
  Drop new PDF or CSV masters into the `Templates/` folder *before* launching.
* **Log capture**
  The console pane in the launcher is resizable; use right‑click → *Copy* to export logs if needed.

---

### 👍 You’re ready to roll!

Insert the USB, open `Launcher.exe`, and the full plant‑guide toolchain runs completely offline.
