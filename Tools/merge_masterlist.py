#!/usr/bin/env python3
"""
merge_masterlist.py  –  Overwrite rows where Botanical Name matches,
                         keep fixed column order,
                         custom-sort by Plant Type hierarchy,
                         guarantee LINK columns contain 'NA' when blank,
                         output merged CSV + Markdown log to NEW/.
"""
from __future__ import annotations
import argparse, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# ───────────────────────────────────────── Configuration ──────────────────── #
MATCH_KEY = "Botanical Name"
NEW_DIR   = Path("NEW")
MISSING   = {"", "NA", "N/A", "na"}

COLUMN_ORDER = [
    "Plant Type","Key","Botanical Name","Common Name","Height (ft)","Spread (ft)",
    "Bloom Color","Bloom Time","Sun","Water","AGCP Regional Status",
    "USDA Hardiness Zone","Attracts","Tolerates","Soil Description",
    "Condition Comments","MaintenanceLevel","Native Habitats","Culture","Uses",
    "UseXYZ","WFMaintenance","Problems",
    "Link: Missouri Botanical Garden","Link: Wildflower.org",
    "Link: Pleasantrunnursery.com","Link: Newmoonnursery.com",
    "Link: Pinelandsnursery.com",
]
LINK_COLS = COLUMN_ORDER[-5:]                # the five link columns

PLANT_ORDER = [
    "Herbaceous, Perennial",
    "Ferns",
    "Grasses, Sedges, And Rushes",
    "Shrubs",
    "Trees",
]
PLANT_RANK = {pt: i for i, pt in enumerate(PLANT_ORDER)}
# ──────────────────────────────────────────────────────────────────────────── #

def to_md(records):
    esc = lambda t: str(t).replace("|","\\|")
    hdr = ["| Action | Botanical Name | Note |",
           "|:------:|:---------------|:----|"]
    rows = [f"| {r['Action']} | {esc(r['Botanical'])} | {esc(r['Note'])} |"
            for r in records]
    return "\n".join(hdr + rows)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--master",   default="Templates/0611_Masterlist_New_Beta_Nodata.csv")
    ap.add_argument("--verified", default="Templates/Plants_Linked_Verified.csv")
    tag = datetime.now().strftime("%m%d")
    ap.add_argument("--out",      default=f"{tag}_Masterlist_New_Beta_Nodata_NEW.csv")
    args = ap.parse_args(argv)

    # ▸ Load files
    try:
        master   = pd.read_csv(args.master,   dtype=str).fillna("")
        verified = pd.read_csv(args.verified, dtype=str).fillna("")
    except FileNotFoundError as e:
        sys.exit(f"❌ File not found: {e.filename}")
    if MATCH_KEY not in master.columns or MATCH_KEY not in verified.columns:
        sys.exit(f"❌ Column '{MATCH_KEY}' missing in one of the files.")

    m_idx = master.set_index(MATCH_KEY)
    v_idx = verified.set_index(MATCH_KEY)
    log   = []

    # ▸ Overwrite rows whose Botanical Name appears in verified
    overlap = m_idx.index.intersection(v_idx.index)
    for bn in overlap:
        m_idx.loc[bn] = v_idx.loc[bn]
        log.append(dict(Action="OVERWRITTEN", Botanical=bn,
                        Note="Row replaced from verified file"))

    # ▸ Append completely new plants
    new_rows = v_idx.loc[v_idx.index.difference(m_idx.index)]
    if not new_rows.empty:
        m_idx = pd.concat([m_idx, new_rows])
        for bn in new_rows.index:
            log.append(dict(Action="ADDED", Botanical=bn, Note="Row added from verified file"))
        print(f"➕ Added {len(new_rows)} new plant(s).")

    # ▸ Ensure NEW/ exists
    NEW_DIR.mkdir(exist_ok=True)
    out_path = Path(args.out)
    if out_path.parent == Path("."):
        out_path = NEW_DIR / out_path.name

    # ▸ Restore columns in fixed order
    merged = m_idx.reset_index()
    for col in COLUMN_ORDER:
        if col not in merged.columns:
            merged[col] = ""
    extra = [c for c in merged.columns if c not in COLUMN_ORDER]
    merged = merged[COLUMN_ORDER + extra]

    # ▸ Convert blank link fields to 'NA'
    for col in LINK_COLS:
        merged.loc[merged[col].str.strip() == "", col] = "NA"

    # ▸ Custom sort: Plant-Type rank then Botanical Name
    merged["__rank"] = merged["Plant Type"].map(lambda v: PLANT_RANK.get(v, len(PLANT_ORDER)))
    merged = merged.sort_values(["__rank", "Botanical Name"],
                                kind="mergesort").drop(columns="__rank")

    # ▸ Save merged CSV
    merged.to_csv(out_path, index=False, na_rep="")
    print(f"✅ Merged CSV → {out_path.resolve()}")

    # ▸ Save Markdown log
    if log:
        log_path = out_path.with_name(out_path.stem + "_merge_log.md")
        log_path.write_text(to_md(log), encoding="utf-8")
        print(f"📝 Log → {log_path.resolve()}")
    else:
        print("ℹ️  No differences found – nothing to log.")

if __name__ == "__main__":
    main()
