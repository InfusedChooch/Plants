# PDFScraper.py ─ Extracts basic plant rows from the Rutgers PDF
# Patched 2025-05-28g —  ignore “Plant Fact Sheet” headers so page 21 resolves correctly

import re, csv                  # std-lib regex and CSV helpers
from pathlib import Path        # portable filesystem paths
from typing import Set, List, Dict  # type hints
import pandas as pd             # DataFrame handling
import pdfplumber               # lightweight PDF text extraction
from tqdm import tqdm           # progress-bar for loops

# ─── Paths ───────────────────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent      # folder containing this script
PDF_PATH = BASE / "Plant Guide Data Base.pdf"    # source guide
OUT_CSV  = BASE / "Plants_Nolinks.csv"          # destination file

# ─── Column Order (fixed) ────────────────────────────────────────────────
COLUMNS = [
    "Page in PDF", "Plant Type", "Key",
    "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)",
    "Bloom Color", "Bloom Time", "Sun", "Water",
    "Characteristics", "Habitats",
    "Wildlife Benefits", "Distribution",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
]

# ─── Page-range → Plant-type Map ─────────────────────────────────────────
PAGE_TYPE_MAP = {
    "Herbaceous, Perennial"       : set(range(3, 53)),
    "Ferns"                       : set(range(54, 61)),
    "Grasses, Sedges, and Rushes" : set(range(62, 81)),
    "Shrubs"                      : set(range(82, 111)),
    "Trees"                       : set(range(112, 118)),
}
def plant_type(p: int) -> str:               # return label for page number
    return next((lbl for lbl, pages in PAGE_TYPE_MAP.items() if p in pages), "")

# ─── Regex Helpers ───────────────────────────────────────────────────────
BOT_LINE_RE = re.compile(        # strict “Genus species” line at start of page
    r"^[A-Z][A-Za-z×\-]+\s+[A-Za-z×\-]*[a-z][A-Za-z×\-]*(?:\s+[A-Za-z×\-]+){0,3}$")
BOT_ANY_RE = re.compile(         # fallback: any Latin binomial on page
    r"\b([A-Z][A-Za-z×\-]+ [A-Za-z×\-]*[a-z][A-Za-z×\-]*(?: [A-Za-z×\-]+){0,3})\b")

STOPWORDS = {                    # text that should never be parsed as names
    "Plant Fact", "Plant Fact Sheet", "Plant Symbol", "Plant Materials",
    "Plant Materials Programs", "Plant Fact Sheet", "Contributed by",
}

# extract single/dual numbers like “1-2 ft” or “up to 5 ft”
HEIGHT_RE = re.compile(r"height[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)
SPREAD_RE = re.compile(r"(?:spread|aerial spread)[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)

def clean(line: str) -> str:            # remove trailing punctuation/notes
    return re.split(r"[,(–-]", line, 1)[0].strip()

def is_all_caps_common(l: str) -> bool: # heuristic: “SMOOTH OXEYE” lines
    return bool(re.fullmatch(r"[A-Z][A-Z0-9\s\-]{1,}$", l)) and 1 <= len(l.split()) <= 5

def guess_common(lines: List[str], bot_idx: int) -> str:  # find common name near bot idx
    for i in range(bot_idx - 1, max(-1, bot_idx - 6), -1):     # search upward
        ln = lines[i]
        if is_all_caps_common(ln) and "PLANT" not in ln and "DESCRIPTION" not in ln:
            return ln
    for ln in lines[bot_idx + 1:]:                             # then downward
        lower = ln.lower()
        if ("plant symbol" in lower) or ("description" in lower) or ("contributed by" in lower):
            continue
        return ln
    return ""

def gen_key(bot_name: str, used: Set[str]) -> str:  # unique 2-letter key (Genus+species)
    g, s = bot_name.split()[:2]
    base = (g[0] + s[0]).upper()
    suffix, i = "", 1
    while base + suffix in used:      # increment until unused
        suffix = str(i); i += 1
    used.add(base + suffix)
    return base + suffix

# ─── Core Extraction Loop ────────────────────────────────────────────────
def extract_rows() -> List[Dict[str, str]]:
    rows, used_keys = [], set()
    skip_pages = {1, 2, 22}           # cover indices / legal notice

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, pg in enumerate(tqdm(pdf.pages, desc="Scanning PDF")):
            page_num = idx + 1
            if page_num in skip_pages:                 # skip non-data pages
                continue

            text  = pg.extract_text() or ""            # raw page text
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]  # list of lines

            # 1️⃣ strict scan first 15 lines for perfect Latin header
            bot_idx = None
            for i, ln in enumerate(lines[:15]):
                if any(sw in ln for sw in STOPWORDS):  # ignore headers
                    continue
                cand = clean(ln)
                if BOT_LINE_RE.match(cand):
                    bot_idx = i
                    break

            # 2️⃣ fallback: first Latin pair found anywhere
            if bot_idx is None:
                for m in BOT_ANY_RE.finditer(text):
                    cand = m.group(1)
                    if any(sw in cand for sw in STOPWORDS):
                        continue
                    bot_idx = -1
                    lines.insert(0, clean(cand))       # treat as first line
                    break
            if bot_idx is None:                       # still nothing → skip
                continue

            bot_name = clean(lines[bot_idx])          # botanical name
            com_name = guess_common(lines, bot_idx)   # common name
            body     = "\n".join(lines)               # full text for regexes

            # height / spread extraction
            height = spread = ""
            if (m := HEIGHT_RE.search(body)):
                height = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)
            if (m := SPREAD_RE.search(body)):
                spread = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)

            # assemble row dict with empty placeholders for yet-to-fill fields
            rows.append({
                "Page in PDF"    : str(page_num),
                "Plant Type"     : plant_type(page_num),
                "Key"            : gen_key(bot_name, used_keys),
                "Botanical Name" : bot_name,
                "Common Name"    : com_name,
                "Height (ft)"    : height,
                "Spread (ft)"    : spread,
                **{c: "" for c in COLUMNS if c not in {
                    "Page in PDF","Plant Type","Key",
                    "Botanical Name","Common Name",
                    "Height (ft)","Spread (ft)",
                }},
            })
    return rows

def main() -> None:                 # orchestrates extraction + CSV save
    df = pd.DataFrame(extract_rows(), columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Saved → {OUT_CSV.name} ({len(df)} rows)")

if __name__ == "__main__":          # allow CLI execution
    main()
