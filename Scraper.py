#!/usr/bin/env python3
"""
Scraper for combined plant database:
- Supports combined CSV with "Plant Type"
- Fills missing Spread, Bloom, Sun, Water, Distribution, Wildlife fields
- Uses PDF, Missouri Botanical Garden, and Wildflower.org
- Outputs updated file, plus optional per-type breakdowns
"""

from __future__ import annotations
import re, time, sys
from pathlib import Path
from typing import Optional

import pandas as pd
import pdfplumber, requests, numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
INPUT_PDF = BASE_DIR / "Plant Guid Data Base.pdf"

if len(sys.argv) > 1:
    INPUT_FILE = Path(sys.argv[1]).expanduser().resolve()
else:
    INPUT_FILE = BASE_DIR / "plant_database_combined.csv"

OUTPUT_CSV = INPUT_FILE.with_name(INPUT_FILE.stem + "_COMPLETE.csv")

PDF_CACHE: dict[str, dict[str, Optional[str]]] = {}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PlantDB/1.0; +https://github.com/yourproject)"}
DELAY = 1.0

# Columns
COL_SPREAD    = "Spread (ft)"
COL_BLOOM     = "Bloom Time"
COL_SUN       = "Sun"
COL_WATER     = "Water"
COL_DIST      = "Distribution"
COL_WILDLIFE  = "Wildlife Benefits"
COL_LINK_MB   = "Link: Missouri Botanical Garden"
COL_LINK_WF   = "Link: Wildflower.org"

ALL_TARGET_COLS = [COL_SPREAD, COL_BLOOM, COL_SUN, COL_WATER, COL_DIST, COL_WILDLIFE]

def safe_first(*vals):
    for v in vals:
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if isinstance(v, (pd.NA.__class__, np.generic)) and pd.isna(v):
            continue
        return v
    return pd.NA

def pdf_lookup(botanical: str) -> dict[str, Optional[str]]:
    if botanical in PDF_CACHE:
        return PDF_CACHE[botanical]

    result = {"spread": None, "bloom": None, "wildlife": None}
    with pdfplumber.open(INPUT_PDF) as pdf:
        regex = re.compile(re.escape(botanical), re.I)
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if not regex.search(txt):
                continue
            if m := re.search(r"Spread:\s*([\d–\-. ]+)\s*ft", txt):
                result["spread"] = m.group(1).strip().replace(" ", "")
            if m := re.search(r"Bloom (Time|Period):\s*([A-Za-z ,–-]+?)\n", txt):
                result["bloom"] = re.sub(r"\s+", " ", m.group(2)).strip()
            if m := re.search(r"(Attracts [^\n]+)", txt):
                result["wildlife"] = m.group(1).rstrip(".")
            break
    PDF_CACHE[botanical] = result
    return result

def mobot_url(name: str) -> str:
    return f"https://www.missouribotanicalgarden.org/PlantFinder/PlantFinderSearchResults.aspx?query={'+'.join(name.strip().split())}"

def wildflower_url(name: str) -> str:
    return f"https://www.wildflower.org/plants/search.php?search_field=name_substring&value={'%20'.join(name.strip().split())}"

