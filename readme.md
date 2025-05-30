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
```

To install all dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔁 Workflow Overview

| Step | Script               | Purpose                                                                               |
| ---- | -------------------- | ------------------------------------------------------------------------------------- |
| 1    | `PDFScraper.py`      | Extracts plant data from the Rutgers PDF and saves a partially filled CSV and images. |
| 2    | `GetLinks.py`        | Locates MBG and Wildflower.org links for each plant and updates the CSV.              |
| 3    | `FillMissingData.py` | Pulls additional plant info from those links to complete the dataset.                 |
| 4    | `TestLinks.py`       | Checks all links to flag and log any broken entries.                                  |
| 5    | `Excelify2.py`       | Produces a styled Excel file with filters, highlights, and embedded source code.      |
| 6    | `GeneratePDF.py`     | Generates a clean, printable PDF plant guide with TOC, sections, and images.          |

---

## 📁 File Descriptions

### `PDFScraper.py`

* Parses the Rutgers PDF guide.
* Extracts plant names, page numbers, height/spread, and any embedded links.
* Saves images from each page as JPEGs.
* Outputs `Plants_NeedLinks.csv` and `image_map.csv`.

### `GetLinks.py`

* Uses Selenium (with Bing) and direct queries to find MBG and Wildflower.org links.
* Updates missing URLs in `Plants_NeedLinks.csv` → `Plants_Linked.csv`.

### `FillMissingData.py`

* Scrapes plant details from the MBG and WF links.
* Merges new data into `Plants_Linked.csv` → `Plants_Linked_Filled.csv`.

### `TestLinks.py`

* Validates all saved URLs.
* Flags broken links in a new CSV and logs issues to `broken_links.txt`.

### `Excelify2.py`

* Converts the enriched CSV to a styled Excel workbook.
* Adds conditional formatting, filters, a README tab, and embeds code from all scripts.

### `GeneratePDF.py`

* Reads the final CSV.
* Creates a printable PDF with a title page, TOC, section dividers, and one plant per page.

---

## 📂 Output Files

* `Plants_NeedLinks.csv` – initial extract from PDF.
* `Plants_Linked.csv` – with links filled in.
* `Plants_Linked_Filled.csv` – full dataset with scraped attributes.
* `broken_links.txt` – human-readable list of broken links.
* `Plants_Linked_Filled.xlsx` – styled Excel export.
* `Plant_Guide_EXPORT.pdf` – final print-ready guide.
* `pdf_images/` – extracted images (JPG).
* `image_map.csv` – mapping of images to plants/pages.

---

## 🚀 Quickstart

1. Run `PDFScraper.py` to initialize your dataset and images.
2. Run `GetLinks.py` to fill in MBG/WF URLs.
3. Run `FillMissingData.py` to enrich with scraped data.
4. Run `TestLinks.py` to verify the URLs work.
5. Run `Excelify2.py` to create your styled spreadsheet.
6. Run `GeneratePDF.py` to output the full plant guide PDF.

---

## 🔧 Notes

* Image filenames follow this format: `page#_botanical_slug_count.jpg`.
* All data columns follow the order and format from the original PDF + websites.
* Headers, filters, and empty cell highlights are defined in `Excelify2.py`.
* PDF pages are auto-grouped by plant type (Herbaceous, Ferns, etc).
* You can customize TOC layout, logos, and color schemes in `GeneratePDF.py`.

---

## 🔢 Column Data Sources

| **Column**           | **PDF (Rutgers)** | **MBG** | **Wildflower.org** |
| -------------------- | ----------------- | ------- | ------------------ |
| Page in PDF          | ✅                 |         |                    |
| Plant Type           | ✅ (by page range) |         |                    |
| Key                  | ✅ (generated)     |         |                    |
| Botanical Name       | ✅                 |         |                    |
| Common Name          | ✅                 |         |                    |
| Height (ft)          | ✅                 | ✅       |                    |
| Spread (ft)          | ✅                 | ✅       |                    |
| Bloom Color          |                   | ✅       | ✅ (primary)        |
| Bloom Time           |                   | ✅       | ✅ (primary)        |
| Sun                  |                   | ✅       | ✅ (merged)         |
| Water                |                   | ✅       | ✅ (merged)         |
| Characteristics      |                   | ✅       | ✅ (extended)       |
| Habitats             |                   |         | ✅                  |
| Wildlife Benefits    |                   | ✅       | ✅ (merged)         |
| Distribution         |                   | ✅       |                    |
| Link: MBG            |                   | ✅       |                    |
| Link: Wildflower.org |                   |         | ✅                  |

---

Made with 💚 for ecological design and STEM education.
