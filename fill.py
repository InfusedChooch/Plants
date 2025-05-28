# fill.py ─ Pulls numeric / habitat details from MBG + Wildflower.org into CSV

from __future__ import annotations      # postpone evaluation of type hints
import csv, re, time                    # std-lib helpers
from pathlib import Path
from typing import Dict, Optional
import pandas as pd                     # CSV read-modify-write
import requests                         # HTTP
from bs4 import BeautifulSoup           # HTML parsing
from tqdm import tqdm                   # progress bar

# ─── Files & Network constants ───────────────────────────────────────────
BASE          = Path(__file__).resolve().parent
IN_CSV        = BASE / "Plants and Links.csv"      # must already contain URLs
OUT_CSV       = BASE / "Plants_COMPLETE.csv"       # output
MASTER_CSV    = IN_CSV                            # template for col order
SLEEP_BETWEEN = 0.7                               # throttle between HTTPs
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

# ─── Helper: HTTP fetch with timeout/quiet failure ───────────────────────
def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)
        if r.ok:
            return r.text
    except requests.RequestException:
        pass
    return None

# ─── Tiny text parsers / cleaners ────────────────────────────────────────
def grab(txt: str, label_pat: str) -> str | None:
    # Search “Label: value” patterns (case-insensitive, dash variants)
    m = re.search(rf"(?:{label_pat})\s*[:–-]\s*(.+?)(?:\n|$)", txt, flags=re.I)
    return m.group(1).strip() if m else None

def rng(s: str | None) -> str | None:   # normalize “1–3 ft” → “1 - 3”
    if not s: return None
    s = s.replace("–", "-")
    nums = re.findall(r"[\d.]+", s)
    nums = [str(int(float(n))) if float(n).is_integer() else n for n in nums]
    return " - ".join(nums) if nums else None

def month_rng(s: str | None) -> str | None:   # Jan–Mar → “Jan, Feb, Mar”
    if not s: return None
    s = re.sub(r"\b(?:to|through)\b", "-", s, flags=re.I)
    parts = [w.title().strip() for w in re.split(r"[,\-/]", s) if w.strip()]
    return ", ".join(parts)

def split_conditions(s: str | None) -> list[str]:
    if not s: return []
    s = s.replace(" to ", ",").replace("–", ",").replace("/", ",")
    return [part.strip() for part in s.split(",") if part.strip()]

def sun_conditions(s: str | None) -> str | None:
    return ", ".join([p.title() for p in split_conditions(s)]) if s else None

def water_conditions(s: str | None) -> str | None:
    return ", ".join([p.lower() for p in split_conditions(s)]) if s else None

# Build “Characteristics” composites
def mbg_chars(tolerate: str | None, maintenance: str | None) -> str | None:
    parts = []
    if tolerate:     parts.append(f"Tolerate: {tolerate}")
    if maintenance:  parts.append(f"Maintenance: {maintenance}")
    return " | ".join(parts) if parts else None

def wf_chars(leaf_retention: str | None, fruit_type: str | None) -> str | None:
    parts = []
    if fruit_type:     parts.append(f"Fruit Type: {fruit_type}")
    if leaf_retention: parts.append(f"Leaf Retention: {leaf_retention}")
    return " | ".join(parts) if parts else None

# merge_field: combines MBG+WF values without duplicates
def merge_field(primary: str | None, secondary: str | None) -> str | None:
    parts = []
    for source in (primary, secondary):
        if source:
            for p in re.split(r"[|,]", source):
                p = p.strip()
                if p and p not in parts:
                    parts.append(p)
    return ", ".join(parts) if parts else None

# generate unique Key if missing (same algorithm as PDFScrape)
def gen_key(botanical: str, used: set[str]) -> str:
    base = "".join(w[0] for w in botanical.split()[:2]).upper()
    suffix = ""; i = 1
    while base + suffix in used:
        suffix = str(i); i += 1
    used.add(base + suffix)
    return base + suffix

# ─── Parsers: MBG & WF HTML → dict of fields ─────────────────────────────
def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return {
        "Height (ft)"      : rng(grab(text, r"Height")),
        "Spread (ft)"      : rng(grab(text, r"Spread")),
        "Sun"              : sun_conditions(grab(text, r"Sun")),
        "Water"            : water_conditions(grab(text, r"Water")),
        "Characteristics"  : mbg_chars(grab(text, r"Tolerate"), grab(text, r"Maintenance")),
        "Wildlife Benefits": grab(text, r"Attracts"),
        "Distribution"     : (f"USDA Hardiness Zone {grab(text, r'Zone')}"
                              if grab(text, r'Zone') else None),
    }

def parse_wf(html: str, mbg_missing: bool = False) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    data = {
        "Bloom Color" : ", ".join(split_conditions(grab(text, r"Bloom Color"))),
        "Bloom Time"  : month_rng(grab(text, r"Bloom Time")),
        "Habitats"    : grab(text, r"Native Habitat"),
    }
    if mbg_missing:   # if MBG parse failed, fill primary fields from WF
        data.update({
            "Sun"              : sun_conditions(grab(text, r"Light Requirement")),
            "Water"            : water_conditions(grab(text, r"Soil Moisture")),
            "Wildlife Benefits": grab(text, r"Benefit"),
            "Characteristics"  : wf_chars(grab(text, r"Leaf Retention"),
                                          grab(text, r"Fruit Type")),
        })
    return data

# ─── Main Routine ────────────────────────────────────────────────────────
def main() -> None:
    df = pd.read_csv(IN_CSV, dtype=str).fillna("")
    if "Key" not in df.columns:
        df["Key"] = ""                              # ensure key column exists
    if "Botanical Name" not in df.columns:
        raise ValueError("❌ Missing 'Botanical Name' column in input CSV.")

    used_keys = set(df["Key"].dropna())             # track assigned keys

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Website Fill"):
        if not row.get("Botanical Name", "").strip():
            continue                                # skip blanks
        if not row.get("Key"):
            df.at[idx, "Key"] = gen_key(row["Botanical Name"], used_keys)

        # ─── Parse MBG first ────────────────────────────────────────────
        mbg_url = row.get("Link: Missouri Botanical Garden", "").strip()
        mbg_data = {}
        if mbg_url.startswith("http") and (html := fetch(mbg_url)):
            mbg_data = parse_mbg(html)
            for col, val in mbg_data.items():
                if val: df.at[idx, col] = val
            time.sleep(SLEEP_BETWEEN)              # throttle

        # ─── Then WF (fills missing or merges) ─────────────────────────
        wf_url = row.get("Link: Wildflower.org", "").strip()
        mbg_missing = not bool(mbg_data)
        if wf_url.startswith("http") and (html := fetch(wf_url)):
            wf_data = parse_wf(html, mbg_missing)
            for col, val in wf_data.items():
                if val:
                    # merge certain fields to keep additive info
                    if col in {"Sun","Water","Wildlife Benefits","Characteristics"}:
                        df.at[idx, col] = merge_field(df.at[idx, col], val)
                    else:
                        df.at[idx, col] = val
            time.sleep(SLEEP_BETWEEN)

    # Reorder columns to template + extras (safety)
    template = list(pd.read_csv(MASTER_CSV, nrows=0).columns)
    df = df[template + [c for c in df.columns if c not in template]]
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅ Saved → {OUT_CSV}")

if __name__ == "__main__":
    main()  # CLI entry-point
