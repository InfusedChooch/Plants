# FillMissingData.py
# Description: Pull numeric, habitat, and other details from Missouri Botanical Garden and Wildflower.org pages and fill them into a CSV.

from __future__ import (
    annotations,
)  # allow postponed evaluation of type hints for forward references
import csv  # built-in support for CSV operations (writing with quotes)
import re  # regular expressions for searching and cleaning text
import time  # to pause between HTTP requests for politeness
from pathlib import Path  # easy file system path manipulations
from typing import (
    Dict,
    Optional,
)  # type hinting for dictionaries and optional return values

import pandas as pd  # data handling library for reading and writing CSVs as DataFrames
import requests  # HTTP library to fetch webpage content
from bs4 import BeautifulSoup  # HTML parser to extract text from web pages
from tqdm import tqdm  # progress bar utility when looping over many items
import argparse

parser = argparse.ArgumentParser(description="Fill missing plant fields using MBG/WF")
parser.add_argument(
    "--in_csv", default="Static/Outputs/Plants_Linked.csv", help="Input CSV file"
)
parser.add_argument(
    "--out_csv",
    default="Static/Outputs/Plants_Linked_Filled.csv",
    help="Output CSV file",
)
args = parser.parse_args()

# ─── File Paths & Configuration ───────────────────────────────────────────
BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent


def repo_path(arg: str) -> Path:
    """Resolve CLI paths relative to the repo root or this script."""
    p = Path(arg).expanduser()
    if p.is_absolute():
        return p
    if p.parts and p.parts[0].lower() == "static":
        return (REPO / p).resolve()
    cand = (BASE / p).resolve()
    return cand if cand.exists() else (REPO / p).resolve()


IN_CSV = repo_path(args.in_csv)
OUT_CSV = repo_path(args.out_csv)
MASTER_CSV = repo_path("Static/Templates/Plants_Linked_Filled_Master.csv")
SLEEP_BETWEEN = 0.7  # seconds to wait between each HTTP request
# identify as a browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# fallback headers if a site blocks the main user agent
HEADERS_ALT = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# columns pulled from each site so we know when to scrape
MBG_COLS = {
    "Height (ft)",
    "Spread (ft)",
    "Sun",
    "Water",
    "Tolerates",
    "Maintenance",
    "Attracts",
    "Zone",
}
WF_COLS = {
    "Bloom Color",
    "Bloom Time",
    "Habitats",
    "Soil Description",
    "Sun",
    "Water",
    "Attracts",
    "Characteristics",
    "AGCP Regional Status",
}
PR_COLS = {
    "Tolerates",
    "Attracts",
}


def missing(val: str | None) -> bool:
    """Return True if cell value is blank or only whitespace."""
    return not str(val or "").strip()


# ─── Helper Function: Fetch HTML Safely ────────────────────────────────────
def fetch(url: str) -> str | None:
    """
    Try to download HTML from `url`. Return the page text if successful;
    otherwise return None quietly on errors.
    """
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)  # attempt HTTP GET
        if r.status_code == 403:
            r = requests.get(url, timeout=12, headers=HEADERS_ALT)
        if r.ok:
            return r.text  # return the HTML body if status code is 200
    except requests.RequestException:
        pass  # ignore network errors, timeouts, etc.
    return None  # return None if anything goes wrong


# ─── Text Parsing Utilities ────────────────────────────────────────────────
def grab(txt: str, label_pat: str) -> str | None:
    """
    Look for patterns like "Label: value" or "Label–value" in `txt`.
    Return the captured `value` or None if not found.
    """
    # regex uses case‑insensitive match of the label pattern, then a colon/dash, then the text
    m = re.search(rf"(?:{label_pat})\s*[:–-]\s*(.+?)(?:\n|$)", txt, flags=re.I)
    return m.group(1).strip() if m else None


def rng(s: str | None) -> str | None:
    """
    Normalize ranges like "1–3 ft" or "1 to 3 ft" into "1 - 3".
    Returns None if input is empty or no numbers found.
    """
    if not s:
        return None
    s = s.replace("–", "-")  # unify dash characters
    nums = re.findall(r"[\d.]+", s)  # extract all numbers
    # convert floats that are whole ints into int strings
    nums = [str(int(float(n))) if float(n).is_integer() else n for n in nums]
    return " - ".join(nums) if nums else None


def month_rng(s: str | None) -> str | None:
    """
    Convert month ranges like "Jan–Mar" or "Feb through Apr"
    into comma-separated full months "Jan, Feb, Mar, Apr".
    """
    if not s:
        return None
    # replace words like "to" or "through" with a hyphen
    s = re.sub(r"\b(?:to|through)\b", "-", s, flags=re.I)
    parts = [w.title().strip() for w in re.split(r"[,/\-]", s) if w.strip()]
    return ", ".join(parts)


