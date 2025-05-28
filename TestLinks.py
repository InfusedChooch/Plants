# /plants/TestLinks.py
# Validates MBG/WF links, flags broken ones, logs them

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path

BASE         = Path(__file__).resolve().parent
INPUT_CSV    = BASE / "Plants and Links.csv"
OUTPUT_CSV   = INPUT_CSV.with_name(INPUT_CSV.stem + "_flagged.csv")
BROKEN_LOG   = BASE / "broken_links.txt"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
MBG_COL = "Link: Missouri Botanical Garden"
WF_COL  = "Link: Wildflower.org"

def fetch_title(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.ok:
            soup = BeautifulSoup(r.text, "lxml")
            return soup.title.string.strip() if soup.title else None
    except requests.RequestException:
        return None
    return None

def flag_broken_link(original: str) -> str:
    return f"🛑 BROKEN {original}" if not original.startswith("🛑") else original

def validate_and_flag(df: pd.DataFrame) -> pd.DataFrame:
    mbg_ok = wf_ok = 0
    broken = []

    for idx, row in df.iterrows():
        bot_name = row.get("Botanical Name", "").strip()
        mbg_link = row.get(MBG_COL, "").strip()
        wf_link  = row.get(WF_COL, "").strip()

        # ─── MBG Check (title-based) ─────────────────────────────
        if mbg_link.startswith("http"):
            title = fetch_title(mbg_link)
            if not title or not all(part.lower() in title.lower() for part in bot_name.split()):
                msg = f"MBG ❌ {bot_name} → {mbg_link}"
                print(msg)
                broken.append(msg)
                df.at[idx, MBG_COL] = flag_broken_link(mbg_link)
            else:
                mbg_ok += 1

        # ─── WF Check (HTTP status only) ─────────────────────────
        if wf_link.startswith("http"):
            try:
                r = requests.get(wf_link, headers=HEADERS, timeout=10)
                if r.ok:
                    wf_ok += 1
                else:
                    raise Exception("Bad status")
            except Exception:
                msg = f"WF  ❌ {bot_name} → {wf_link}"
                print(msg)
                broken.append(msg)
                df.at[idx, WF_COL] = flag_broken_link(wf_link)

    with open(BROKEN_LOG, "w", encoding="utf-8") as f:
        f.write("Broken Links Log\n")
        f.write("================\n\n")
        for entry in broken:
            f.write(entry + "\n")
        f.write(f"\nSummary:\nMBG valid: {mbg_ok} / {len(df)}\nWF valid: {wf_ok} / {len(df)}\n")

    print("\n✅ Summary:")
    print(f"✔️  MBG valid: {mbg_ok} / {len(df)}")
    print(f"✔️  WF  valid: {wf_ok} / {len(df)}")
    print(f"📝 Log saved → {BROKEN_LOG.name}")
    return df

def main():
    df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    if "Botanical Name" not in df.columns:
        print("❌ Missing 'Botanical Name' column.")
        return

    flagged = validate_and_flag(df)
    flagged.to_csv(OUTPUT_CSV, index=False)
    print(f"💾 Flagged file saved → {OUTPUT_CSV.name}")

if __name__ == "__main__":
    main()
