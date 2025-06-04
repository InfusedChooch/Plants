# 🌱 Plant Database Automation Suite

A fully automated pipeline for extracting, enriching, verifying, and exporting plant data from Rutgers Cooperative PDF fact sheets, Missouri Botanical Garden, and Wildflower.org.

---

## 📦 Requirements (from `requirements.txt`)

```txt
fpdf2
pandas
openpyxl
beautifulsoup4==4.12.3
requests==2.31.0
pdfplumber==0.10.2
tqdm==4.66.2
Pillow
lxml==5.2.1
selenium==4.20.0
PyPDF2==3.0.1
Customtkinter
tkinter
black
```

To install all dependencies:

```bash
pip install -r requirements.txt
```

> **Chrome Note**: To use Selenium, you must install [Google Chrome Portable](https://portableapps.com/apps/internet/google_chrome_portable) and place it inside the `Static/GoogleChromePortable/` folder. Also ensure `chromedriver.exe` is in `Static/Python/`.

---

## 🔁 Workflow Overview

| Step | Script               | Purpose                                                                                |
| ---- | -------------------- | -------------------------------------------------------------------------------------- |
| 1    | `PDFScraper.py`      | Extracts plant data from the Rutgers PDF and saves a partially filled CSV and images.  |
| 2    | `GetLinks.py`        | Locates links for MBG, Wildflower.org, Pleasantrunnursery.com, Newmoonnursery.com, and Pinelandsnursery.com sites. |
| 3    | `FillMissingData.py` | Pulls additional plant info from those links to complete the dataset.                  |
| 4    | `TestLinks.py`       | Checks all links to flag and log any broken entries.                                   |
| 5    | `Excelify2.py`       | Produces a styled Excel file with filters, highlights, and embedded source code.       |
| 6    | `GeneratePDF.py`     | Generates a clean, printable PDF plant guide with TOC, sections, and images.           |
| -    | `Launcher.py`        | CustomTkinter GUI to run the toolchain with override paths, console log, and controls. |

---

## 📁 File Descriptions

### `PDFScraper.py`

* Parses the Rutgers PDF guide.
* Extracts plant names, page numbers, height/spread, and any embedded links.
* Saves images from each page as JPEGs.
* Outputs `Plants_NeedLinks.csv` and `image_map.csv`.

### `GetLinks.py`

* Uses each site's search first, then falls back to Bing with Selenium (HTML fallback).
* Requires portable Chrome setup.
* Outputs `Plants_Linked.csv`.

### `FillMissingData.py`

* Scrapes plant details from the MBG and WF links.
* Adds missing attributes like bloom, sun, water, habitat, and characteristics.
* Outputs `Plants_Linked_Filled.csv`.


### `Excelify2.py`

* Converts the final CSV to a styled Excel workbook.
* Adds filters, missing-cell highlights, README tab, pip list, and Black-styled embedded source code.

### `GeneratePDF.py`

* Reads the final CSV.
* Creates a printable PDF with a title page, TOC, plant sections, and footers with source links.

### `Launcher.py`

* CustomTkinter interface for running tools with override support for input/output.
* Auto-generates output paths using prefix/suffix.
* Logs real-time script output.

---

## 📂 Output Files

* `Plants_NeedLinks.csv` – initial extract from PDF.
* `Plants_Linked.csv` – with links filled in.
* `Plants_Linked_Filled.csv` – full dataset with scraped attributes.
* `broken_links.txt` – log of broken links.
* `Plants_Linked_Filled.xlsx` – styled Excel export with embedded code.
* `Plant_Guide_EXPORT.pdf` – print-ready guide.
* `pdf_images/` – extracted JPEG images.
* `image_map.csv` – mapping of images to plants/pages.

---

## 🚀 Quickstart

1. Run `PDFScraper.py` to extract data and images.
2. Run `GetLinks.py` to search and assign links for all supported sites.
3. Run `FillMissingData.py` to scrape additional data.
4. Run `TestLinks.py` to validate all links.
5. Run `Excelify2.py` to generate the Excel workbook.
6. Run `GeneratePDF.py` to produce the final guide.
7. Optionally, use `Launcher.py` for a GUI-driven experience.

---

## 🔧 Notes

* Chrome/Selenium requires a portable installation of Chrome.
* Image filenames use: `botanical_slug_index.jpg` starting at 0.
* PDF sections auto-group by type (Herbaceous, Ferns, Shrubs, etc).
* `Excelify2.py` sets filters on select columns and highlights missing values.
* Scripts are designed to be rerun with override support.

---

## 📃 Column Data Hierarchy

Every field is first scraped from the Rutgers PDF. Missing values are filled from other sites in the priority order shown.

| **Column** | **Data Hierarchy** | **Formatting / Notes** |
| ---------- | ------------------ | ---------------------- |
| Page in PDF | PDF only | |
| Plant Type | PDF only | |
| Key | generated from Botanical Name | |
| Botanical Name | PDF only | |
| Common Name | PDF only | stored in ALL CAPS |
| Height (ft) | PDF → MBG → Wildflower | `X - Y` |
| Spread (ft) | PDF → MBG → Wildflower | `X - Y` |
| Bloom Color | PDF → Wildflower → MBG | `Color1, Color2, ...` |
| Bloom Time | PDF → Wildflower → MBG | `Month1, Month2, ...` |
| Sun | PDF → MBG → Wildflower | `Full sun, Part sun, Part Shade, Full Shade` |
| Water | PDF → MBG → Wildflower | `Low, Medium, High` |
| Tolerates | PDF → MBG + Pleasant Run | comma-separated list |
| Maintenance | PDF → MBG | `Low, Medium, High` |
| Native Habitats | PDF → Wildflower | comma-separated list |
| Attracts | PDF → Pleasant Run + WF + MBG | |
| Soil Description | PDF → Wildflower | |
| Distribution Zone | PDF → MBG | |
| AGCP Regional Status | PDF → Wildflower | from "National Wetland Indicator Status" |
| Link: Missouri Botanical Garden | from GetLinks | |
| Link: Wildflower.org | from GetLinks | |
| Link: Pleasantrunnursery.com | from GetLinks | |
| Link: Newmoonnursery.com | from GetLinks | |
| Link: Pinelandsnursery.com | from GetLinks | |

Made with 💚 for ecological design and STEM education.
