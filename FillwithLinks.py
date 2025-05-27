#!/usr/bin/env python3
# ─ FillwithLinks.py ─────────────────────────────────────────────────────────
# 2025-05-27 patch 2:  range-standardisation and tidy Sun / Water columns
# ---------------------------------------------------------------------------

from __future__ import annotations
import re, csv
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── config ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
INPUT_CSV  = BASE_DIR / "Plants_FROM_PDF_ONLY.csv"
OUTPUT_CSV = BASE_DIR / "Plants_COMPLETE.csv"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

# ─── helpers (generic) ─────────────────────────────────────────────────────
def fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"⚠️  {url} → {e}")
        return None


def strip_ws(val: Optional[str]) -> Optional[str]:
    if not isinstance(val, str):
        return None
    return re.sub(r"\s+", " ", val.strip()) or None


# ─── helpers (normalisation) ───────────────────────────────────────────────
def _clean_number(num_str: str) -> str:
    """Drop trailing .0 and .00, keep significant decimals."""
    num = float(num_str)
    return str(int(num)) if num.is_integer() else str(num).rstrip("0").rstrip(".")

def norm_numeric_range(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    # remove units
    text = re.sub(r"\b(feet|foot|ft\.?|')\b", "", text, flags=re.I)
    text = text.replace("–", " to ")  # en-dash variants
    parts = re.split(r"\s*to\s*", text)
    nums = [m.group() for p in parts for m in [re.search(r"[\d.]+", p)] if m]
    if not nums:
        return strip_ws(text)
    nums = [_clean_number(n) for n in nums]
    return " - ".join(nums)

def norm_month_range(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = re.sub(r"\s*(to|–)\s*", " - ", text, flags=re.I)
    return strip_ws(text.title())

def norm_conditions(text: Optional[str]) -> Optional[str]:
    """
    'Full sun to part shade'   → 'Full sun, Part shade'
    'Medium to wet'            → 'Medium, Wet'
    """
    if not text:
        return None
    text = re.sub(r"\s*(to|–)\s*", ", ", text, flags=re.I)
    parts = [p.strip().capitalize() for p in text.split(",")]
    return ", ".join(parts)

# ─── low-level grabber ─────────────────────────────────────────────────────
def _grab(text: str, label_regex: str) -> Optional[str]:
    m = re.search(fr"(?:{label_regex}):?\s*(.+)", text, re.I)
    return strip_ws(m.group(1).split("\n", 1)[0]) if m else None


# ─── Missouri Botanical Garden parser ──────────────────────────────────────
def parse_mbg(html: str) -> dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return {
        "Height (ft)":       norm_numeric_range(_grab(text, "Height")),
        "Spread (ft)":       norm_numeric_range(_grab(text, "Spread")),
        "Bloom Color":       _grab(text, "Bloom Description"),
        "Bloom Time":        norm_month_range(_grab(text, "Bloom Time")),
        "Sun":               norm_conditions(_grab(text, "Sun")),
        "Water":             norm_conditions(_grab(text, "Water")),
        "Wetland Status":    strip_ws(_grab(text, "Wetland Status")),
        "Habitats":          _grab(text, "Habitats?"),
        "Characteristics":   _grab(text, "Characteristics?"),
        "Wildlife Benefits": _grab(text, "Attracts"),
        "Distribution":      _grab(text, "Native Range|Distribution"),
        "Plant Type":        _grab(text, "Type"),
        "Type":              _grab(text, "Type"),
    }


# ─── Wildflower.org parser ────────────────────────────────────────────────
def parse_wildflower(html: str) -> dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return {
        "Height (ft)":       norm_numeric_range(_grab(text, "Height")),
        "Spread (ft)":       norm_numeric_range(_grab(text, "Spread")),
        "Bloom Color":       _grab(text, "Bloom Color"),
        "Bloom Time":        norm_month_range(_grab(text, "Bloom Time")),
        "Sun":               norm_conditions(_grab(text, "Sun")),
        "Water":             norm_conditions(_grab(text, "Moisture")),
        "Distribution":      _grab(text, "USDA Native Status|Distribution"),
        "Wildlife Benefits": _grab(text, "Attracts"),
    }


# ─── main workflow ─────────────────────────────────────────────────────────
def main() -> None:
    df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Website Fill"):
        # MBG pass
        mbg_url = row.get("Link: Missouri Botanical Garden", "").strip()
        if mbg_url:
            html = fetch(mbg_url)
            if html:
                for k, v in parse_mbg(html).items():
                    if v and not row.get(k):
                        df.at[idx, k] = v

        # Wildflower pass
        wf_url = row.get("Link: Wildflower.org", "").strip()
        if wf_url:
            html = fetch(wf_url)
            if html:
                for k, v in parse_wildflower(html).items():
                    if v and not row.get(k):
                        df.at[idx, k] = v

    df.to_csv(OUTPUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Done.  Output saved to {OUTPUT_CSV.name}")


if __name__ == "__main__":
    main()
