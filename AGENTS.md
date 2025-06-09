# 🧠 agents.md — Overview of Helper EXEs and Workflow Roles

This document explains how the plant database pipeline has been modularized into standalone agents (compiled `.exe` files) and how each one contributes to the overall process. This system allows for portable, frozen distribution using PyInstaller's **onedir** mode.

---

## 🎯 Project Architecture: One Tool = One Agent

Each tool in the workflow is converted to its own EXE via PyInstaller, and organized under the `/helpers` subdirectory.

```text
dist/
  Launcher/
    Launcher.exe
    helpers/
      PDFScraper.exe
      GetLinks.exe
      FillMissingData.exe
      GeneratePDF.exe
      Excelify2.exe
    Static/
    Templates/
```

The `Launcher.exe` serves as the central GUI that calls each helper with its respective input/output arguments.

---

## 🥉 Agent Responsibilities

Each EXE in the `/helpers` folder maps directly to one Python script and is responsible for a single pipeline step:

| EXE Name              | Role Description                                                                  |
| --------------------- | --------------------------------------------------------------------------------- |
| `PDFScraper.exe`      | Extracts plant data, links, and image assets from the source PDF.                 |
| `GetLinks.exe`        | Fills in missing web links (MBG, Wildflower.org, nurseries) via browser scraping. |
| `FillMissingData.exe` | Fills gaps in plant data using those links (height, spread, habitats, etc.).      |
| `GeneratePDF.exe`     | Generates a printable PDF guide with TOC, plant cards, and inline images.         |
| `Excelify2.exe`       | Exports a cleanly formatted Excel workbook with filters, legends, and links.      |

All of these EXEs accept CLI arguments for input/output and behave identically whether run standalone or via the Launcher.

---

## ⚙️ The Launcher

The `Launcher.py` (built as `Launcher.exe`) is a CustomTkinter GUI that:

* Detects whether it's running from source or frozen.
* Routes user input to the correct agent (EXE) via subprocess.
* Handles file I/O paths, argument passing, and runtime logging.
* Automatically syncs with `Static/`, `Templates/`, and `Outputs/`.

You can override:

* Input/output paths
* File prefixes/suffixes
* PDF/image directories
* Master CSVs
  ...all from the UI before triggering a run.

---

## 📦 How Freezing Works

Each script is bundled individually using:

```bash
pyinstaller your_script.py --onefile --noconfirm --windowed
```

The Launcher is bundled as:

```bash
pyinstaller Launcher.py --onedir --noconfirm --windowed \
  --add-data "Static;Static" \
  --add-data "Templates;Templates" \
  --add-data "helpers;helpers" \
  --icon "Static/themes/leaf.ico"
```

> 💡 By separating each tool into its own EXE, we simplify debugging, modular reuse, and allow for partial updates without rebuilding the entire suite.

---

## 🗃 Folder Layout Summary

```text
Templates/           ← PDF, master CSV
Static/              ← ChromePortable, themes, pdf_images/
helpers/             ← Onefile PyInstaller EXEs
Outputs/             ← All generated files
Launcher.exe         ← GUI entry point
```

---

## 🧼 Notes for Devs

* All scripts use `repo_dir()` to find the root, so relative paths always resolve from the launcher.
* If a Chrome driver is needed, place it in `Static/GoogleChromePortable/...`.
* All missing folders are auto-created on first launch.
* Ensure `requirements.txt` is up to date when re-freezing any EXE.

---
