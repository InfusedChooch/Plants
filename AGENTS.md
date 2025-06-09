# 🧠 agents.md — Overview of Helper EXEs and Workflow Roles

This document defines the folder layout, structure, and dependencies for running the Rutgers Plant Guide pipeline from a portable folder. Each step in the pipeline is a separate `.exe` in the `/helpers/` folder, all coordinated by a GUI launcher.

---

## 🏠 Folder Structure Requirement

> **All `.exe` tools must reside in `helpers/` alongside `Launcher.exe`**.

Correct portable layout (Windows example):

```
C:\Users\james.gliem\Desktop\RU Plant Guide\Launcher.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\helpers\Excelify2.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\helpers\FillMissingData.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\helpers\GeneratePDF.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\helpers\GetLinks.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\helpers\PDFScraper.exe
C:\Users\james.gliem\Desktop\RU Plant Guide\Outputs\...
C:\Users\james.gliem\Desktop\RU Plant Guide\Static\...
C:\Users\james.gliem\Desktop\RU Plant Guide\Templates\...
```

---

## 🚧 Agent Roles

| Executable            | Role Description                                                   |
| --------------------- | ------------------------------------------------------------------ |
| `PDFScraper.exe`      | Extracts plant data, hyperlinks, and images from the source PDF.   |
| `GetLinks.exe`        | Fills in MBG/Wildflower/nursery links using Chrome-based scraping. |
| `FillMissingData.exe` | Scrapes site data (height, spread, habitats) into empty fields.    |
| `GeneratePDF.exe`     | Builds a printable guide with TOC, plant cards, and images.        |
| `Excelify2.exe`       | Outputs an Excel workbook with legends, links, and full metadata.  |

---

## ✨ Launcher Behavior

The launcher GUI (`Launcher.exe`) provides:

* Input/output override per tool
* Persistent state for prefix/suffix, folders, and master CSV
* Image folder configuration
* Chrome portable validation and installation guidance
* One-click run for each EXE via subprocess

All scripts resolve paths from the launcher root using `repo_dir()` internally, so frozen or source mode works identically.

---

## 📦 Freezing Helpers

Build EXEs using onefile mode:

```bash
pyinstaller Static/Python/PDFScraper.py      --onefile --noconfirm --windowed --distpath "helpers"
pyinstaller Static/Python/GetLinks.py        --onefile --noconfirm --windowed --distpath "helpers"
pyinstaller Static/Python/FillMissingData.py --onefile --noconfirm --windowed --distpath "helpers"
pyinstaller Static/Python/GeneratePDF.py     --onefile --noconfirm --windowed --distpath "helpers"
pyinstaller Static/Python/Excelify2.py       --onefile --noconfirm --windowed --distpath "helpers"
```

The launcher must be built in `onedir` mode:

```bash
pyinstaller Launcher.py --onedir --noconfirm --windowed ^
  --add-data "Static;Static" ^
  --add-data "Templates;Templates" ^
  --add-data "helpers;helpers" ^
  --icon "Static/themes/leaf.ico"
```

---

## 🔎 Dev Notes

* `Static/Python/*.py` are the source scripts for EXEs.
* `Static/GoogleChromePortable` is required for link scraping.
* `Templates/` holds the PDF, master CSV, and templates.
* `Outputs/` is the target folder for generated CSVs, images, and PDFs.
* Launcher dynamically patches subprocess arguments and watches log output live.

Do **not** move helper `.exe` files outside of `/helpers/`, or the GUI launcher will fail to locate them.
