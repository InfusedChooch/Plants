#!/usr/bin/env python3
"""
PDFScrape.py  –  updated to strip plant-type labels from the “Characteristics” field.
"""

import re
from pathlib import Path
from typing import Dict, Tuple, Set, Optional

import pandas as pd
import pdfplumber
from tqdm import tqdm

# ─── paths ────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent
IN_CSV    = BASE / "Plants and Links.csv"
PDF_PATH  = BASE / "Plant Guid Data Base.pdf"
OUT_CSV   = BASE / "Plants_FROM_PDF_ONLY.csv"

# ─── 17-column schema ─────────────────────────────────────────────────────
FINAL_COLS = [
    "Page in PDF", "Plant Type", "Key", "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)", "Bloom Color", "Bloom Time",
    "Sun", "Water", "Characteristics", "Habitats",
    "Wildlife Benefits", "Distribution",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
]

FIELDS: Dict[str, str] = {
    "height"    : "Height (ft)",
    "spread"    : "Spread (ft)",
    "color"     : "Bloom Color",
    "bloom"     : "Bloom Time",
    "sun"       : "Sun",
    "water"     : "Water",
    "habitat"   : "Habitats",
    "char"      : "Characteristics",
    "wildlife"  : "Wildlife Benefits",
    "dist"      : "Distribution",
    "planttype" : "Plant Type",
}

# ─── keywords to strip from Characteristics ───────────────────────────────
PLANT_TYPE_WORDS: set[str] = {
    # major groups
    "herbaceous", "perennial", "annual", "biennial",
    "fern", "grass", "sedge", "rush",
    "shrub", "tree",
    # qualifiers / modifiers
    "deciduous", "evergreen", "persistent", "nonpersistent", "semi-persistent",
    "broad-leaved", "broad-leafed", "native",
    # catch-alls
    "plant", "plants",
}

# ─── tiny formatters (unchanged) ──────────────────────────────────────────
def _range(txt: str | None) -> str | None:
    if not txt: return None
    txt = txt.replace("–", "-").replace("to", "-")
    nums = re.findall(r"[\d.]+", txt)
    return f"{nums[0]} - {nums[1]}" if len(nums) == 2 else txt.strip()

def _colors(txt: str | None) -> str | None:
    if not txt: return None
    return re.sub(r"\s*/\s*", "/", txt.replace(",", "/")
                                   .replace(" and ", "/")
                                   .replace(" or ", "/").strip())

def _bloom(txt: str | None) -> str | None:
    if not txt: return None
    months = re.findall(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)",
        txt, re.I)
    return f"{months[0].title()} - {months[1].title()}" if len(months) >= 2 \
        else months[0].title() if months else txt.strip()

def _sun(txt: str | None) -> str | None:
    if not txt: return None
    parts = re.split(r",|;| or ", txt.lower())
    return ", ".join(p.strip().capitalize() for p in parts if p.strip())

# ─── NEW: strip plant-type words from Characteristics ─────────────────────
def _strip_types(txt: str | None) -> str | None:
    """
    Remove generic plant-type descriptors (herbaceous, shrub, tree, etc.)
    and return the remaining descriptors joined by '; '.
    """
    if not txt: return None
    cleaned: list[str] = []
    for piece in re.split(r"[;,]", txt):          # split on ; or ,
        piece_clean = piece.strip()
        if not piece_clean:
            continue
        # keep token only if it contains none of the banned keywords
        low = piece_clean.lower()
        if not any(word in low for word in PLANT_TYPE_WORDS):
            cleaned.append(piece_clean)
    return "; ".join(dict.fromkeys(cleaned)) or None  # ordered de-dupe

# ─── key generator (unchanged from last fix) ──────────────────────────────
def _gen_key(bot_name: str, used: Set[str]) -> str:
    genus, *rest = bot_name.split()
    species = rest[0] if rest else ""
    base = (
        genus[0].upper() +
        (species[:1].upper() if species else "") +
        (species[1:2].lower() if len(species) > 1 else "")
    )
    if base not in used:
        used.add(base); return base
    n = 1
    while f"{base}{n}" in used: n += 1
    key = f"{base}{n}"
    used.add(key); return key

