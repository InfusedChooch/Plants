# tests/Spotcheck.py
# Robust link spot checker using requests with fallback to Selenium for 403s and mismatches
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
import argparse
from tqdm import tqdm
from urllib.parse import urlparse
import re

def parse_cli_args():
    parser = argparse.ArgumentParser(description="Robust link spot checker")
    parser.add_argument("--in_csv", default="Templates/Linkcheck.csv", help="Input CSV file")
    parser.add_argument("--out_csv", default="Outputs/link_spotcheck_results.csv", help="Output CSV file")
    parser.add_argument("--retry_browser", action="store_true", help="Retry 403s/mismatches using Selenium")
    return parser.parse_args()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS_ALT = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def get_title_with_requests(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 403:
            r = requests.get(url, headers=HEADERS_ALT, timeout=10)
        if r.ok:
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.title.string.strip() if soup.title else "[No Title]"
            return title, r.status_code
        return "[Unavailable]", r.status_code
    except Exception as e:
        return f"[ERROR] {e}", 0

def name_matches(title, bot_name, com_name):
    title = title.lower()
    return (
        bot_name.lower() in title or
        com_name.lower() in title or
        " ".join(bot_name.lower().split()[:2]) in title
    )

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

def init_browser():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--blink-settings=imagesEnabled=false")
    opt.add_argument("--log-level=3")
    try:
        driver = webdriver.Chrome(options=opt)
        return driver
    except WebDriverException as e:
        print("[ERROR] Selenium driver failed:", e)
        return None

def get_title_with_selenium(driver, url):
    try:
        driver.get(url)
        title = driver.title
        return title.strip() if title else "[No Title]"
    except Exception as e:
        return f"[SE ERROR] {e}"


def main():
    args = parse_cli_args()
    df = pd.read_csv(args.in_csv).fillna("")
    results = []
    link_cols = [
        "Link: Missouri Botanical Garden",
        "Link: Wildflower.org",
        "Link: Pleasantrunnursery.com",
        "Link: Newmoonnursery.com",
        "Link: Pinelandsnursery.com",
    ]
    with tqdm(total=len(df) * len(link_cols), desc="Checking links") as pbar:
        for _, row in df.iterrows():
            bot_name = str(row.get("Botanical Name", "")).strip()
            com_name = str(row.get("Common Name", "")).strip()
            for col in link_cols:
                url = row.get(col, "").strip()
                if not url:
                    results.append({
                        "Botanical Name": bot_name,
                        "Common Name": com_name,
                        "Source": col,
                        "Match": "❌ MISSING",
                        "Title": "",
                        "URL": ""
                    })
                    pbar.update(1)
                    continue
                title, status = get_title_with_requests(url)
                matched = name_matches(title, bot_name, com_name)
                if args.retry_browser and (not matched or status == 403):
                    if "driver" not in locals():
                        driver = init_browser()
                    if driver:
                        title = get_title_with_selenium(driver, url)
                        matched = name_matches(title, bot_name, com_name)
                result = {
                    "Botanical Name": bot_name,
                    "Common Name": com_name,
                    "Source": col,
                    "Match": "✔" if matched else f"❌ ({status})",
                    "Title": title,
                    "URL": url
                }
                results.append(result)
                pbar.update(1)

    out_df = pd.DataFrame(results)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out_csv, index=False)
    if "driver" in locals() and driver: driver.quit()
    print(f"[DONE] Spotcheck complete → {args.out_csv}")

if __name__ == "__main__":
    main()
