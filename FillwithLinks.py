# plants/FillwithLinks.py
# Fills in plant data by scraping MBG + Wildflower.org,
# with formatting consistent with PDFScrape.py

from __future__ import annotations
import re, csv, time
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── paths ─────────────────────────────────────────────────────────────────
BASE         = Path(__file__).resolve().parent
IN_CSV       = BASE / "Plants_FROM_PDF_ONLY.csv"
MASTER_CSV   = BASE / "Plants and Links.csv"
OUT_CSV      = BASE / "Plants_COMPLETE.csv"

# ─── scraping settings ────────────────────────────────────────────────────
UA            = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
TIMEOUT       = 30
SLEEP_BETWEEN = 1.2

# ─── formatting functions ─────────────────────────────────────────────────
def ws(val: Optional[str]) -> Optional[str]:
    return re.sub(r"\s+"," ",val.strip()) if isinstance(val,str) else None

def _fmt(n: str) -> str:
    try:
        f = float(n)
        return str(int(f)) if f.is_integer() else str(f).rstrip("0").rstrip(".")
    except: return n.strip()

def rng(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    txt = re.sub(r"\b(feet|foot|ft\.?|')\b","",txt,flags=re.I).replace("–"," to ")
    nums = [m.group() for m in re.finditer(r"[\d.]+", txt)]
    return f"{_fmt(nums[0])} - {_fmt(nums[1])}" if len(nums) >= 2 else _fmt(nums[0]) if nums else ws(txt)

def month_rng(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    months = re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)", txt, re.I)
    return f"{months[0].title()} - {months[1].title()}" if len(months) >= 2 else months[0].title() if months else ws(txt)

def conditions(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    txt = txt.lower()
    sun_opts = []
    if "full sun" in txt:
        sun_opts.append("Full sun")
    if "part shade" in txt or "partial shade" in txt:
        sun_opts.append("Part shade")
    if "shade" in txt and "part shade" not in txt and "partial shade" not in txt:
        sun_opts.append("Shade")
    return ", ".join(sorted(set(sun_opts))) if sun_opts else None

def strip_types(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    TYPES = {
        "Herbaceous Perennials", "Ferns", "Grasses", "Sedges", "Rushes",
        "Shrubs", "Trees", "Grasses, Sedges, and Rushes"
    }
    for t in TYPES:
        txt = re.sub(rf"\b{re.escape(t)}\b", "", txt, flags=re.I)
    return re.sub(r"\s{2,}", " ", txt).strip(",; ").strip()

def clean_chars(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    txt = txt.lower()
    banned = ["appearance", "asclepias", "tuberosa", "incarnata", "syriaca"]
    if any(b in txt for b in banned):
        return None
    return strip_types(txt)

def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"⚠️  {url} → {e}")
        return None

def grab(txt: str, label: str) -> Optional[str]:
    pattern = rf"{label}:\s*(.*)"
    for line in txt.splitlines():
        if re.search(pattern, line, flags=re.I):
            return ws(re.sub(pattern, r"\1", line, flags=re.I))
    return None


def gen_key(bot_name: str, used: set[str]) -> str:
    genus, *rest = bot_name.strip().split()
    species = rest[0] if rest else ""
    base = genus[0].upper() + species[0].upper() if species else ""
    if base and base not in used:
        used.add(base)
        return base
    return ""  # no numbered fallback

# ─── site parsers ─────────────────────────────────────────────────────────
def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)

    # Extract individual pieces
    dist = grab(text, "USDA Native Status|Distribution")
    raw_dist = grab(text, "Native Range|Distribution")
    base_char = clean_chars(grab(text, "Characteristics?"))
    tolerate = grab(text, "Tolerate")
    maintenance = grab(text, "Maintenance")

    # Assemble final Characteristics field
    char_parts = []
    if base_char: char_parts.append(base_char)
    if tolerate: char_parts.append(tolerate.rstrip("."))
    if maintenance: char_parts.append(f"Maintenance: {maintenance}")
    full_char = "; ".join(char_parts) if char_parts else None

    return {
        "Height (ft)"      : rng(grab(text, "Height")),
        "Spread (ft)"      : rng(grab(text, "Spread")),
        "Bloom Color"      : grab(text, "Bloom Description"),
        "Bloom Time"       : month_rng(grab(text, "Bloom Time")),
        "Sun"              : conditions(grab(text, "Sun")),
        "Water"            : conditions(grab(text, "Water")),
        "Wetland Status"   : grab(text, "Wetland Status"),
        "Habitats"         : grab(text, "Habitats?"),
        "Characteristics"  : full_char,
        "Wildlife Benefits": grab(text, "Attracts"),
        "Distribution"     : (f"USDA Hardiness Zone {dist.strip()}" if dist and re.search(r"\d+\s*[-–]\s*\d+", dist) else None),
        "Plant Type"       : grab(text, "Type"),
        "Type"             : grab(text, "Type"),
    }

def parse_wf(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    dist = grab(text, "USDA Native Status|Distribution")
    return {
        "Height (ft)"      : rng(grab(text, "Height")),
        "Spread (ft)"      : rng(grab(text, "Spread")),
        "Bloom Color"      : grab(text, "Bloom Color"),
        "Bloom Time"       : month_rng(grab(text, "Bloom Time")),
        "Sun"              : conditions(grab(text, "Sun")),
        "Water"            : conditions(grab(text, "Moisture")),
        "Distribution"     : (
            f"USDA Hardiness Zone {dist.strip()}" if dist and re.search(r"\d+\s*[-–]\s*\d+", dist) else None
        ),
        "Wildlife Benefits": grab(text, "Attracts"),
        "Habitats"         : grab(text, "Native Habitat"),
    }


# ─── main workflow ────────────────────────────────────────────────────────
def main() -> None:
    df = pd.read_csv(IN_CSV, dtype=str).fillna("")
    used_keys = set(df["Key"].dropna())

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Website Fill"):
        # Assign missing Key
        if not row.get("Key"):
            df.at[idx, "Key"] = gen_key(row["Botanical Name"], used_keys)

        # MBG pass
        mbg = row.get("Link: Missouri Botanical Garden", "").strip()
        if mbg.startswith("http"):
            if html := fetch(mbg):
                for k, v in parse_mbg(html).items():
                    if v and not row.get(k):
                        df.at[idx, k] = v
            time.sleep(SLEEP_BETWEEN)

        # Wildflower pass
        wf = row.get("Link: Wildflower.org", "").strip()
        if wf.startswith("http"):
            if html := fetch(wf):
                for k, v in parse_wf(html).items():
                    if v and not row.get(k):
                        df.at[idx, k] = v
            time.sleep(SLEEP_BETWEEN)

    # Order columns
    template = list(pd.read_csv(MASTER_CSV, nrows=0).columns)
    extra = [c for c in df.columns if c not in template]
    df = df[template + extra]

    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Saved → {OUT_CSV.name}")

if __name__ == "__main__":
    main()