def fetch_html(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
    except Exception:
        pass
    return None

def parse_mobot(soup: BeautifulSoup) -> dict[str, Optional[str]]:
    if not soup:
        return {}
    txt = soup.select_one(".detail-info")
    txt = txt.get_text(" ", strip=True) if txt else ""
    def grab(pat): return (m := re.search(pat, txt, re.I)) and m.group(1).strip()
    return {
        "spread": grab(r"Spread:?([^;]+?)(?:Height|Zones|$)"),
        "sun":    grab(r"(Full.*?shade|Part.*?shade|Full sun)"),
        "water":  grab(r"(Dry|Medium|Moist|Wet)[^.;]*"),
        "dist":   grab(r"Native Range:?([^;]+?)(?:Height|Zones|$)"),
        "wild":   grab(r"Attracts([^.;]+)"),
        "bloom":  grab(r"Bloom Time:?([^;]+?)(?:Bloom\scolor|$)")
    }

def parse_wildflower(soup: BeautifulSoup) -> dict[str, Optional[str]]:
    if not soup:
        return {}
    tbl = soup.find("table", class_="plant-info")
    txt = tbl.get_text(" ", strip=True) if tbl else ""
    def grab(pat): return (m := re.search(pat, txt, re.I)) and m.group(1).strip()
    return {
        "spread": grab(r"Spread:?([^;]+?)(?:Height|$)"),
        "sun":    grab(r"Sun Exposure:?([^;]+?)$"),
        "water":  grab(r"Soil Moisture:?([^;]+?)$"),
        "dist":   grab(r"Native Distribution:?([^;]+?)$"),
        "wild":   grab(r"Wildlife Value:?([^;]+?)$"),
        "bloom":  grab(r"Bloom:?([^;]+?)$")
    }

def fill_row(df: pd.DataFrame, idx: int) -> None:
    name = df.at[idx, "Botanical Name"]
    pdf_d = pdf_lookup(name)
    needs_data = df.loc[idx, ALL_TARGET_COLS].isna().any()
    mobot_d, wild_d = {}, {}

    if needs_data:
        mb_url = mobot_url(name)
        mobot_d = parse_mobot(fetch_html(mb_url))
        df.at[idx, COL_LINK_MB] = f"[MBG]({mb_url})"
        time.sleep(DELAY)

    needs_data = df.loc[idx, ALL_TARGET_COLS].isna().any()
    if needs_data:
        wf_url = wildflower_url(name)
        wild_d = parse_wildflower(fetch_html(wf_url))
        df.at[idx, COL_LINK_WF] = f"[WF]({wf_url})"
        time.sleep(DELAY)

    df.at[idx, COL_SPREAD]   = safe_first(df.at[idx, COL_SPREAD],   pdf_d["spread"], mobot_d.get("spread"), wild_d.get("spread"))
    df.at[idx, COL_BLOOM]    = safe_first(df.at[idx, COL_BLOOM],    pdf_d["bloom"],   mobot_d.get("bloom"),  wild_d.get("bloom"))
    df.at[idx, COL_SUN]      = safe_first(df.at[idx, COL_SUN],      mobot_d.get("sun"),   wild_d.get("sun"))
    df.at[idx, COL_WATER]    = safe_first(df.at[idx, COL_WATER],    mobot_d.get("water"), wild_d.get("water"))
    df.at[idx, COL_DIST]     = safe_first(df.at[idx, COL_DIST],     mobot_d.get("dist"),  wild_d.get("dist"))
    df.at[idx, COL_WILDLIFE] = safe_first(df.at[idx, COL_WILDLIFE], pdf_d["wildlife"],    mobot_d.get("wild"), wild_d.get("wild"))

def main() -> None:
    if INPUT_FILE.suffix.lower() == ".xlsx":
        df = pd.read_excel(INPUT_FILE, engine="openpyxl")
    else:
        df = pd.read_csv(INPUT_FILE)

    if "Plant Type" not in df.columns:
        print("⚠️  No 'Plant Type' column found. Continuing anyway...")

    for col in (COL_LINK_MB, COL_LINK_WF):
        if col not in df.columns:
            df[col] = pd.NA

    for idx in tqdm(df.index, desc=f"Filling: {INPUT_FILE.name}"):
        if df.loc[idx, ALL_TARGET_COLS].isna().any():
            fill_row(df, idx)

    # Save full combined CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"✔ Combined output saved → {OUTPUT_CSV.name}")

    # Optional: write per-type breakdowns
    if "Plant Type" in df.columns:
        for plant_type, sub_df in df.groupby("Plant Type"):
            name = plant_type.replace(",", "").replace(" ", "_").lower() + "_COMPLETE.csv"
            sub_df.to_csv(INPUT_FILE.with_name(name), index=False, encoding="utf-8")
            print(f"  └─ {plant_type} saved as {name}")

if __name__ == "__main__":
    main()
