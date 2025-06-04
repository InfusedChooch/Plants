#!/usr/bin/env python3
"""Compare which fields each plant site provides for a given URL.

This script fetches the provided URLs for Missouri Botanical Garden
(MBG), Wildflower.org, Pleasant Run Nursery, New Moon Nursery and
Pinelands Nursery.  It previously relied on :mod:`FillMissingData` for
all parsing helpers.  To allow quick standalone execution it now
contains lightweight versions of the needed functions directly.

Example::

    python Tools/compare_site_data.py --mbg <MBG_URL> --wf <WF_URL> \
        --pr <PLEASANT_RUN_URL> --nm <NEW_MOON_URL> --pn <PINELANDS_URL>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Callable, Dict, Optional

import requests
from bs4 import BeautifulSoup


# ─── Basic Fetch ───────────────────────────────────────────────────────────
def fetch(url: str) -> str | None:
    """Return the page HTML or ``None`` on errors.

    A fallback via `r.jina.ai` is attempted for sites that block
    direct requests (HTTP 403).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    alt = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, timeout=12, headers=headers)
        if r.status_code == 403:
            r = requests.get(url, timeout=12, headers=alt)
        if r.status_code == 403:
            # final fallback via text-only proxy
            r = requests.get("https://r.jina.ai/" + url, timeout=12, headers=headers)
        if r.ok:
            return r.text
    except requests.RequestException:
        pass
    return None


# ─── Text Helpers ─────────────────────────────────────────────────────────-
def grab(txt: str, label_pat: str) -> str | None:
    m = re.search(rf"(?:{label_pat})\s*[:–-]\s*(.+?)(?:\n|$)", txt, flags=re.I)
    return m.group(1).strip() if m else None


def rng(s: str | None) -> str | None:
    if not s:
        return None
    s = s.replace("–", "-")
    nums = re.findall(r"[\d.]+", s)
    nums = [str(int(float(n))) if float(n).is_integer() else n for n in nums]
    return " - ".join(nums) if nums else None


def month_rng(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"\b(?:to|through)\b", "-", s, flags=re.I)
    parts = [w.title().strip() for w in re.split(r"[,/\-]", s) if w.strip()]
    return ", ".join(parts)


def split_conditions(s: str | None) -> list[str]:
    if not s:
        return []
    s = s.replace(" to ", ",").replace("–", ",").replace("/", ",")
    return [part.strip() for part in s.split(",") if part.strip()]


def sun_conditions(s: str | None) -> str | None:
    return ", ".join(p.title() for p in split_conditions(s)) if s else None


def water_conditions(s: str | None) -> str | None:
    return ", ".join(p.lower() for p in split_conditions(s)) if s else None


def wf_chars(leaf_retention: str | None, fruit_type: str | None) -> str | None:
    parts = []
    if fruit_type:
        parts.append(f"Fruit Type: {fruit_type}")
    if leaf_retention:
        parts.append(f"Leaf Retention: {leaf_retention}")
    return " | ".join(parts) if parts else None


def merge_field(primary: str | None, secondary: str | None) -> str | None:
    parts: list[str] = []
    for source in (primary, secondary):
        if source:
            for p in re.split(r"[|,]", source):
                val = p.strip()
                if val and val not in parts:
                    parts.append(val)
    return ", ".join(parts) if parts else None


def wf_wetland_status(soup: BeautifulSoup, region: str = "AGCP") -> Optional[str]:
    """Return the wetland indicator status for *region* from WF table."""
    h4 = soup.find(
        "h4", string=lambda x: x and "National Wetland Indicator Status" in x
    )
    if not h4:
        return None
    table = h4.find_next("table")
    if not table:
        return None
    rows = table.find_all("tr")
    if len(rows) < 2:
        return None
    regions = [td.get_text(strip=True) for td in rows[0].find_all("td")]
    statuses = [td.get_text(strip=True) for td in rows[1].find_all("td")]
    if regions and regions[0].lower().startswith("region"):
        regions = regions[1:]
    if statuses and statuses[0].lower().startswith("status"):
        statuses = statuses[1:]
    mapping = {r: s for r, s in zip(regions, statuses) if r}
    return mapping.get(region)


# ─── Site Parsers ─────────────────────────────────────────────────────────-
def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    return {
        "Height (ft)": rng(grab(text, r"Height")),
        "Spread (ft)": rng(grab(text, r"Spread")),
        "Sun": sun_conditions(grab(text, r"Sun")),
        "Water": water_conditions(grab(text, r"Water")),
        "Tolerates": grab(text, r"Tolerate"),
        "Maintenance": grab(text, r"Maintenance"),
        "Attracts": grab(text, r"Attracts"),
        "Zone": (
            f"USDA Hardiness Zone {grab(text, r'Zone')}"
            if grab(text, r"Zone")
            else None
        ),
    }