# ─── PDF scraping helper (unchanged except for _strip_types call) ─────────
def pdf_lookup(name: str, hint: Optional[int]) -> Tuple[Dict[str, str | None], int | None]:
    data = {k: None for k in FIELDS}
    found_page = None

    with pdfplumber.open(PDF_PATH) as pdf:
        pages = ([hint-1] if hint and 1 <= hint <= len(pdf.pages) and hint not in (21, 22)
                 else [i for i in range(len(pdf.pages)) if i + 1 not in (21, 22)])

        for i in pages:
            page = pdf.pages[i]
            txt = page.extract_text() or ""
            if "Appearance:" not in txt:
                continue
            found_page = i + 1

            lines = txt.splitlines()
            start = next((j for j, l in enumerate(lines) if "Appearance:" in l), None)
            if start is None: continue
            for ln in lines[start+1:]:
                ln = ln.strip("•–—- ").replace("–", "-")
                if not ln or re.match(r"^[A-Z][a-z]+:", ln): break
                ll = ln.lower()

                if "height" in ll and (m:=re.search(r"height\s*[-–]\s*([\d.\- to]+)\s*ft", ll)):
                    data["height"] = _range(m.group(1))
                elif "spread" in ll and (m:=re.search(r"spread\s*[-–]\s*([\d.\- to]+)\s*ft", ll)):
                    data["spread"] = _range(m.group(1))
                elif "flower color" in ll and (m:=re.search(r"flower color\s*[-–]\s*(.+)", ln, flags=re.I)):
                    data["color"] = _colors(m.group(1))
                elif "flowering period" in ll and (m:=re.search(r"flowering period\s*[-–]\s*(.+)", ln, flags=re.I)):
                    data["bloom"] = _bloom(m.group(1))

            grabs = [
                ("sun",       r"Sun:\s*([^\n]+)",            _sun),
                ("water",     r"Water:\s*([^\n]+)",          str.strip),
                ("habitat",   r"Habitats?:\s*([^\n]+)",      str.strip),
                ("char",      r"Characteristics?:\s*([^\n]+)", _strip_types),
                ("wildlife",  r"(Attracts [^\n]+)",          lambda x: x.strip().rstrip(".")),
                ("dist",      r"Distribution:\s*([^\n]+)",   str.strip),
                ("planttype", r"Plant Type:\s*([^\n]+)",     str.strip),
            ]
            for k, pat, fn in grabs:
                if not data[k] and (m:=re.search(pat, txt)):
                    data[k] = fn(m.group(1))
            break
    return data, found_page

# ─── main routine (unchanged) ─────────────────────────────────────────────
def main() -> None:
    df = pd.read_csv(IN_CSV, dtype=str).fillna("")
    for col in FINAL_COLS:
        if col not in df.columns:
            df[col] = ""
    used: Set[str] = set()

    for idx in tqdm(df.index, desc="PDF scrape"):
        name = df.at[idx, "Botanical Name"]
        hint = int(df.at[idx, "Page in PDF"]) if str(df.at[idx, "Page in PDF"]).isdigit() else None
        scraped, page = pdf_lookup(name, hint)

        for k, csv_col in FIELDS.items():
            if not df.at[idx, csv_col]:
                df.at[idx, csv_col] = scraped[k] or ""

        if not df.at[idx, "Page in PDF"]:
            df.at[idx, "Page in PDF"] = page or ""
        if not df.at[idx, "Key"]:
            df.at[idx, "Key"] = _gen_key(name, used)

    df = df[FINAL_COLS]
    df.to_csv(OUT_CSV, index=False)
    print(f"✅  Saved → {OUT_CSV.name}")

if __name__ == "__main__":
    main()
