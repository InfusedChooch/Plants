# path: PDFScrape.py
# Patched 2025-05-28g  ——  ignore “Plant Fact Sheet” (and similar headers)
# so page 21 resolves to:
# 21,Herbaceous, Perennial,HH,Heliopsis helianthoides,SMOOTH OXEYE,…

import re, csv
from pathlib import Path
from typing import Set, List, Dict
import pandas as pd
import pdfplumber
from tqdm import tqdm

# ─── paths ────────────────────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent
PDF_PATH = BASE / "Plant Guid Data Base.pdf"
OUT_CSV  = BASE / "Plants_Nolinks.csv"

# ─── output columns (fixed order) ─────────────────────────────────────────
COLUMNS = [
    "Page in PDF", "Plant Type", "Key",
    "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)",
    "Bloom Color", "Bloom Time", "Sun", "Water",
    "Characteristics", "Habitats",
    "Wildlife Benefits", "Distribution",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
]

# ─── PDF page-ranges → plant-type labels ──────────────────────────────────
PAGE_TYPE_MAP = {
    "Herbaceous, Perennial"       : set(range(3, 53)),
    "Ferns"                       : set(range(54, 61)),
    "Grasses, Sedges, and Rushes" : set(range(62, 81)),
    "Shrubs"                      : set(range(82, 111)),
    "Trees"                       : set(range(112, 118)),
}
def plant_type(p: int) -> str:
    return next((lbl for lbl, pages in PAGE_TYPE_MAP.items() if p in pages), "")

# ─── regex helpers ────────────────────────────────────────────────────────
BOT_LINE_RE = re.compile(
    r"^[A-Z][A-Za-z×\-]+"             # Genus
    r"\s+[A-Za-z×\-]*[a-z][A-Za-z×\-]*"   # species (contains lowercase)
    r"(?:\s+[A-Za-z×\-]+){0,3}$"
)
BOT_ANY_RE = re.compile(
    r"\b([A-Z][A-Za-z×\-]+ [A-Za-z×\-]*[a-z][A-Za-z×\-]*(?: [A-Za-z×\-]+){0,3})\b"
)

STOPWORDS = {
    # line-level and page-wide exclusions
    "Plant Fact", "Plant Fact Sheet", "Plant Symbol", "Plant Materials",
    "Plant Materials Programs", "Plant Fact Sheet",  # NB: no-break space variant
    "Contributed by",
}

HEIGHT_RE = re.compile(
    r"height[^:;\n]*?(?:up to\s*)?"
    r"([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I
)
SPREAD_RE = re.compile(
    r"(?:spread|aerial spread)[^:;\n]*?(?:up to\s*)?"
    r"([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I
)

def clean(line: str) -> str:
    return re.split(r"[,(–-]", line, 1)[0].strip()

def is_all_caps_common(l: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9\s\-]{1,}$", l)) and 1 <= len(l.split()) <= 5

def guess_common(lines: List[str], bot_idx: int) -> str:
    # look upward first (for all-caps lines like “SMOOTH OXEYE”)
    for i in range(bot_idx - 1, max(-1, bot_idx - 6), -1):
        ln = lines[i]
        if is_all_caps_common(ln) and "PLANT" not in ln and "DESCRIPTION" not in ln:
            return ln
    # then downward
    for ln in lines[bot_idx + 1:]:
        lower = ln.lower()
        if ("plant symbol" in lower) or ("description" in lower) or ("contributed by" in lower):
            continue
        return ln
    return ""

def gen_key(bot_name: str, used: Set[str]) -> str:
    g, s = bot_name.split()[:2]
    base = (g[0] + s[0]).upper()
    suffix, i = "", 1
    while base + suffix in used:
        suffix = str(i); i += 1
    used.add(base + suffix)
    return base + suffix

# ─── extraction loop ──────────────────────────────────────────────────────
def extract_rows() -> List[Dict[str, str]]:
    rows, used_keys = [], set()
    skip_pages = {1, 2, 22}

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, pg in enumerate(tqdm(pdf.pages, desc="Scanning PDF")):
            page_num = idx + 1
            if page_num in skip_pages:
                continue

            text  = pg.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

            # 1️⃣ strict scan among the first 15 lines
            bot_idx = None
            for i, ln in enumerate(lines[:15]):
                if any(sw in ln for sw in STOPWORDS):
                    continue
                cand = clean(ln)
                if BOT_LINE_RE.match(cand):
                    bot_idx = i
                    break

            # 2️⃣ fallback: first Latin pair on the page not in STOPWORDS
            if bot_idx is None:
                for m in BOT_ANY_RE.finditer(text):
                    cand = m.group(1)
                    if any(sw in cand for sw in STOPWORDS):
                        continue
                    bot_idx = -1
                    lines.insert(0, clean(cand))
                    break
            if bot_idx is None:
                continue

            bot_name = clean(lines[bot_idx])
            com_name = guess_common(lines, bot_idx)
            body     = "\n".join(lines)

            height = spread = ""
            if (m := HEIGHT_RE.search(body)):
                height = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)
            if (m := SPREAD_RE.search(body)):
                spread = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)

            rows.append({
                "Page in PDF"          : str(page_num),
                "Plant Type"           : plant_type(page_num),
                "Key"                  : gen_key(bot_name, used_keys),
                "Botanical Name"       : bot_name,
                "Common Name"          : com_name,
                "Height (ft)"          : height,
                "Spread (ft)"          : spread,
                **{c: "" for c in COLUMNS if c not in {
                    "Page in PDF", "Plant Type", "Key",
                    "Botanical Name", "Common Name",
                    "Height (ft)", "Spread (ft)",
                }},
            })
    return rows

def main() -> None:
    df = pd.DataFrame(extract_rows(), columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Saved → {OUT_CSV.name} ({len(df)} rows)")

if __name__ == "__main__":
    main()
