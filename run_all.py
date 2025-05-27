#!/usr/bin/env python3
"""
Runs both PDF scrape and website fill sequentially.
"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

PDF_SCRIPT = BASE / "PDFScrape.py"
WEB_SCRIPT = BASE / "FillwithLinks.py"

print("🔍 Running PDF scraper...")
pdf_result = subprocess.run([sys.executable, str(PDF_SCRIPT)], capture_output=True, text=True)
print(pdf_result.stdout)
if pdf_result.returncode != 0:
    print("❌ PDF scrape failed:", pdf_result.stderr)
    sys.exit(1)

print("\n🌐 Running website filler...")
web_result = subprocess.run([sys.executable, str(WEB_SCRIPT)], capture_output=True, text=True)
print(web_result.stdout)
if web_result.returncode != 0:
    print("❌ Website fill failed:", web_result.stderr)
    sys.exit(1)

print("\n All steps complete. Final file: Plants_FINAL.csv")
