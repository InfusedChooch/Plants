#!/usr/bin/env python3
# scrape_html_links.py — Download and save raw HTML from pasted URLs

import requests
from pathlib import Path
from urllib.parse import urlparse
import os

# Output folder
OUT_DIR = Path("html_dumps")
OUT_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}


def fetch_html(url: str) -> str | None:
    try:
        r = requests.get(url.strip(), headers=HEADERS, timeout=12)
        if r.ok:
            return r.text
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
    return None


def save_html(content: str, url: str):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(".", "_")
    slug = parsed.path.strip("/").replace("/", "_") or "index"
    filename = f"{domain}__{slug}.html"
    filepath = OUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Saved: {filepath}")


# ─── Main loop ───────────────────────────────────────────────────────────
print("Paste your URLs one per line. Leave blank and press Enter when done:\n")
urls = []
while True:
    line = input()
    if not line.strip():
        break
    urls.append(line.strip())

for url in urls:
    if url.startswith("http"):
        html = fetch_html(url)
        if html:
            save_html(html, url)
    else:
        print(f"⚠️ Skipped invalid URL: {url}")