def parse_wf(html: str, mbg_missing: bool = False) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    status = wf_wetland_status(soup)
    text = soup.get_text("\n", strip=True)
    data = {
        "Bloom Color": ", ".join(split_conditions(grab(text, r"Bloom Color"))),
        "Bloom Time": month_rng(grab(text, r"Bloom Time")),
        "Habitats": grab(text, r"Native Habitat"),
        "Soil Description": grab(text, r"Soil Description"),
        "AGCP Regional Status": status,
    }
    if mbg_missing:
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


def parse_nm(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)
    flat = text.replace("\n", " ")

    def find_label(label: str) -> Optional[str]:
        m = re.search(rf"{label}\s*:?\s*([^\n]+)", text, flags=re.I)
        if m:
            return m.group(1).strip()
        return None

    data = {
        "Sun": sun_conditions(find_label("Exposure")),
        "Water": water_conditions(find_label("Soil Moisture Preference")),
        "Bloom Color": find_label("Bloom Colors"),
        "Height (ft)": (
            rng(re.search(r"Height\s*:\s*([\d\s-]+)\s*ft", flat, flags=re.I).group(1))
            if re.search(r"Height\s*:\s*([\d\s-]+)\s*ft", flat, flags=re.I)
            else None
        ),
    }

    salts = find_label("Salt Tolerance")
    walnut = find_label("Juglans nigra")
    parts = []
    if salts:
        parts.append(f"Salt Tolerance: {salts}")
    if walnut and walnut.lower().startswith("yes"):
        parts.append("Black Walnut Tolerant")
    if parts:
        data["Tolerates"] = ", ".join(parts)

    return {k: v for k, v in data.items() if v}


def parse_pn(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    info = {}
    for item in soup.select("div.item"):
        label = item.find("span")
        val = item.find("p")
        if label and val:
            info[label.get_text(strip=True)] = val.get_text(strip=True)

    data = {
        "Bloom Color": info.get("Bloom Color"),
        "Bloom Time": month_rng(info.get("Bloom Period")),
        "Height (ft)": rng(info.get("Max Mature Height") or info.get("Height")),
        "Spread (ft)": rng(info.get("Spread")),
    }

    if info.get("Pollinator Attributes"):
        data["Attracts"] = info["Pollinator Attributes"]
    if info.get("Deer Resistant", "").lower() == "yes":
        data["Tolerates"] = merge_field(data.get("Tolerates"), "Deer")

    return {k: v for k, v in data.items() if v}


# ─── Helpers ───────────────────────────────────────────────────────────────
def parse_site(
    url: str, parser: Callable[[str], Dict[str, Optional[str]]], name: str
) -> Dict[str, str]:
    """Fetch ``url`` and return a dict of ``field -> value`` for found values."""
    if not url or not url.startswith("http"):
        return {}
    html = fetch(url)
    if not html:
        print(f"Failed to fetch {name} URL", file=sys.stderr)
        return {}
    try:
        data = parser(html)
    except Exception as exc:  # pragma: no cover - just defensive
        print(f"Error parsing {name}: {exc}", file=sys.stderr)
        return {}
    return {k: v for k, v in data.items() if v}


# ─── CLI ───────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Compare scraped fields across sites")
parser.add_argument("--mbg", default="", help="MBG plant URL")
parser.add_argument("--wf", default="", help="Wildflower.org URL")
parser.add_argument("--pr", default="", help="Pleasant Run Nursery URL")
parser.add_argument("--nm", default="", help="New Moon Nursery URL")
parser.add_argument("--pn", default="", help="Pinelands Nursery URL")
parser.add_argument(
    "--json", action="store_true", help="Output JSON instead of a table"
)
parser.add_argument(
    "--output",
    default="",
    help="Save extracted field values to the given text file",
)
args = parser.parse_args()

# ─── Gather data ───────────────────────────────────────────────────────────
results = {
    "MBG": parse_site(args.mbg, parse_mbg, "MBG"),
    "WF": parse_site(args.wf, parse_wf, "Wildflower"),
    "PR": parse_site(args.pr, parse_pr, "Pleasant Run"),
    "NM": parse_site(args.nm, parse_nm, "New Moon"),
    "PN": parse_site(args.pn, parse_pn, "Pinelands"),
}

# ─── Output ────────────────────────────────────────────────────────────────
if args.json:
    print(json.dumps(results, indent=2))
    raise SystemExit

if args.output:
    with open(args.output, "w", encoding="utf-8") as fh:
        for site, data in results.items():
            fh.write(f"[{site}]\n")
            for field, value in data.items():
                fh.write(f"{field}: {value}\n")
            fh.write("\n")

all_fields = sorted({f for d in results.values() for f in d})
header = ["Field"] + list(results.keys())
rows = []
for field in all_fields:
    row = [field]
    for site in results:
        row.append("✔" if field in results[site] else "")
    rows.append(row)

# compute column widths
widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]

# print header
line = " | ".join(str(h).ljust(w) for h, w in zip(header, widths))
print(line)
print("-+-".join("-" * w for w in widths))
for row in rows:
    print(" | ".join(str(c).ljust(w) for c, w in zip(row, widths)))
