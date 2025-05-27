# plants/FillwithLinks.py
# Fills missing fields by scraping Missouri Botanical Garden & Wildflower.org

from __future__ import annotations
import re, csv, time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── configuration ──────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
INPUT_CSV       = BASE_DIR / "Plants_FROM_PDF_ONLY.csv"
MASTER_CSV      = BASE_DIR / "Plants and Links.csv"         # for column order
OUTPUT_CSV      = BASE_DIR / "Plants_COMPLETE.csv"
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN   = 1.2                                       # be kind to servers

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ─── generic helpers ───────────────────────────────────────────────────────
def fetch(url: str) -> Optional[str]:
    """Return HTML text or None on error (prints a warning)."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        print(f"⚠️  {url} → {exc}")
        return None


def ws(val: Optional[str]) -> Optional[str]:
    """Collapse whitespace; return None for N/A values."""
    if not isinstance(val, str):
        return None
    return re.sub(r"\s+", " ", val.strip()) or None


# ─── normalisation helpers ─────────────────────────────────────────────────
def _fmt_num(num_str: str) -> str:
    """'3.00'→'3', '2.50'→'2.5'.  Returns original text if float() fails."""
    try:
        n = float(num_str)
        return str(int(n)) if n.is_integer() else str(n).rstrip("0").rstrip(".")
    except Exception:
        return num_str.strip()


def norm_numeric_range(txt: Optional[str]) -> Optional[str]:
    """Convert '1.0 to 2.00 feet' → '1 - 2'."""
    if not txt:
        return None
    txt = re.sub(r"\b(feet|foot|ft\.?|')\b", "", txt, flags=re.I)
    txt = txt.replace("–", " to ")
    nums = [m.group() for m in re.finditer(r"[\d.]+", txt)]
    if len(nums) >= 2:
        return f"{_fmt_num(nums[0])} - {_fmt_num(nums[1])}"
    if nums:
        return _fmt_num(nums[0])
    return ws(txt)


def norm_month_range(txt: Optional[str]) -> Optional[str]:
    """'April to June' → 'April - June' (title-case)."""
    if not txt:
        return None
    txt = re.sub(r"\s*(to|–)\s*", " - ", txt, flags=re.I)
    return ws(txt.title())


def norm_conditions(txt: Optional[str]) -> Optional[str]:
    """
    'full sun to part shade' → 'Full sun, Part shade'
    Handles 'to', 'and', 'or', ',', ';' as delimiters.
    """
    if not txt:
        return None
    txt = (
        txt.lower()
        .replace(" to ", ",")
        .replace(" and ", ",")
        .replace(" or ", ",")
        .replace(";", ",")
    )
    parts: list[str] = []
    for item in txt.split(","):
        item = item.strip()
        if item and item not in parts:       # ordered de-dupe
            parts.append(item)
    return ", ".join(p.capitalize() for p in parts)


def _grab(text: str, label: str) -> Optional[str]:
    """
    Extract everything after '<label>:'
    `label` may be an alternation, e.g. 'Native Range|Distribution'.
    """
    m = re.search(fr"(?:{label}):?\s*(.+)", text, flags=re.I)
    return ws(m.group(1).split("\n", 1)[0]) if m else None


# ─── MBG + Wildflower parsers ──────────────────────────────────────────────
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
        "Wetland Status":    _grab(text, "Wetland Status"),
        "Habitats":          _grab(text, "Habitats?"),
        "Characteristics":   _grab(text, "Characteristics?"),
        "Wildlife Benefits": _grab(text, "Attracts"),
        "Distribution":      _grab(text, "Native Range|Distribution"),
        "Plant Type":        _grab(text, "Type"),
        "Type":              _grab(text, "Type"),
    }


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
            time.sleep(SLEEP_BETWEEN)

        # Wildflower pass
        wf_url = row.get("Link: Wildflower.org", "").strip()
        if wf_url:
            html = fetch(wf_url)
            if html:
                for k, v in parse_wildflower(html).items():
                    if v and not row.get(k):
                        df.at[idx, k] = v
            time.sleep(SLEEP_BETWEEN)

    # ── final column order = master CSV header + any new columns  ───────────
    try:
        template_cols = list(pd.read_csv(MASTER_CSV, nrows=0).columns)
        extra_cols = [c for c in df.columns if c not in template_cols]
        df = df[template_cols + extra_cols]
    except Exception:
        pass  # if master CSV missing, keep current order

    df.to_csv(OUTPUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Done.  Output saved to {OUTPUT_CSV.name}")


if __name__ == "__main__":
    main()
