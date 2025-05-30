#!/usr/bin/env python3
# GetLinks.py ── Find and fill in missing plant website links using web searches

import time                          # for pausing between requests
import pandas as pd                  # for reading and writing CSV files
import requests                      # for simple HTTP requests
from bs4 import BeautifulSoup        # for parsing HTML pages
from urllib.parse import quote_plus  # for safely encoding search terms in URLs
from selenium import webdriver       # for controlling a web browser programmatically
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from typing import Optional          # for simple type hints in function signatures
import argparse

parser = argparse.ArgumentParser(description="Find missing MBG/WF plant links")
parser.add_argument("--in_csv", default="Plants_NeedLinks.csv", help="Input CSV file")
parser.add_argument("--out_csv", default="Plants_Linked.csv", help="Output CSV file")
args = parser.parse_args()

# ─── File and Column Settings ─────────────────────────────────────────────

INPUT_CSV  = BASE / args.in_csv
OUTPUT_CSV = BASE / args.out_csv
MBG_COL    = "Link: Missouri Botanical Garden"
WF_COL     = "Link: Wildflower.org"
HEADERS    = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}  # pretend to be a normal browser

# ─── Start a headless Chrome browser via Selenium ──────────────────────────
opt = Options()
opt.add_argument("--headless=new")   # run without opening a visible window
opt.add_argument("--disable-gpu")    # avoid GPU-related errors
opt.add_argument("--log-level=3")    # hide extra browser logs
driver = webdriver.Chrome(options=opt)

# ─── Helper: Try an HTTP GET with retries ─────────────────────────────────
def safe_get(url: str, retries=2, delay=2) -> Optional[requests.Response]:
    """
    Try to fetch `url` up to (retries + 1) times using requests.
    Wait `delay` seconds between attempts.
    Return the Response object if successful, or None if all fail.
    """
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.ok:
                return r
        except Exception:
            time.sleep(delay)
    return None  # give up after all retries

# ─── Direct MBG Search via HTML ───────────────────────────────────────────
def query_mbg(name: str) -> Optional[str]:
    """
    Use Missouri Botanical Garden’s own search page (no JavaScript needed).
    Return the link to the details page if found, else None.
    """
    base = "https://www.missouribotanicalgarden.org/PlantFinder/PlantFinderSearchResults.aspx"
    url = f"{base}?basic={quote_plus(name)}"
    if (r := safe_get(url)):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='PlantFinderDetails.aspx']")
        if a and a.get("href"):
            return "https://www.missouribotanicalgarden.org" + a["href"]
    return None

# ─── MBG Lookup via Bing + Selenium ────────────────────────────────────────
def selenium_mbg_link(name: str) -> Optional[str]:
    """
    Open Bing search for '"name" site:missouribotanicalgarden.org',
    then look for the first result pointing to a MBG details page.
    """
    query = f'"{name}" site:missouribotanicalgarden.org'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)  # let the page load
    # Find all result links and pick the first that matches
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "PlantFinderDetails.aspx" in href:
            return href
    return None

# ─── Wildflower.org Lookup via Bing + Selenium ────────────────────────────
def selenium_wf_link(name: str) -> Optional[str]:
    """
    Similar to selenium_mbg_link, but search site:wildflower.org
    looking for the wildflower.org 'plants/result.php' pages.
    """
    query = f'"{name}" site:wildflower.org "plants/result.php"'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "wildflower.org/plants/result.php" in href:
            return href
    return None

# ─── Prepare Different Name Variations ────────────────────────────────────
def name_variants(row):
    """
    Build a list of names to try in searches:
      1) the full botanical name
      2) the common name (if present)
      3) just the genus + species (no subspecies)
    This helps catch cases where the site might list a slightly different variant.
    """
    names = [row["Botanical Name"]]
    if row.get("Common Name"):
        names.append(row["Common Name"])
    # take only the first two words of botanical name
    names.append(" ".join(row["Botanical Name"].split()[:2]))
    return list(dict.fromkeys(names))  # remove duplicates, keep order

# ─── Check That the Page Title Matches the Plant ──────────────────────────
def title_contains(botanical_name: str) -> bool:
    """
    After navigating to a candidate page, ensure the browser’s title
    contains all parts of the botanical name (case-insensitive).
    This avoids false positives.
    """
    title = driver.title.lower()
    return all(part.lower() in title for part in botanical_name.split())

# ─── Load CSV and Add Missing Columns ─────────────────────────────────────
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")  # read in original CSV
for col in (MBG_COL, WF_COL):
    if col not in df.columns:
        df[col] = ""  # make sure link columns exist

# ─── Main Loop: Fill in Missing Links ────────────────────────────────────
for idx, row in df.iterrows():
    bname = row["Botanical Name"]
    cname = row.get("Common Name", "")
    have_mbg = "PlantFinderDetails.aspx" in row[MBG_COL]
    have_wf  = "wildflower.org/plants/result.php" in row[WF_COL]

    print(f"\n🔍 {bname} ({cname})")  # show progress

    # — MBG lookup: try Selenium first, then HTML fallback ——
    if not have_mbg:
        # 1) Selenium-based search
        for variant in name_variants(row):
            if link := selenium_mbg_link(variant):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, MBG_COL] = link
                    print(f"✅ MBG → {link}")
                    break
        else:
            # 2) Plain HTML-based query if Selenium did not find it
            for variant in name_variants(row):
                if link := query_mbg(variant):
                    driver.get(link); time.sleep(1)
                    if title_contains(bname):
                        df.at[idx, MBG_COL] = link
                        print(f"✅ MBG (fallback) → {link}")
                        break
            else:
                print("⚠️ MBG not found or invalid")

    # — Wildflower.org lookup: only Selenium ——
    if not have_wf:
        for variant in name_variants(row):
            if link := selenium_wf_link(variant):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, WF_COL] = link
                    print(f"✅ WF  → {link}")
                    break
        else:
            print("⚠️ WF not found or invalid")

    time.sleep(1.0)  # pause between rows for politeness

# ─── Wrap Up: save and close browser ──────────────────────────────────────
driver.quit()
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 Done → {OUTPUT_CSV}")
