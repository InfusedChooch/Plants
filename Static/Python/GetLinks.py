#!/usr/bin/env python3
# GetLinks.py ── Prefill, find, and validate MBG / Wildflower links for plants

import time
import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# ─── Selenium setup ──────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# --- CLI Arguments -------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Prefill, locate, and validate MBG / Wildflower links."
)
parser.add_argument("--in_csv",  default="Static/Outputs/Plants_NeedLinks.csv")
parser.add_argument("--out_csv", default="Static/Outputs/Plants_Linked.csv")
parser.add_argument("--master_csv",
                    default="Static/Templates/Plants_Linked_Filled_Master.csv")

# NEW: build a safe default for chromedriver
default_cd = (Path(__file__).resolve().parent / "chromedriver.exe").as_posix()
parser.add_argument("--chromedriver",
                    default=default_cd,
                    help="Full path to chromedriver.exe")

args = parser.parse_args()

# ─── Constants ───────────────────────────────────────────────────────────
BASE        = Path(__file__).resolve().parent
INPUT_CSV   = BASE / args.in_csv
OUTPUT_CSV  = BASE / args.out_csv
MASTER_CSV  = BASE / args.master_csv
if not MASTER_CSV.is_absolute():
    # treat the path as relative to the REPO ROOT, not Static/Python
    MASTER_CSV = (BASE.parent / MASTER_CSV).resolve()
CHROMEDRIVER= BASE / args.chromedriver
if not CHROMEDRIVER.is_absolute():          # if user gave a relative path
    CHROMEDRIVER = (BASE / CHROMEDRIVER).resolve()

MBG_COL = "Link: Missouri Botanical Garden"
WF_COL  = "Link: Wildflower.org"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

# ─── Start Selenium (headless Chrome) ────────────────────────────────────
opt = Options()
opt.add_argument("--headless=new")
opt.add_argument("--disable-gpu")
opt.add_argument("--log-level=3")
driver = webdriver.Chrome(service=Service(str(CHROMEDRIVER)), options=opt)

# ─── Helper: polite GET with retries ─────────────────────────────────────
def safe_get(url: str, retries: int = 2, delay: int = 2) -> Optional[requests.Response]:
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.ok:
                return r
        except Exception:
            pass
        time.sleep(delay)
    return None

# ─── MBG direct HTML query ───────────────────────────────────────────────
def query_mbg(name: str) -> Optional[str]:
    base = ("https://www.missouribotanicalgarden.org/"
            "PlantFinder/PlantFinderSearchResults.aspx")
    url  = f"{base}?basic={quote_plus(name)}"
    if (r := safe_get(url)):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='PlantFinderDetails.aspx']")
        if a and a.get("href"):
            return "https://www.missouribotanicalgarden.org" + a["href"]
    return None

# ─── Selenium search helpers ─────────────────────────────────────────────
def selenium_bing_link(query: str, include: str) -> Optional[str]:
    driver.get(f"https://www.bing.com/search?q={quote_plus(query)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if include in href:
            return href
    return None

def selenium_mbg_link(name: str) -> Optional[str]:
    return selenium_bing_link(f'"{name}" site:missouribotanicalgarden.org',
                              "PlantFinderDetails.aspx")

def selenium_wf_link(name: str) -> Optional[str]:
    return selenium_bing_link(f'"{name}" site:wildflower.org "plants/result.php"',
                              "wildflower.org/plants/result.php")

# ─── Name variants to widen search net ───────────────────────────────────
def name_variants(row):
    names = [row["Botanical Name"]]
    if row.get("Common Name"):
        names.append(row["Common Name"])
    names.append(" ".join(row["Botanical Name"].split()[:2]))  # Genus + species
    return list(dict.fromkeys(names))

# ─── Title must contain each part of botanical name ──────────────────────
def title_contains(botanical: str) -> bool:
    t = driver.title.lower()
    return all(part.lower() in t for part in botanical.split())

# ─── Load input & master CSVs ─────────────────────────────────────────────
df      = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
master  = pd.read_csv(MASTER_CSV, dtype=str).fillna("")
master_index = master.set_index("Botanical Name")

for col in (MBG_COL, WF_COL):
    if col not in df.columns:
        df[col] = ""

# ── 1) Prefill from master CSV ───────────────────────────────────────────
prefilled = 0
for idx, row in df.iterrows():
    bot_name = row["Botanical Name"]
    if bot_name in master_index.index:
        mrow = master_index.loc[bot_name]
        for col in (MBG_COL, WF_COL):
            if not df.at[idx, col] and mrow.get(col, "").startswith("http"):
                df.at[idx, col] = mrow[col]
                prefilled += 1
print(f"🔄 Prefilled {prefilled} links from master.")

# ── 2) Search for still-missing links ────────────────────────────────────
for idx, row in df.iterrows():
    bname = row["Botanical Name"]
    have_mbg = "PlantFinderDetails.aspx" in row[MBG_COL]
    have_wf  = "wildflower.org/plants/result.php" in row[WF_COL]

    print(f"\n🔍 {bname}")

    # MBG search (selenium → fallback HTML)
    if not have_mbg:
        found = False
        for variant in name_variants(row):
            if link := selenium_mbg_link(variant):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, MBG_COL] = link
                    found = True
                    print(f"✅ MBG   → {link}")
                    break
        if not found:
            for variant in name_variants(row):
                if link := query_mbg(variant):
                    driver.get(link); time.sleep(1)
                    if title_contains(bname):
                        df.at[idx, MBG_COL] = link
                        print(f"✅ MBG ♻ → {link}")
                        break
            else:
                print("⚠️  MBG not found")

    # Wildflower search
    if not have_wf:
        for variant in name_variants(row):
            if link := selenium_wf_link(variant):
                driver.get(link); time.sleep(1)
                if title_contains(bname):
                    df.at[idx, WF_COL] = link
                    print(f"✅ WF    → {link}")
                    break
        else:
            print("⚠️  WF not found")

    time.sleep(1.0)  # polite pause

# ── 3) Validate every link added/copied in this run ──────────────────────
def validate_link(url: str) -> bool:
    if not url.startswith("http") or url.startswith("🛑"):
        return False
    r = safe_get(url, retries=0)
    return bool(r)

broken_log = []
for idx, row in df.iterrows():
    for col in (MBG_COL, WF_COL):
        url = row[col]
        if url and not url.startswith("🛑") and not validate_link(url):
            df.at[idx, col] = f"🛑 BROKEN {url}"
            broken_log.append(f"{row['Botanical Name']} → {url}")

if broken_log:
    log_path = OUTPUT_CSV.with_name("broken_links_this_run.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Broken Links Detected This Run\n==============================\n")
        f.writelines(line + "\n" for line in broken_log)
    print(f"\n🛑 {len(broken_log)} broken links flagged. Log → {log_path.name}")
else:
    print("\n✅ All new or copied links responded with HTTP 200.")

# ─── Save & cleanup ──────────────────────────────────────────────────────
driver.quit()
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 Complete → {OUTPUT_CSV.relative_to(BASE)}")