def split_conditions(s: str | None) -> list[str]:
    """
    Break strings like "full sun to part shade" or "dry/moist"
    into a clean list of individual conditions.
    """
    if not s:
        return []
    # replace common separators with commas, then split
    s = s.replace(" to ", ",").replace("–", ",").replace("/", ",")
    return [part.strip() for part in s.split(",") if part.strip()]


def sun_conditions(s: str | None) -> str | None:
    """
    Standardize sun exposure terms to Title Case, comma-separated.
    """
    return ", ".join(p.title() for p in split_conditions(s)) if s else None


def water_conditions(s: str | None) -> str | None:
    """
    Standardize water needs to lowercase, comma-separated.
    """
    return ", ".join(p.lower() for p in split_conditions(s)) if s else None


def mbg_chars(tolerate: str | None, maintenance: str | None) -> str | None:
    """
    Combine MBG’s "Tolerate" and "Maintenance" fields into one string,
    separated by " | ".
    """
    parts = []
    if tolerate:
        parts.append(f"Tolerate: {tolerate}")
    if maintenance:
        parts.append(f"Maintenance: {maintenance}")
    return " | ".join(parts) if parts else None


def wf_chars(leaf_retention: str | None, fruit_type: str | None) -> str | None:
    """
    Combine Wildflower.org’s "Leaf Retention" and "Fruit Type" into one string.
    """
    parts = []
    if fruit_type:
        parts.append(f"Fruit Type: {fruit_type}")
    if leaf_retention:
        parts.append(f"Leaf Retention: {leaf_retention}")
    return " | ".join(parts) if parts else None


def merge_field(primary: str | None, secondary: str | None) -> str | None:
    """
    Merge two comma- or pipe-separated strings without duplicates,
    preserving the order they appear.
    """
    parts: list[str] = []
    for source in (primary, secondary):
        if source:
            for p in re.split(r"[|,]", source):
                val = p.strip()
                if val and val not in parts:
                    parts.append(val)
    return ", ".join(parts) if parts else None


def gen_key(botanical: str, used: set[str]) -> str:
    """
    Create a simple unique key from the first letters of genus and species,
    appending numbers if needed to avoid duplicates.
    """
    parts = botanical.split()
    base = "".join(w[0] for w in parts[:2]).upper()
    suffix = ""
    i = 1
    while base + suffix in used:
        suffix = str(i)
        i += 1
    used.add(base + suffix)
    return base + suffix


# ─── HTML Parsers for Each Site ──────────────────────────────────────────
def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    """
    Extract MBG details: height, spread, sun, water, characteristics,
    wildlife benefits, and distribution (hardiness zone).
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return {

        "Height (ft)":      rng(grab(text, r"Height")),
        "Spread (ft)":      rng(grab(text, r"Spread")),
        "Sun":              sun_conditions(grab(text, r"Sun")),
        "Water":            water_conditions(grab(text, r"Water")),
        "Tolerates":        grab(text, r"Tolerate"),
        "Maintenance":      grab(text, r"Maintenance"),
        "Attracts":         grab(text, r"Attracts"),
        "Zone":             (f"USDA Hardiness Zone {grab(text, r'Zone')}" if grab(text, r"Zone") else None),
    }


def parse_wf(html: str, mbg_missing: bool = False) -> Dict[str, Optional[str]]:
    """
    Extract Wildflower.org details: bloom color/time and habitats.
    If MBG data is missing, also pull sun, water, benefits, and characteristics from WF.
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    data = {
        "Bloom Color": ", ".join(split_conditions(grab(text, r"Bloom Color"))),
        "Bloom Time": month_rng(grab(text, r"Bloom Time")),
        "Habitats": grab(text, r"Native Habitat"),
        "Soil Description": grab(text, r"Soil Description"),
        "AGCP Regional Status": grab(text, r"(?:National Wetland Indicator Status|AGCP)"),
    }
    if mbg_missing:
        # fill core fields when MBG had no data
        data.update(
            {
                "Sun": sun_conditions(grab(text, r"Light Requirement")),
                "Water": water_conditions(grab(text, r"Soil Moisture")),
                "Attracts": grab(text, r"Benefit"),
                "Characteristics": wf_chars(
                    grab(text, r"Leaf Retention"), grab(text, r"Fruit Type")
                ),
            }
        )
    return data


