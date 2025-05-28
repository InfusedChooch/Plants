#!/usr/bin/env python3
# /plants/GetLinks_FullHybrid.py

import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from typing import Optional

INPUT_CSV  = "Plants_Nolinks.csv"
OUTPUT_CSV = "Plants and Links TEST.csv"
MBG_COL    = "Link: Missouri Botanical Garden"
WF_COL     = "Link: Wildflower.org"
HEADERS    = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

# ─── Headless Selenium Setup ──────────────────────────────────────────────
opt = Options()
opt.add_argument("--headless=new")
opt.add_argument("--disable-gpu")
opt.add_argument("--log-level=3")
driver = webdriver.Chrome(options=opt)

def safe_get(url: str, retries=2, delay=2) -> Optional[requests.Response]:
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.ok:
                return r
        except Exception:
            time.sleep(delay)
    return None

def query_mbg(name: str) -> Optional[str]:
    url = ("https://www.missouribotanicalgarden.org/PlantFinder/"
           f"PlantFinderSearchResults.aspx?basic={quote_plus(name)}")
    if (r := safe_get(url)):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='PlantFinderDetails.aspx']")
        if a and a.get("href"):
            return "https://www.missouribotanicalgarden.org" + a["href"]
    return None

def selenium_mbg_link(name: str) -> Optional[str]:
    query = f'"{name}" site:missouribotanicalgarden.org'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "PlantFinderDetails.aspx" in href:
            return href
    return None

def selenium_wf_link(name: str) -> Optional[str]:
    query = f'"{name}" site:wildflower.org "plants/result.php"'
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if "wildflower.org/plants/result.php" in href:
            return href
    return None

def name_variants(row):
    names = [row["Botanical Name"]]
    if row.get("Common Name"):
        names.append(row["Common Name"])
    names.append(" ".join(row["Botanical Name"].split()[:2]))
    return list(dict.fromkeys(names))

def title_contains(botanical_name: str) -> bool:
    """Verify the title contains all parts of the botanical name."""
    page_title = driver.title.lower()
    return all(part.lower() in page_title for part in botanical_name.lower().split())

# ─── Main Lookup Logic ────────────────────────────────────────────────────
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
for col in (MBG_COL, WF_COL):
    if col not in df.columns:
        df[col] = ""

for idx, row in df.iterrows():
    bname = row["Botanical Name"]
    cname = row.get("Common Name", "")
    have_mbg = "PlantFinderDetails.aspx" in row[MBG_COL]
    have_wf  = "wildflower.org/plants/result.php" in row[WF_COL]

    print(f"\n🔍 {bname} ({cname})")

    # MBG Lookup
    if not have_mbg:
        for q in name_variants(row):
            if link := selenium_mbg_link(q):
                driver.get(link)
                time.sleep(1)
                if title_contains(bname):
                    df.at[idx, MBG_COL] = link
                    print(f"✅ MBG → {link}")
                    break
        else:
            for q in name_variants(row):
                if link := query_mbg(q):
                    driver.get(link)
                    time.sleep(1)
                    if title_contains(bname):
                        df.at[idx, MBG_COL] = link
                        print(f"✅ MBG (fallback) → {link}")
                        break
            else:
                print("⚠️ MBG not found or invalid")

    # WF Lookup
    if not have_wf:
        for q in name_variants(row):
            if link := selenium_wf_link(q):
                driver.get(link)
                time.sleep(1)
                if title_contains(bname):
                    df.at[idx, WF_COL] = link
                    print(f"✅ WF  → {link}")
                    break
        else:
            print("⚠️ WF not found or invalid")

    time.sleep(1.0)

# ─── Save Results ─────────────────────────────────────────────────────────
driver.quit()
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 Done → {OUTPUT_CSV}")
