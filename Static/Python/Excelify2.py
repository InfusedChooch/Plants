# Static\Python\Excelify2.py
"""Create a styled Excel workbook from the fully populated plant CSV.

Columns are formatted and highlighted for easier review and the script info is
embedded for traceability.
"""

from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter
from datetime import datetime
import black  # New: for Black-style formatting
import argparse

parser = argparse.ArgumentParser(description="Export formatted Excel from CSV")
parser.add_argument(
    "--in_csv",
    default="Static/Templates/Plants_Linked_Filled_Master.csv",
    help="Input CSV file",
)
parser.add_argument(
    "--out_xlsx",
    default="Static/Outputs/Plants_Linked_Filled_Review.xlsx",
    help="Output Excel file",
)
args = parser.parse_args()

# ─── File Paths ───────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent  # Goes from Static/Python → repo root
CSV_FILE = (REPO / args.in_csv).resolve()
XLSX_FILE = (REPO / args.out_xlsx).resolve()


# ─── Step 1: Load CSV and write it to a basic Excel file ────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
template_cols = list(
    pd.read_csv(
        Path("Static/Templates/Plants_Linked_Filled_Master.csv"), nrows=0
    ).columns
)
df = df.reindex(
    columns=template_cols + [c for c in df.columns if c not in template_cols]
)
df.to_excel(XLSX_FILE, index=False)
wb = load_workbook(XLSX_FILE)
ws = wb.active
ws.title = "Plant Data"

# ─── Step 2: Freeze header row, style headers, and auto-adjust column widths ───
ws.freeze_panes = "A2"
HEADER_FILL = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
BOLD_FONT = Font(bold=True)
for cell in ws[1]:
    cell.fill = HEADER_FILL
    cell.font = BOLD_FONT
for i, column_cells in enumerate(ws.columns, start=1):
    max_length = max(len(str(cell.value or "")) for cell in column_cells)
    ws.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

# ─── Step 3: Apply filters to specific columns ──────────────────────────────
filter_cols = [
    "Page in PDF",
    "Plant Type",
    "Bloom Color",
    "Sun",
    "Water",
]
header = [cell.value for cell in ws[1]]
filter_indices = [i + 1 for i, val in enumerate(header) if val in filter_cols]
if filter_indices:
    col_range = f"{get_column_letter(min(filter_indices))}1:{get_column_letter(max(filter_indices))}1"
    ws.auto_filter.ref = col_range

# ─── Step 4: Highlight missing cells in red ────────────────────────────────
RED = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
for row_idx, row in enumerate(df.itertuples(index=False), start=2):
    for col_idx, col_name in enumerate(header, start=1):
        cell = ws.cell(row=row_idx, column=col_idx)
        if not cell.value or str(cell.value).strip() == "":
            cell.fill = RED

# ─── Step 5: README Sheet ─────────────────────────────────────────────────
readme = wb.create_sheet("README")
readme.sheet_properties.tabColor = "A9A9A9"
readme.column_dimensions["A"].width = 100
readme["A1"] = "🌿 Plant Database Export: Excel Legend and Process Notes"
readme["A3"] = "Legend:"
readme["A4"] = "🔴 Red: Missing value (empty cell)"
readme["A6"] = "Filters applied only to these columns:"
readme["A7"] = ", ".join(filter_cols)
readme["A9"] = "🛠 How to filter by partial match in Excel:"
readme["A10"] = (
    "1. Click the filter dropdown on the column header (e.g., Sun or Water)."
)
readme["A11"] = "2. Choose 'Text Filters' > 'Contains...'"
readme["A12"] = "3. Type a partial term (e.g., 'shade', 'yellow') and click OK."
readme["A13"] = "💡 Use this to find plants matching conditions across categories."
readme["A15"] = "📄 https://github.com/InfusedChooch/Plants"
readme["A16"] = (
    "This Excel was generated from the filled CSV using the script Excelify2.py"
)
readme["A17"] = (
    "Download https://portableapps.com/apps/internet/google_chrome_portable and place it in the /Static folder"
)
readme["A18"] = "Static/GoogleChromePortable"

# ─── Step 6: Script Version Info ──────────────────────────────────────────
script_descriptions = {
    "PDFScraper.py": "Extracts plant data from the PDF guide",
    "GetLinks.py": "Finds official MBG & WF URLs for each plant",
    "FillMissingData.py": "Populates missing fields using those links",
    "Excelify2.py": "Creates formatted Excel output with filters & highlights",
}
row_start = readme.max_row + 2
readme[f"A{row_start}"] = "📁 Script Version Info (Last Modified):"
for i, (filename, description) in enumerate(
    script_descriptions.items(), start=row_start + 1
):
    path = BASE / filename
    if path.exists():
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
        readme[f"A{i}"] = f"{filename:<24} → {modified}    {description}"
    else:
        readme[f"A{i}"] = f"{filename:<24} → MISSING        {description}"

# ─── Step 7: Append pip requirements ──────────────────────────────────────
req_path = REPO / "requirements.txt"
readme_row = readme.max_row + 2
readme[f"A{readme_row}"] = "📦 Required Python Packages:"
try:
    lines = req_path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, start=readme_row + 1):
        if line.strip() and not line.strip().startswith("#"):
            readme[f"A{i}"] = line.strip()
except Exception as e:
    readme[f"A{readme_row + 1}"] = f"⚠️ Error reading requirements.txt: {e}"

# ─── Step 8: Embed Black-styled script content ─────────────────────────────
for script_name in script_descriptions:
    path = BASE / script_name
    if not path.exists():
        continue

    with open(path, "r", encoding="utf-8") as f:
        raw_code = f.read()

    try:
        formatted_code = black.format_str(raw_code, mode=black.Mode())
    except Exception:
        formatted_code = raw_code

    ws = wb.create_sheet(script_name)
    ws.column_dimensions["A"].width = 120
    ws["A1"] = "```python"
    for i, line in enumerate(formatted_code.splitlines(), start=2):
        ws[f"A{i}"] = line
    ws[f"A{i+1}"] = "```"

# ─── Step 9: Import readme.md as its own tab ──────────────────────────────
readme_md_path = REPO / "readme.md"
if readme_md_path.exists():
    readme_full = wb.create_sheet("README_full")
    readme_full.column_dimensions["A"].width = 120
    with readme_md_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            readme_full[f"A{i}"] = line.rstrip("\n")
else:
    print("[WARN] readme.md not found. Skipping README_full tab.")


def safe_print(*objs, **kw):
    try:
        print(*objs, **kw)
    except UnicodeEncodeError:
        fallback = " ".join(str(o) for o in objs)
        encoded = fallback.encode(sys.stdout.encoding or "ascii", "ignore").decode()
        print(encoded, **kw)


# ─── Step 10: Save Excel ─────────────────────────────────────────────────
wb.save(XLSX_FILE)
print(f"Yeehaw Final Excel saved --> {XLSX_FILE}")
