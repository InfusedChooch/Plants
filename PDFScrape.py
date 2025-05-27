#!/usr/bin/env python3
"""
PDF-only scraper with standardization:
- Uses 'Page in PDF' if available
- Parses 'Appearance' line-by-line
- Skips pages 21-22
- Generates `Key` from botanical name (e.g. Amsonia tabernaemontana → Ata)
- Formats:
    - Height/Spread: X - Y
    - Bloom Color: color/color
    - Bloom Time: Month - Month
    - Sun: Condition, Condition
"""

import re
import pandas as pd
import pdfplumber
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "Plants and Links.csv"
OUTPUT_CSV = BASE_DIR / "Plants_FROM_PDF_ONLY.csv"
PDF_PATH = BASE_DIR / "Plant Guid Data Base.pdf"

FIELDS = {
    "height": "Height (ft)",
    "spread": "Spread (ft)",
    "color": "Bloom Color",
    "bloom": "Bloom Time",
    "sun": "Sun",
    "water": "Water",
    "wet": "Wetland Status",
    "habitat": "Habitats",
    "char": "Characteristics",
    "wildlife": "Wildlife Benefits",
    "dist": "Distribution",
    "type": "Type",
    "planttype": "Plant Type"
}

def standardize_height(value):
    if not value: return None
    value = value.replace("to", "-").replace("–", "-")
    numbers = re.findall(r"[\d\.]+", value)
    return f"{numbers[0]} - {numbers[1]}" if len(numbers) == 2 else value.strip()

def standardize_color(value):
    if not value: return None
    value = value.replace(",", "/").replace(" or ", "/").replace(" and ", "/")
    return re.sub(r"\s*/\s*", "/", value.strip())

def standardize_bloom_time(value):
    if not value: return None
    months = re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)", value, re.I)
    if len(months) >= 2:
        return f"{months[0].title()} - {months[1].title()}"
    elif len(months) == 1:
        return months[0].title()
    return value.strip()

def standardize_sun(value):
    if not value: return None
    parts = re.split(r",|;| or ", value)
    return ", ".join([p.strip().capitalize() for p in parts if p.strip()])

def generate_key(botanical_name: str, used_keys: set[str]) -> str:
    parts = botanical_name.strip().split()
    if len(parts) < 2:
        return botanical_name[:2].upper()

    genus = parts[0].capitalize()
    species = parts[1].lower()

    base = f"{genus[0]}{species[0].upper()}"
    if base not in used_keys:
        used_keys.add(base)
        return base

    alt = f"{genus[0]}{species[:2].capitalize()}"
    if alt not in used_keys:
        used_keys.add(alt)
        return alt

    suffix = 1
    while f"{alt}{suffix}" in used_keys:
        suffix += 1
    key = f"{alt}{suffix}"
    used_keys.add(key)
    return key



def pdf_lookup(name: str, page_hint: int | None):
    data = {k: None for k in FIELDS}
    page_found = None

    with pdfplumber.open(PDF_PATH) as pdf:
        pages_to_check = []

        if isinstance(page_hint, int) and 1 <= page_hint <= len(pdf.pages):
            if page_hint in [21, 22]:
                return data, page_hint
            pages_to_check = [page_hint - 1]
        else:
            pages_to_check = list(range(len(pdf.pages)))

        for i in pages_to_check:
            page = pdf.pages[i]
            text = page.extract_text() or ""
            page_found = i + 1

            if "Appearance:" not in text:
                continue

            lines = text.splitlines()
            start = next((j for j, l in enumerate(lines) if "Appearance:" in l), None)
            if start is None: continue

            for line in lines[start + 1:]:
                if line.strip() == "" or re.match(r"^[A-Z][a-z]+:", line): break
                line = line.strip("•–—- ").replace("–", "-")

                if "height" in line.lower():
                    m = re.search(r"height\s*[-–]\s*([\d\.\- to]+)\s*ft", line, re.I)
                    if m: data["height"] = standardize_height(m.group(1))
                elif "spread" in line.lower():
                    m = re.search(r"spread\s*[-–]\s*([\d\.\- to]+)\s*ft", line, re.I)
                    if m: data["spread"] = standardize_height(m.group(1))
                elif "flower color" in line.lower():
                    m = re.search(r"flower color\s*[-–]\s*(.+)", line, re.I)
                    if m: data["color"] = standardize_color(m.group(1))
                elif "flowering period" in line.lower():
                    m = re.search(r"flowering period\s*[-–]\s*(.+)", line, re.I)
                    if m: data["bloom"] = standardize_bloom_time(m.group(1))

            # Additional fields
            if m := re.search(r"Sun:\s*([^\n]+)", text): data["sun"] = standardize_sun(m.group(1))
            if m := re.search(r"Water:\s*([^\n]+)", text): data["water"] = m.group(1).strip()
            if m := re.search(r"Wetland Status:\s*([^\n]+)", text): data["wet"] = m.group(1).strip()
            if m := re.search(r"Habitats?:\s*([^\n]+)", text): data["habitat"] = m.group(1).strip()
            if m := re.search(r"Characteristics?:\s*([^\n]+)", text): data["char"] = m.group(1).strip()
            if m := re.search(r"(Attracts [^\n]+)", text): data["wildlife"] = m.group(1).strip().strip(".")
            if m := re.search(r"Distribution:\s*([^\n]+)", text): data["dist"] = m.group(1).strip()
            if m := re.search(r"Type:\s*([^\n]+)", text): data["type"] = m.group(1).strip()
            if m := re.search(r"Plant Type:\s*([^\n]+)", text): data["planttype"] = m.group(1).strip()
            break

    return data, page_found

def main():
    df = pd.read_csv(INPUT_CSV)
    used_keys = set()

    for col in list(FIELDS.values()) + ["Page in PDF", "Key"]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = df[col].astype("object")

    for idx in tqdm(df.index, desc="PDF scrape"):
        name = df.at[idx, "Botanical Name"]
        page_val = df.at[idx, "Page in PDF"]
        page_hint = int(page_val) if pd.notna(page_val) and str(page_val).isdigit() else None

        existing = df.loc[idx, list(FIELDS.values())]
        pdf_data, page = pdf_lookup(name, page_hint)

        for key, col in FIELDS.items():
            df.at[idx, col] = existing[col] if pd.notna(existing[col]) and str(existing[col]).strip() else pdf_data.get(key)

        if pd.isna(df.at[idx, "Page in PDF"]):
            df.at[idx, "Page in PDF"] = page

        # Generate and set key
        df.at[idx, "Key"] = generate_key(name, used_keys)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f" Done. Output saved to: {OUTPUT_CSV.name}")

if __name__ == "__main__":
    main()
