import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# === File Setup ===
INPUT_CSV = "Plant Data Base WIP.csv"
OUTPUT_CSV = "Plant Data Base WIP_COMPLETE.csv"
MBG_COL = "Link: Missouri Botanical Garden"
WF_COL = "Link: Wildflower.org"

# === Browser Setup ===
options = Options()
options.add_argument("--start-minimized")  # shows browser briefly, not headless
options.add_argument("--disable-gpu")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(options=options)

# === Load Data ===
df = pd.read_csv(INPUT_CSV)
if MBG_COL not in df.columns:
    df[MBG_COL] = ""
if WF_COL not in df.columns:
    df[WF_COL] = ""

# === MBG Search ===
def get_mbg_link(botanical_name):
    """Search MBG via Google CSE and return the first matching PlantFinder link."""
    url = f"https://cse.google.com/cse?cx=015816930756675652018:7gxyi5crvvu&q={'%20'.join(botanical_name.split())}"
    driver.get(url)
    time.sleep(2)
    try:
        links = driver.find_elements(By.XPATH, '//a[contains(@href, "PlantFinderDetails.aspx")]')
        for link in links:
            href = link.get_attribute("href")
            if "PlantFinderDetails.aspx" in href:
                return href
    except:
        return None
    return None

# === Wildflower Search (mimics your manual entry) ===
def get_wildflower_link(botanical_name):
    query = f"site:wildflower.org {botanical_name}"
    url = f"https://www.bing.com/search?q={'+'.join(query.split())}"
    driver.get(url)
    time.sleep(2)

    links = driver.find_elements(By.XPATH, '//li[@class="b_algo"]//a[@href]')
    for link in links:
        href = link.get_attribute("href")
        if "wildflower.org/plants/result.php?id_plant=" in href:
            return href
    return None




# === Main Loop ===
for idx, row in df.iterrows():
    name = row["Botanical Name"]

    has_mbg = isinstance(row[MBG_COL], str) and "PlantFinderDetails.aspx" in row[MBG_COL]
    has_wf = isinstance(row[WF_COL], str) and "wildflower.org/plants/result.php" in row[WF_COL]

    if has_mbg and has_wf:
        continue

    print(f"\n🔍 {name}")

    if not has_mbg:
        mbg = get_mbg_link(name)
        if mbg:
            df.at[idx, MBG_COL] = mbg
            print(f"✅ MBG: {mbg}")
        else:
            print("⚠️  No MBG link found")

    if not has_wf:
        wf = get_wildflower_link(name)
        if wf:
            df.at[idx, WF_COL] = wf
            print(f"✅ WF: {wf}")
        else:
            print("⚠️  No Wildflower link found")

    time.sleep(1.5)

driver.quit()

# === Save Results ===
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n🎉 Done! File saved as → {OUTPUT_CSV}")
