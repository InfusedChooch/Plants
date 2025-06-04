#!/usr/bin/env python3
# GetLinks.py – Prefill from master first, launch Chrome only if needed (rev-patched)

import argparse, io, re, shutil, subprocess, tempfile, time, zipfile, json
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# ─── CLI ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Fill missing plant site links")
parser.add_argument("--in_csv", default="Static/Outputs/Plants_NeedLinks.csv")
parser.add_argument("--out_csv", default="Static/Outputs/Plants_Linked.csv")
parser.add_argument(
    "--master_csv", default="Static/Templates/Plants_Linked_Filled_Master.csv"
)
parser.add_argument(
    "--chromedriver", default="", help="Path to chromedriver.exe (file OR folder)"
)
parser.add_argument(
    "--chrome_binary",
    default="",
    help="Path to chrome.exe (leave blank to auto-detect)",
)
args = parser.parse_args()

# ─── Repo layout ────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
STATIC = BASE.parent
REPO = STATIC.parent


def repo_path(arg: str) -> Path:
    p = Path(arg).expanduser()
    if p.is_absolute():
        return p
    if p.parts and p.parts[0].lower() == "static":
        return (REPO / p).resolve()
    cand = (BASE / p).resolve()
    return cand if cand.exists() else (REPO / p).resolve()


INPUT = repo_path(args.in_csv)
OUTPUT = repo_path(args.out_csv)
MASTER = repo_path(args.master_csv)

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

# ─── Step 1: Load CSVs & prefill from master ─────────────────────────────
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
    print(f"Master CSV not found at {MASTER} – skipping prefill.")
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


# ─── Step 2: Check for needs ─────────────────────────────────────────────
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
    print(f"All links present – written straight to {OUTPUT.relative_to(REPO)}")
    raise SystemExit

# ─── Step 3: only now import Selenium & start Chrome ────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

# where we look for a bundled chrome.exe
PORT_DIRS = [BASE / "GoogleChromePortable"]  # legacy


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
        "❌ Chrome not found – place portable Chrome in " "Static\\GoogleChromePortable"
    )


def full_ver(bin_path: Path) -> str:
    out = subprocess.check_output(
        [str(bin_path), "--version"], text=True, stderr=subprocess.STDOUT
    )
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else ""


def major(v: str) -> str:
    return v.split(".", 1)[0] if v else ""


def find_driver() -> Path:
    # CLI override allowed, else use Static\Python\chromedriver.exe
    if args.chromedriver:
        p = Path(args.chromedriver).expanduser()
        return (p / "chromedriver.exe") if p.is_dir() else p
    drv = BASE / "chromedriver.exe"
    if drv.exists():
        return drv
    raise SystemExit(
        " chromedriver.exe not found in Static\\Python – "
        "copy a matching build there."
    )


CHROME_EXE = find_chrome()
DRV_EXE = find_driver()
if not DRV_EXE.exists():
    raise SystemExit(f"❌ chromedriver not found at {DRV_EXE}")

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
    raise SystemExit(f"❌ Selenium failed to start Chrome:\n{e}")


# ─── Helper functions ───────────────────────────────────────────────────
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


# ─── Search only rows that still need links ─────────────────────────────
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
                    print(f" MBG ♻ {link}")
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
                    print(f" PR ♻ {link}")
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
                    print(f" NM ♻ {link}")
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
                    print(f" PN ♻ {link}")
                    break
            else:
                print("  PN not found")
    time.sleep(1)

# ─── Save & exit ────────────────────────────────────────────────────────
driver.quit()
df.rename(columns=reverse_map, inplace=True)
template_cols = list(pd.read_csv(MASTER, nrows=0).columns)
df = df.reindex(
    columns=template_cols + [c for c in df.columns if c not in template_cols]
)
df.to_csv(OUTPUT, index=False, na_rep="")
try:
    rel = OUTPUT.relative_to(REPO)
except ValueError:  # outside the repo – show full path
    rel = OUTPUT
print(f"\n Saved -->  {rel}")