def parse_pr(html: str) -> Dict[str, Optional[str]]:
    """Extract wildlife attractions and tolerances from Pleasant Run."""
    soup = BeautifulSoup(html, "lxml")

    def collect(title: str) -> str | None:
        h = soup.find("h5", string=lambda x: x and title.lower() in x.lower())
        if not h:
            return None
        box = h.find_parent("div")
        if not box:
            return None
        vals = [a.get_text(strip=True) for a in box.find_all("a")]
        cleaned = [re.sub(r"^Attracts\s+", "", v) for v in vals]
        return ", ".join(cleaned) if cleaned else None

    return {
        "Attracts": collect("Attracts Wildlife"),
        "Tolerates": collect("Tolerance"),
    }


# ─── Main Processing Loop ─────────────────────────────────────────────────
def main() -> None:
    # load CSV into a DataFrame, ensuring all empty cells become blank strings
    df = pd.read_csv(IN_CSV, dtype=str).fillna("")
    df = df.rename(
        columns={
            "Link: Missouri Botanical Garden": "MBG Link",
            "Link: Wildflower.org": "WF Link",
            "Link: Pleasantrunnursery.com": "PR Link",
            "Distribution": "Zone",
        }
    )
    # ensure a Key column exists for identifying rows uniquely
    if "Key" not in df.columns:
        df["Key"] = ""
    if "Botanical Name" not in df.columns:
        raise ValueError("❌ Missing 'Botanical Name' column in input CSV.")

    used_keys = set(df["Key"].dropna())  # track already-used keys

    # iterate each plant row with a progress bar
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Website Fill"):
        # skip rows without a botanical name
        if not row.get("Botanical Name", "").strip():
            continue
        # generate a key if missing
        if not row.get("Key"):
            df.at[idx, "Key"] = gen_key(row["Botanical Name"], used_keys)

        # ── Fetch and parse MBG only for missing columns ───────────────
        mbg_url = row.get("MBG Link", "").strip()
        mbg_data: Dict[str, Optional[str]] = {}
        needs_mbg = any(missing(row.get(c)) for c in MBG_COLS)
        if needs_mbg and mbg_url.startswith("http"):
            html = fetch(mbg_url)
            if html:
                mbg_data = parse_mbg(html)
                for col, val in mbg_data.items():
                    if not val:
                        continue
                    if col in {"Attracts", "Tolerates"}:
                        if df.at[idx, col]:
                            df.at[idx, col] = merge_field(df.at[idx, col], val)
                        else:
                            df.at[idx, col] = val
                    elif missing(df.at[idx, col]):
                        df.at[idx, col] = val
                time.sleep(SLEEP_BETWEEN)

        # ── Fetch and parse WF, merging or filling missing ─────────────
        row = df.loc[idx]
        wf_url = row.get("WF Link", "").strip()
        needs_wf = any(missing(row.get(c)) for c in WF_COLS)
        if needs_wf and wf_url.startswith("http"):
            html = fetch(wf_url)
            if html:
                wf_data = parse_wf(html, mbg_missing=not bool(mbg_data))
                for col, val in wf_data.items():
                    if not val:
                        continue
                    if col in {"Sun", "Water", "Attracts", "Characteristics"}:
                        if df.at[idx, col]:
                            df.at[idx, col] = merge_field(df.at[idx, col], val)
                        else:
                            df.at[idx, col] = val
                    elif missing(df.at[idx, col]):
                        df.at[idx, col] = val
                time.sleep(SLEEP_BETWEEN)

        # ── Fetch and parse Pleasant Run for tolerances/attracts ───────
        row = df.loc[idx]
        pr_url = row.get("PR Link", "").strip()
        needs_pr = any(missing(row.get(c)) for c in PR_COLS)
        if pr_url.startswith("http") and needs_pr:
            html = fetch(pr_url)
            if html:
                pr_data = parse_pr(html)
                for col, val in pr_data.items():
                    if not val:
                        continue
                    # always merge for additive fields
                    if col in {"Attracts", "Tolerates"}:
                        if df.at[idx, col]:
                            df.at[idx, col] = merge_field(df.at[idx, col], val)
                        else:
                            df.at[idx, col] = val
                    elif missing(df.at[idx, col]):
                        df.at[idx, col] = val
                time.sleep(SLEEP_BETWEEN)

    # reorder columns to match original template, keeping extras at end
    template = list(pd.read_csv(MASTER_CSV, nrows=0).columns)
    df = df[template + [c for c in df.columns if c not in template]]
    # save out the newly filled CSV
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL, na_rep="")
    print(f"Saved → {OUT_CSV}")


if __name__ == "__main__":
    main()  # run when executed as a script
