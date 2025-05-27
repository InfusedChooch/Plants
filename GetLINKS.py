# plants/GetLINKS.py
# Uses Selenium to find MBG + Wildflower links and appends them to the CSV

import re, time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ─── configuration ──────────────────────────────────────────────────────────
INPUT_CSV  = "Plant Data Base WIP.csv"
OUTPUT_CSV = "Plant Data Base WIP_COMPLETE.csv"
MBG_COL    = "Link: Missouri Botanical Garden"
WF_COL     = "Link: Wildflower.org"

# ─── Selenium setup ─────────────────────────────────────────────────────────
opt = Options()
opt.add_argument("--start-minimized")
opt.add_argument("--disable-gpu")
opt.add_argument("--log-level=3")
driver = webdriver.Chrome(options=opt)

# ─── load / prepare DataFrame ───────────────────────────────────────────────
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
for col in (MBG_COL, WF_COL):
    if col not in df.columns:
        df[col] = ""

# ─── helper: google CSE for MBG ─────────────────────────────────────────────
def google_mbg_link(name: str) -> str | None:
    search_url = (
        "https://cse.google.com/cse"
        "?cx=015816930756675652018:7gxyi5crvvu&q=" + "+".join(name.split())
    )
    driver.get(search_url)
    time.sleep(1.5)
    links = driver.find_elements(By.XPATH, '//a[contains(@href,"PlantFinderDetails.aspx")]')
    for a in links:
        href = a.get_attribute("href")
        if "PlantFinderDetails.aspx" in href:
            return href
    return None

# ─── helper: Bing search for Wildflower.org ─────────────────────────────────
def bing_wildflower_link(name: str) -> str | None:
    query = "site:wildflower.org " + name
    driver.get("https://www.bing.com/search?q=" + "+".join(query.split()))
    time.sleep(1.5)
    links = driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]')
    for a in links:
        href = a.get_attribute("href")
        if "wildflower.org/plants/result.php?id_plant=" in href:
            return href
    return None

# ─── main loop ─────────────────────────────────────────────────────────────
for idx, row in df.iterrows():
    name      = row["Botanical Name"]
    have_mbg  = "PlantFinderDetails.aspx" in row[MBG_COL]
    have_wf   = "wildflower.org/plants/result.php" in row[WF_COL]
    if have_mbg and have_wf:
        continue

    print(f"\n🔍 {name}")
    if not have_mbg:
        link = google_mbg_link(name)
        if link:
            df.at[idx, MBG_COL] = link
            print(f"✅ MBG  → {link}")
        else:
            print("⚠️  MBG  → not found")

    if not have_wf:
        link = bing_wildflower_link(name)
        if link:
            df.at[idx, WF_COL] = link
            print(f"✅ WF   → {link}")
        else:
            print("⚠️  WF   → not found")

    time.sleep(1.0)

driver.quit()
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 All done → {OUTPUT_CSV}")
