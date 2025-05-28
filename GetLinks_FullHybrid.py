#!/usr/bin/env python3
# GetLinks_FullHybrid.py ─ Hybrid Bing-Selenium + HTML parse to resolve MBG & WF URLs

import time                          # delays / pacing
import pandas as pd                  # CSV I/O
import requests                      # plain HTTP fallback
from bs4 import BeautifulSoup        # HTML parsing
from urllib.parse import quote_plus  # safe query strings
from selenium import webdriver       # headless browser
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from typing import Optional          # type hints

# ─── File / Column constants ─────────────────────────────────────────────
INPUT_CSV  = "Plants_Nolinks.csv"            # produced by PDFScrape
OUTPUT_CSV = "Plants and Links TEST.csv"     # enriched version
MBG_COL    = "Link: Missouri Botanical Garden"
WF_COL     = "Link: Wildflower.org"
HEADERS    = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}  # polite header

# ─── Selenium: launch Chrome in headless mode ────────────────────────────
opt = Options()
opt.add_argument("--headless=new")   # new headless implementation (Chrome ≥ 109)
opt.add_argument("--disable-gpu")    # stability on Windows
opt.add_argument("--log-level=3")    # suppress warnings
driver = webdriver.Chrome(options=opt)

# ─── Lightweight retry wrapper around requests.get ───────────────────────
def safe_get(url: str, retries=2, delay=2) -> Optional[requests.Response]:
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.ok:
                return r
        except Exception:
            time.sleep(delay)        # wait then retry
    return None                      # all attempts failed

# ─── Missouri Botanical Garden: parse search results directly (no JS) ────
def query_mbg(name: str) -> Optional[str]:
    url = ("https://www.missouribotanicalgarden.org/PlantFinder/"
           f"PlantFinderSearchResults.aspx?basic={quote_plus(name)}")
    if (r := safe_get(url)):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='PlantFinderDetails.aspx']")
        if a and a.get("href"):
            return "https://www.missouribotanicalgarden.org" + a["href"]
    return None

# ─── Bing via Selenium for MBG result ─────────────────────────────────────
def selenium_mbg_link(name: str) -> Optional[str]:
    query = f'"{name}" site:missouribotanicalgarden.org'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "PlantFinderDetails.aspx" in href:
            return href
    return None

# ─── Bing via Selenium for Wildflower.org result ─────────────────────────
def selenium_wf_link(name: str) -> Optional[str]:
    query = f'"{name}" site:wildflower.org "plants/result.php"'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "wildflower.org/plants/result.php" in href:
            return href
    return None

# Generate variants: botanical, common, and “Genus species” (no subspp.)
def name_variants(row):
    names = [row["Botanical Name"]]
    if row.get("Common Name"):
        names.append(row["Common Name"])
    names.append(" ".join(row["Botanical Name"].split()[:2]))
    return list(dict.fromkeys(names))   # dedupe + keep order

def title_contains(botanical_name: str) -> bool:
    """Check if all botanical tokens appear in current tab title."""
    page_title = driver.title.lower()
    return all(part.lower() in page_title for part in botanical_name.lower().split())

# ─── Read CSV & Ensure columns exist ─────────────────────────────────────
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
for col in (MBG_COL, WF_COL):
    if col not in df.columns:
        df[col] = ""                   # add empty link columns if missing

# ─── Iterate rows and resolve missing links ──────────────────────────────
for idx, row in df.iterrows():
    bname = row["Botanical Name"]
    cname = row.get("Common Name", "")
    have_mbg = "PlantFinderDetails.aspx" in row[MBG_COL]
    have_wf  = "wildflower.org/plants/result.php" in row[WF_COL]

    print(f"\n🔍 {bname} ({cname})")    # progress feedback

    # — MBG lookup (Selenium first, fallback plain HTML) —
    if not have_mbg:
        for q in name_variants(row):
            if link := selenium_mbg_link(q):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, MBG_COL] = link
                    print(f"✅ MBG → {link}")
                    break
        else:                           # Selenium failed, try HTML search
            for q in name_variants(row):
                if link := query_mbg(q):
                    driver.get(link); time.sleep(1)
                    if title_contains(bname):
                        df.at[idx, MBG_COL] = link
                        print(f"✅ MBG (fallback) → {link}")
                        break
            else:
                print("⚠️ MBG not found or invalid")

    # — WF lookup (only Selenium) —
    if not have_wf:
        for q in name_variants(row):
            if link := selenium_wf_link(q):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, WF_COL] = link
                    print(f"✅ WF  → {link}")
                    break
        else:
            print("⚠️ WF not found or invalid")

    time.sleep(1.0)                     # polite pacing

# ─── Save & Quit ─────────────────────────────────────────────────────────
driver.quit()
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 Done → {OUTPUT_CSV}")
