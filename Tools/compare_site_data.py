#!/usr/bin/env python3
"""Compare which fields each plant site provides for a given URL.

This tool fetches the provided URLs for Missouri Botanical Garden (MBG),
Wildflower.org, Pleasant Run Nursery, New Moon Nursery and Pinelands
Nursery. It reuses the parsing helpers from ``FillMissingData.py`` to
extract data and then reports which fields were present on each site.

Example:
    python Tools/compare_site_data.py --mbg <MBG_URL> --wf <WF_URL> \
        --pr <PLEASANT_RUN_URL> --nm <NEW_MOON_URL> --pn <PINELANDS_URL>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

# ─── Load parsing functions from FillMissingData.py ─────────────────────────
BASE = Path(__file__).resolve().parents[1]
fill_path = BASE / "Static" / "Python" / "FillMissingData.py"
spec = importlib.util.spec_from_file_location("fill", fill_path)
fill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fill)  # type: ignore

fetch = fill.fetch
parse_mbg = fill.parse_mbg
parse_wf = fill.parse_wf
parse_pr = fill.parse_pr
parse_nm = getattr(fill, "parse_nm", None)
parse_pn = getattr(fill, "parse_pn", None)

# fallback stubs if new parsers are not yet present
if parse_nm is None:

    def parse_nm(html: str) -> Dict[str, Optional[str]]:
        return {}


if parse_pn is None:

    def parse_pn(html: str) -> Dict[str, Optional[str]]:
        return {}


# ─── Helpers ───────────────────────────────────────────────────────────────
def parse_site(
    url: str, parser: Callable[[str], Dict[str, Optional[str]]], name: str
) -> Dict[str, bool]:
    """Fetch ``url`` and return a dict of ``field -> True`` for found values."""
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
    return {k: bool(v) for k, v in data.items()}


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

all_fields = sorted({f for d in results.values() for f in d})
header = ["Field"] + list(results.keys())
rows = []
for field in all_fields:
    row = [field] + ["✔" if results[site].get(field) else "" for site in results]
    rows.append(row)

# compute column widths
widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]

# print header
line = " | ".join(str(h).ljust(w) for h, w in zip(header, widths))
print(line)
print("-+-".join("-" * w for w in widths))
for row in rows:
    print(" | ".join(str(c).ljust(w) for c, w in zip(row, widths)))
