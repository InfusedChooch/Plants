#!/usr/bin/env python3
"""
Batch processor to run Scraper.py over all plant data files.
"""

import subprocess, sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("Scraper.py")
FILES = [
    "herbaceous_perennials.xlsx",
    "herbaceous_perennials_COMPLETE.csv",
    "ferns.csv",
    "grasses_sedges_and_rushes.csv",
    "shrubs.csv",
    "trees.csv",
]

for fname in FILES:
    fpath = Path(fname).resolve()
    if not fpath.exists():
        print(f"⚠️  Skipping missing file: {fname}")
        continue

    print(f"🔄 Processing {fname} ...")
    subprocess.run([sys.executable, str(SCRIPT), str(fpath)], check=True)

print("\n✅ All available files processed.")
