# TestLinks.py ─ Validate every stored link & flag broken ones
#BETAAA

import pandas as pd               # CSV handling
import requests                    # HTTP checking
from pathlib import Path           # fs paths

# ─── Files ───────────────────────────────────────────────────────────────
BASE         = Path(__file__).resolve().parent
INPUT_CSV    = BASE / "Plants_Linked"  # original dataset to verify
OUTPUT_CSV   = INPUT_CSV.with_name(INPUT_CSV.stem + "_flagged.csv")
BROKEN_LOG   = BASE / "broken_links.txt"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}  # polite header
MBG_COL = "Link: Missouri Botanical Garden"
WF_COL  = "Link: Wildflower.org"

# Prepend 🛑 to already-flagged or fresh broken URLs
def flag_broken_link(original: str) -> str:
    return f"🛑 BROKEN {original}" if not original.startswith("🛑") else original

# core validation loop
def validate_and_flag(df: pd.DataFrame) -> pd.DataFrame:
    mbg_ok = wf_ok = 0
    broken = []                             # collect messages for log

    for idx, row in df.iterrows():
        bot_name = row.get("Botanical Name", "").strip()
        mbg_link = row.get(MBG_COL, "").strip()
        wf_link  = row.get(WF_COL, "").strip()

        # ─── MBG check ────────────────────────────────────────────
        if mbg_link.startswith("http"):
            try:
                r = requests.get(mbg_link, headers=HEADERS, timeout=10)
                if r.ok:
                    print(f"✅ MBG OK  → {bot_name} → {mbg_link}")
                    mbg_ok += 1
                else:
                    raise Exception("Bad status")
            except Exception:
                print(f"🛑 MBG ❌ → {bot_name} → {mbg_link}")
                broken.append(f"MBG ❌ {bot_name} → {mbg_link}")
                df.at[idx, MBG_COL] = flag_broken_link(mbg_link)

        # ─── WF check ─────────────────────────────────────────────
        if wf_link.startswith("http"):
            try:
                r = requests.get(wf_link, headers=HEADERS, timeout=10)
                if r.ok:
                    print(f"✅ WF  OK  → {bot_name} → {wf_link}")
                    wf_ok += 1
                else:
                    raise Exception("Bad status")
            except Exception:
                print(f"🛑 WF  ❌ → {bot_name} → {wf_link}")
                broken.append(f"WF ❌ {bot_name} → {wf_link}")
                df.at[idx, WF_COL] = flag_broken_link(wf_link)

    # write summary to text file
    with open(BROKEN_LOG, "w", encoding="utf-8") as f:
        f.write("Broken Links Log\n================\n\n")
        for entry in broken:
            f.write(entry + "\n")
        f.write(f"\nSummary:\nMBG valid: {mbg_ok} / {len(df)}\n"
                f"WF valid: {wf_ok} / {len(df)}\n")

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
