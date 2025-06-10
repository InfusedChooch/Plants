#!/usr/bin/env python3
# GetLinks.py - Prefill from master first, launch Chrome only if needed (rev-patched)
"""Search web resources to populate missing plant links in the CSV.

Existing links from the master sheet are reused. Any remaining gaps are
queried against several plant databases and nursery sites, optionally
spinning up a headless Chrome session when necessary.
"""
import sys
import argparse
import re
import subprocess
import time
import json
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# --- CLI ----------------------------------------------------------------
parser = argparse.ArgumentParser(description="Fill missing plant site links")
parser.add_argument("--in_csv", default="Outputs/Plants_NeedLinks.csv")  # <- moved
parser.add_argument("--out_csv", default="Outputs/Plants_Linked.csv")  # <- moved
parser.add_argument(
    "--master_csv", default="Templates/Plants_Linked_Filled_Master.csv"
)  # <- moved
parser.add_argument("--chromedriver", default="", help="Path to chromedriver.exe")
parser.add_argument("--chrome_binary", default="", help="Path to chrome.exe")
args = parser.parse_args()

# --- Repo layout & path helpers -----------------------------------------

def repo_dir() -> Path:
    """
    Return the root of the project folder.
    Supports:
    - frozen .exe inside `_internal/helpers`
    - or running from source
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        # If we're in .../_internal/helpers/, go up 2
        if exe_dir.name.lower() == "helpers" and exe_dir.parent.name.lower() == "_internal":
            return exe_dir.parent.parent
        return exe_dir.parent  # fallback: go up 1
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Templates").is_dir() and (parent / "Outputs").is_dir():
            return parent
    return here.parent.parent


REPO = repo_dir()
STATIC = REPO / "Static"  # still contains themes, GoogleChromePortable, etc.


def repo_path(arg: str | Path) -> Path:
    """
    Turn relative CLI strings ('Outputs/...', 'Templates/...', 'Static/...')
    into absolute paths under REPO.  Absolute paths pass through.
    """
    p = Path(arg).expanduser()
    if p.is_absolute():
        return p
    if p.parts and p.parts[0].lower() in {"outputs", "templates", "static"}:
        return (REPO / p).resolve()
    # fallback: relative to script, then repo root
    cand = (Path(__file__).resolve().parent / p).resolve()
    return cand if cand.exists() else (REPO / p).resolve()


INPUT = repo_path(args.in_csv)  # e.g.  .../Outputs/Plants_NeedLinks.csv
OUTPUT = repo_path(args.out_csv)  # e.g.  .../Outputs/Plants_Linked.csv
MASTER = repo_path(args.master_csv)  # e.g.  .../Templates/Plants_Linked_Filled_Master.csv

# first run from a fresh flash-drive: make sure Outputs exists
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS_ALT = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
MBG_COL = "Link: Missouri Botanical Garden"
WF_COL = "Link: Wildflower.org"
PR_COL = "Link: Pleasantrunnursery.com"
NM_COL = "Link: Newmoonnursery.com"
PN_COL = "Link: Pinelandsnursery.com"

# --- Step 1: Load CSVs & prefill from master -----------------------------
df = pd.read_csv(INPUT, dtype=str).fillna("")

rename_map = {
    "Link: Missouri Botanical Garden": MBG_COL,
    "Link: Wildflower.org": WF_COL,
    # accept legacy and new header variants for the nursery links
    "Link: Pleasant Run": PR_COL,
    "Link: Pleasantrunnursery.com": PR_COL,
    "Link: New Moon": NM_COL,
    "Link: Newmoonnursery.com": NM_COL,
    "Link: Pinelands": PN_COL,
    "Link: Pinelandsnursery.com": PN_COL,
}
df.rename(
    columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True
)

# Map legacy/internal column names to the canonical headers above.
reverse_map = {
    "MBG Link": MBG_COL,
    "WF Link": WF_COL,
    "Link: Pleasant Run": PR_COL,
    "Link: New Moon": NM_COL,
    "Link: Pinelands": PN_COL,
}

try:
    master = pd.read_csv(MASTER, dtype=str).fillna("")
    master.rename(
        columns={k: v for k, v in rename_map.items() if k in master.columns},
        inplace=True,
    )
except FileNotFoundError:
    print(f"Master CSV not found at {MASTER} - skipping prefill.")
    master = pd.DataFrame(columns=["Botanical Name", MBG_COL, WF_COL])

m_idx = master.set_index("Botanical Name")

# Ensure columns exist
for col in (MBG_COL, WF_COL, PR_COL, NM_COL, PN_COL):
    if col not in df.columns:
        df[col] = ""

# Prefill from master
pref = 0
for i, row in df.iterrows():
    b = row["Botanical Name"]
    if b in m_idx.index:
        for col in (MBG_COL, WF_COL, PR_COL, NM_COL, PN_COL):
            val = m_idx.at[b, col] if col in m_idx.columns else ""
            if val.startswith("http") and not str(df.at[i, col]).strip():
                df.at[i, col] = val
                pref += 1
print(f"Prefilled {pref} links from master.")


# --- Step 2: Check for needs ---------------------------------------------
def safe_starts(col):
    return (
        df[col].astype(str).str.startswith("http")
        if col in df.columns
        else pd.Series([False] * len(df))
    )


needs = df[
    ~safe_starts(MBG_COL)
    | ~safe_starts(WF_COL)
    | ~safe_starts(PR_COL)
    | ~safe_starts(NM_COL)
    | ~safe_starts(PN_COL)
]

if needs.empty:
    # Normalize any legacy column names before exporting
    df.rename(columns=reverse_map, inplace=True)
    template_cols = list(pd.read_csv(MASTER, nrows=0).columns)
    df = df.reindex(
        columns=template_cols + [c for c in df.columns if c not in template_cols]
    )
    df.to_csv(OUTPUT, index=False, na_rep="")
    print(f"All links present - written straight to {OUTPUT.relative_to(REPO)}")
    raise SystemExit

# --- Step 3: only now import Selenium & start Chrome --------------------
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

# where we look for a bundled chrome.exe
PORT_DIRS = [STATIC / "GoogleChromePortable"]  # legacy


def find_chrome() -> Path:
    # explicit CLI path still wins
    if args.chrome_binary:
        p = Path(args.chrome_binary).expanduser()
        if p.exists():
            return p

    # 1) direct chrome.exe under GoogleChromePortable\App\Chrome-bin\*\chrome.exe
    for exe in (STATIC / "GoogleChromePortable" / "App" / "Chrome-bin").rglob(
        "chrome.exe"
    ):
        return exe  # take the first one found

    # 2) fallback to the launcher (rarely needed)
    launcher = STATIC / "GoogleChromePortable" / "GoogleChromePortable.exe"
    if launcher.exists():
        return launcher

    raise SystemExit(
        "[ERROR] Chrome not found - place portable Chrome in " "Static\\GoogleChromePortable"
    )


def full_ver(bin_path: Path) -> str:
    out = subprocess.check_output(
        [str(bin_path), "--version"], text=True, stderr=subprocess.STDOUT
    )
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else ""


def major(v: str) -> str:
    return v.split(".", 1)[0] if v else ""


# --- Driver discovery ----------------------------------------------------
def find_driver() -> Path:
    """
    Return a working chromedriver.exe.

    Priority:
    1) --chromedriver CLI flag  (file or folder)
    2) Static/Python/chromedriver.exe
    3) Any chromedriver.exe inside Static/GoogleChromePortable/App/Chrome-bin/*
    """
    # 1) explicit CLI path wins
    if args.chromedriver:
        p = Path(args.chromedriver).expanduser()
        return (p / "chromedriver.exe") if p.is_dir() else p

    # 2) standalone driver next to helper scripts
    cand = STATIC / "Python" / "chromedriver.exe"
    if cand.exists():
        return cand

    # 3) driver that ships with portable Chrome
    for drv in (STATIC / "GoogleChromePortable" / "App" / "Chrome-bin").rglob(
        "chromedriver.exe"
    ):
        return drv  # take the first one found

    raise SystemExit(
        "[ERROR] chromedriver.exe not found.\n"
        "Put one in Static\\Python or rely on the copy under "
        "Static\\GoogleChromePortable\\App\\Chrome-bin\\<version>\\"
    )


CHROME_EXE = find_chrome()
DRV_EXE = find_driver()
if not DRV_EXE.exists():
    raise SystemExit(f"[ERROR] chromedriver not found at {DRV_EXE}")

opt = Options()
opt.binary_location = str(CHROME_EXE)
try:
    opt.add_argument("--headless=new")
except:
    opt.add_argument("--headless")
opt.add_argument("--disable-gpu")
opt.add_argument("--blink-settings=imagesEnabled=false")

try:
    driver = webdriver.Chrome(service=Service(str(DRV_EXE)), options=opt)
except WebDriverException as e:
    raise SystemExit(f"[ERROR] Selenium failed to start Chrome:\n{e}")


# --- Helper functions ---------------------------------------------------
def safe_get(url: str, retries=2, delay=2):
    for _ in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 403:
                r = requests.get(url, headers=HEADERS_ALT, timeout=10)
            if r.ok:
                return r
        except Exception:
            pass
        time.sleep(delay)
    return None


def name_variants(row):
    v = [row["Botanical Name"]]
    if row.get("Common Name"):
        v.append(row["Common Name"])
    v.append(" ".join(row["Botanical Name"].split()[:2]))
    return list(dict.fromkeys(v))


def bing_link(q: str, include: str) -> Optional[str]:
    driver.get(f"https://www.bing.com/search?q={quote_plus(q)}")
    time.sleep(1)
    for a in driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]'):
        href = a.get_attribute("href")
        if include in href:
            return href
    return None


def title_ok(botan: str) -> bool:
    return all(p.lower() in driver.title.lower() for p in botan.split())


def query_mbg_html(name: str) -> Optional[str]:
    url = (
        "https://www.missouribotanicalgarden.org/PlantFinder/"
        "PlantFinderSearchResults.aspx?basic=" + quote_plus(name)
    )
    if r := safe_get(url):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='PlantFinderDetails.aspx']")
        if a and a.get("href"):
            return "https://www.missouribotanicalgarden.org" + a["href"]


def query_pr_html(name: str) -> Optional[str]:
    url = (
        "https://www.pleasantrunnursery.com/index.cfm/"
        "fuseaction/plants.kwSearchPost?presearch=" + quote_plus(name)
    )
    if r := safe_get(url):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='/plant-name/']")
        if a and a.get("href"):
            href = a["href"]
            return (
                href
                if href.startswith("http")
                else "https://www.pleasantrunnursery.com" + href
            )


def query_nm_html(name: str) -> Optional[str]:
    url = f"https://newmoonnursery.com/?s={quote_plus(name)}"
    if r := safe_get(url):
        soup = BeautifulSoup(r.text, "lxml")
        a = soup.select_one("a[href*='/nursery-plants/']")
        if a and a.get("href"):
            href = a["href"]
            return (
                href if href.startswith("http") else "https://newmoonnursery.com" + href
            )


def query_pn_html(name: str) -> Optional[str]:
    url = f"https://www.pinelandsnursery.com/search?query={quote_plus(name)}"
    if r := safe_get(url):
        soup = BeautifulSoup(r.text, "lxml")

        # try direct anchor in the product grid
        a = soup.select_one(
            "div.product-name a[href^='https://www.pinelandsnursery.com/']"
        )
        if a and a.get("href"):
            return a["href"]

        # fallback to JSON-LD product data
        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string)
            except Exception:
                continue
            if (
                isinstance(data, dict)
                and data.get("@type") == "Product"
                and data.get("url")
            ):
                return data["url"]
            if isinstance(data, list):
                for item in data:
                    if (
                        isinstance(item, dict)
                        and item.get("@type") == "Product"
                        and item.get("url")
                    ):
                        return item["url"]

        # if no direct product link found, return the search page itself
        return url


# --- Search only rows that still need links -----------------------------
for i, row in needs.iterrows():
    bname = row["Botanical Name"]
    have_mbg = row[MBG_COL].startswith("http")
    have_wf = row[WF_COL].startswith("http")
    have_pr = row[PR_COL].startswith("http")
    have_nm = row[NM_COL].startswith("http")
    have_pn = row[PN_COL].startswith("http")
    print(f"Finding {bname}")

    if not have_mbg:
        for v in name_variants(row):
            if link := bing_link(
                f'"{v}" site:missouribotanicalgarden.org', "PlantFinderDetails.aspx"
            ):
                driver.get(link)
                time.sleep(1)
                if title_ok(bname):
                    df.at[i, MBG_COL] = link
                    print(f" MBG --> {link}")
                    break
        else:
            for v in name_variants(row):
                if link := query_mbg_html(v):
                    df.at[i, MBG_COL] = link
                    print(f" MBG reused {link}")
                    break
            else:
                print("  MBG not found")

    if not have_wf:
        for v in name_variants(row):
            if link := bing_link(
                f'"{v}" site:wildflower.org "plants/result.php"',
                "wildflower.org/plants/result.php",
            ):
                driver.get(link)
                time.sleep(1)
                if title_ok(bname):
                    df.at[i, WF_COL] = link
                    print(f" WF  --> {link}")
                    break
        else:
            print("  WF not found")

    if not have_pr:
        for v in name_variants(row):
            if link := bing_link(
                f'"{v}" site:pleasantrunnursery.com', "pleasantrunnursery.com"
            ):
                driver.get(link)
                time.sleep(1)
                if title_ok(bname):
                    df.at[i, PR_COL] = link
                    print(f" PR  --> {link}")
                    break
        else:
            for v in name_variants(row):
                if link := query_pr_html(v):
                    df.at[i, PR_COL] = link
                    print(f" PR reused {link}")
                    break
            else:
                print("  PR not found")

    if not have_nm:
        for v in name_variants(row):
            if link := bing_link(
                f'"{v}" site:newmoonnursery.com', "newmoonnursery.com"
            ):
                driver.get(link)
                time.sleep(1)
                if title_ok(bname):
                    df.at[i, NM_COL] = link
                    print(f" NM  --> {link}")
                    break
        else:
            for v in name_variants(row):
                if link := query_nm_html(v):
                    df.at[i, NM_COL] = link
                    print(f" NM reused {link}")
                    break
            else:
                print("  NM not found")

    if not have_pn:
        for v in name_variants(row):
            if link := bing_link(
                f'"{v}" site:pinelandsnursery.com', "pinelandsnursery.com"
            ):
                driver.get(link)
                time.sleep(1)
                if title_ok(bname):
                    df.at[i, PN_COL] = link
                    print(f" PN  --> {link}")
                    break
        else:
            for v in name_variants(row):
                if link := query_pn_html(v):
                    df.at[i, PN_COL] = link
                    print(f" PN reused {link}")
                    break
            else:
                print("  PN not found")
    time.sleep(1)

# --- Save & exit --------------------------------------------------------
driver.quit()
df.rename(columns=reverse_map, inplace=True)
template_cols = list(pd.read_csv(MASTER, nrows=0).columns)
df = df.reindex(
    columns=template_cols + [c for c in df.columns if c not in template_cols]
)
df.to_csv(OUTPUT, index=False, na_rep="")
try:
    rel = OUTPUT.relative_to(REPO)
except ValueError:  # outside the repo - show full path
    rel = OUTPUT
print(f"\n Saved -->  {rel}")
