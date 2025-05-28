# /plants/PDFScrape.py
# Scrapes Rutgers PDF and fills out core plant info columns

import re
from pathlib import Path
from typing import Dict, Tuple, Set, Optional

import pandas as pd
import pdfplumber
from tqdm import tqdm

BASE      = Path(__file__).resolve().parent
IN_CSV    = BASE / "Plants and Links.csv"
PDF_PATH  = BASE / "Plant Guid Data Base.pdf"
OUT_CSV   = BASE / "Plants_FROM_PDF_ONLY.csv"

FINAL_COLS = [
    "Page in PDF", "Plant Type", "Key", "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)", "Bloom Color", "Bloom Time",
    "Sun", "Water", "Characteristics", "Habitats",
    "Wildlife Benefits", "Distribution",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
]

FIELDS = {
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

PLANT_TYPE_WORDS = {
    "herbaceous", "perennial", "annual", "biennial",
    "fern", "grass", "sedge", "rush", "shrub", "tree",
    "deciduous", "evergreen", "persistent", "nonpersistent", "semi-persistent",
    "broad-leaved", "broad-leafed", "native", "plant", "plants",
    "full sun", "partial shade", "part shade", "shade"
}

def _range(txt): 
    if not txt: return None
    txt = txt.replace("–", "-").replace("to", "-")
    nums = re.findall(r"[\d.]+", txt)
    return f"{nums[0]} - {nums[1]}" if len(nums) >= 2 else txt.strip()

def _colors(txt): 
    return re.sub(r"\s*/\s*", "/", txt.replace(",", "/").replace(" and ", "/").replace(" or ", "/").strip()) if txt else None

def _bloom(txt): 
    if not txt: return None
    months = re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)", txt, re.I)
    return f"{months[0].title()} - {months[1].title()}" if len(months) >= 2 else months[0].title() if months else txt.strip()

def _sun(txt: str | None) -> str | None:
    if not txt: return None
    txt = txt.lower()
    sun_opts = []
    if "full sun" in txt: sun_opts.append("Full sun")
    if "part shade" in txt or "partial shade" in txt: sun_opts.append("Part shade")
    if "shade" in txt and "part shade" not in txt and "partial shade" not in txt: sun_opts.append("Shade")
    return ", ".join(sorted(set(sun_opts))) if sun_opts else None

def _strip_types(txt): 
    if not txt: return None
    cleaned = []
    for piece in re.split(r"[;,]", txt):
        piece_clean = piece.strip()
        if piece_clean and not any(word in piece_clean.lower() for word in PLANT_TYPE_WORDS):
            cleaned.append(piece_clean)
    return "; ".join(dict.fromkeys(cleaned)) or None

def _parse_types(raw): 
    words = set(w.strip().capitalize() for w in re.split(r"[;,]", raw) if w.strip().lower() in PLANT_TYPE_WORDS)
    return ", ".join(sorted(words)) if words else None

def _gen_key(bot_name: str, used: Set[str]) -> str:
    genus, *rest = bot_name.strip().split()
    species = rest[0] if rest else ""
    base = genus[0].upper() + species[0].upper() if species else ""
    if base not in used:
        used.add(base)
        return base
    n = 1
    while f"{base}{n}" in used:
        n += 1
    key = f"{base}{n}"
    used.add(key)
    return key

def pdf_lookup(name: str, hint: Optional[int]) -> Tuple[Dict[str, str | None], int | None]:
    data = {k: None for k in FIELDS}
    found_page = None

    with pdfplumber.open(PDF_PATH) as pdf:
        pages = [hint-1] if hint and 1 <= hint <= len(pdf.pages) else list(range(len(pdf.pages)))
        for i in pages:
            page = pdf.pages[i]
            txt = page.extract_text() or ""
            if name.lower() not in txt.lower() or "Appearance:" not in txt:
                continue
            found_page = i + 1
            lines = txt.splitlines()
            body = "\n".join(lines)

            # From "Appearance" block
            start = next((j for j, l in enumerate(lines) if "Appearance:" in l), None)
            for ln in lines[start+1:]:
                ln = ln.strip("•–—- ")
                if not ln or re.match(r"^[A-Z][a-z]+:", ln): break
                ll = ln.lower()
                if "height" in ll and (m := re.search(r"height\s*[-–]\s*([\d.\- to]+)\s*ft", ll)):
                    data["height"] = _range(m.group(1))
                elif "spread" in ll and (m := re.search(r"spread\s*[-–]\s*([\d.\- to]+)\s*ft", ll)):
                    data["spread"] = _range(m.group(1))
                elif "flower color" in ll and (m := re.search(r"flower color\s*[-–]\s*(.+)", ln, re.I)):
                    data["color"] = _colors(m.group(1))
                elif "flowering period" in ll and (m := re.search(r"flowering period\s*[-–]\s*(.+)", ln, re.I)):
                    data["bloom"] = _bloom(m.group(1))
                elif "sun exposure" in ll or "prefers" in ll:
                    sun_guess = _sun(ln)
                    if sun_guess:
                        data["sun"] = sun_guess

            # From whole page body
            grabs = [
                ("sun",       r"Sun:\s*([^\n]+)",            _sun),
                ("water",     r"Water:\s*([^\n]+)",          str.strip),
                ("habitat",   r"Habitats?:\s*([^\n]+)",      str.strip),
                ("char",      r"Characteristics?:\s*([^\n]+)", _strip_types),
                ("planttype", r"Characteristics?:\s*([^\n]+)", _parse_types),
                ("wildlife",  r"(Attracts [^\n]+)",          lambda x: x.strip().rstrip(".")),
                ("dist",      r"USDA hardiness zones?\s*(\d+\s*[-–]\s*\d+)", lambda x: f"USDA Hardiness Zone {x.strip()}"),
            ]
            for k, pat, fn in grabs:
                if not data[k] and (m := re.search(pat, body, re.I)):
                    data[k] = fn(m.group(1))

            return data, found_page
    return data, None

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
