#!/usr/bin/env python3
# Static/Python_full/CleanMerge.py – Clean or merge plant data exports using CLI only.

from __future__ import annotations
import argparse, csv, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

MATCH_KEY = "Botanical Name"
NEW_DIR = Path("Outputs/NewMaster")
MISSING = {"", "NA", "N/A", "na"}

COLUMN_ORDER = [
    "Plant Type", "Key", "Botanical Name", "Common Name", "Height (ft)", "Spread (ft)",
    "Bloom Color", "Bloom Time", "Sun", "Water", "AGCP Regional Status",
    "USDA Hardiness Zone", "Attracts", "Tolerates", "Soil Description",
    "Condition Comments", "MaintenanceLevel", "Native Habitats", "Culture", "Uses",
    "UseXYZ", "WFMaintenance", "Problems",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
    "Link: Pleasantrunnursery.com", "Link: Newmoonnursery.com",
    "Link: Pinelandsnursery.com", "Link: Others", "Rev",
]
LINK_COLS = COLUMN_ORDER[-6:-1]
PLANT_ORDER = ["Herbaceous, Perennial", "Ferns", "Grasses, Sedges, and Rushes", "Shrubs", "Trees"]
PLANT_RANK = {pt: i for i, pt in enumerate(PLANT_ORDER)}

def to_md(records):
    esc = lambda t: str(t).replace("|", "\\|")
    hdr = ["| Action | Botanical Name | Note |", "|:------:|:---------------|:----|"]
    rows = [f"| {r['Action']} | {esc(r['Botanical'])} | {esc(r['Note'])} |" for r in records]
    return "\n".join(hdr + rows)

def parse_rev_date(rev: str) -> datetime | None:
    rev = rev.strip()
    if len(rev) >= 8 and rev[:8].isdigit():
        try:
            return datetime.strptime(rev[:8], "%Y%m%d")
        except ValueError:
            return None
    return None

def clean_csv(input_csv: Path, output_csv: Path) -> None:
    df = pd.read_csv(input_csv, dtype=str, encoding="utf-8-sig", keep_default_na=False).fillna("")
    df.columns = [col.replace('\ufeff', '').strip() for col in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    desired_cols = COLUMN_ORDER
    log = []

    TAG_WORDS = ["Masterlist", "FillMissingData", "GetLinks"]
    df = df[~df.apply(lambda row: any(any(tag in str(cell) for tag in TAG_WORDS) for cell in row), axis=1)]

    if "Mark Reviewed" in df.columns:
        df.drop(columns=["Mark Reviewed"], inplace=True)

    for row_idx in df.index:
        for col in df.columns:
            val = str(df.at[row_idx, col]).strip()
            if val == "Needs Review":
                log.append({
                    "Action": "STRIPPED",
                    "Botanical": df.at[row_idx, "Botanical Name"] if "Botanical Name" in df.columns else "",
                    "Note": f"Cleared '{col}' (was: \"{val}\")"
                })
                df.at[row_idx, col] = ""

    if "Rev" not in df.columns:
        df["Rev"] = ""
    df["Rev"] = df["Rev"].astype(str).fillna("").str.strip()

    for col in LINK_COLS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).fillna("").str.strip()
        no_rev = df["Rev"].eq("")
        has_rev = ~no_rev

        stripped = no_rev & df[col].eq("NA")
        for idx in df[stripped].index:
            log.append({"Action": "CLEANED", "Botanical": df.at[idx, "Botanical Name"],
                        "Note": f"Cleared '{col}' (was: \"NA\", no Rev)"})
        df.loc[stripped, col] = ""

        inserted = has_rev & df[col].eq("")
        for idx in df[inserted].index:
            log.append({"Action": "INSERTED", "Botanical": df.at[idx, "Botanical Name"],
                        "Note": f"Inserted 'NA' into '{col}' (Rev present)"})
        df.loc[inserted, col] = "NA"

    for col in desired_cols:
        if col not in df.columns:
            df[col] = ""

    for col in df.columns:
        if col not in desired_cols:
            desired_cols.append(col)

    df = df[desired_cols]

    output_csv.parent.mkdir(exist_ok=True)
    df.to_csv(output_csv, index=False, na_rep="", quoting=csv.QUOTE_ALL)
    print(f"Cleaned CSV saved to: {output_csv}")

    if log:
        log_path = NEW_DIR / f"{output_csv.stem}_clean_log.md"
        log_path.write_text(to_md(log), encoding="utf-8")
        print(f"Clean log saved to: {log_path}")
    else:
        print("No cleaning log to save — no changes found.")

def find_latest_master(input_dir: Path) -> Path | None:
    candidates = sorted(input_dir.glob("20??????_Masterlist.csv"), reverse=True)
    return candidates[0] if candidates else None

def merge_csv(input_csv: Path, master_csv: Path | None = None) -> None:
    if master_csv is None:
        master_csv = find_latest_master(Path("Templates"))

    if not master_csv or not master_csv.exists():
        sys.exit(f"[ERROR] Masterlist not found at: {master_csv}")

    prefix = master_csv.stem.replace("_Masterlist", "")
    out_csv = Path("Outputs/NewMaster") / f"{prefix}_Masterlist_REMOVE.csv"

    vdf = pd.read_csv(input_csv, dtype=str, keep_default_na=False).fillna("")
    mdf = pd.read_csv(master_csv, dtype=str, keep_default_na=False).fillna("")
    log = []

    # Ensure all required columns exist
    for col in COLUMN_ORDER:
        if col not in vdf.columns:
            vdf[col] = ""
        if col not in mdf.columns:
            mdf[col] = ""

    vdf = vdf[COLUMN_ORDER]
    mdf = mdf[COLUMN_ORDER]

    vdf.set_index(MATCH_KEY, inplace=True)
    mdf.set_index(MATCH_KEY, inplace=True)

    for bn, row in vdf.iterrows():
        v_rev = row.get("Rev", "").strip()
        v_date = parse_rev_date(v_rev)

        if bn not in mdf.index:
            mdf.loc[bn] = row
            log.append({"Action": "ADDED", "Botanical": bn, "Note": "New entry from verified list."})
            continue

        m_rev = mdf.at[bn, "Rev"]
        m_date = parse_rev_date(m_rev)

        if not v_date:
                mdf.loc[bn] = row
                log.append({"Action": "MERGED", "Botanical": bn, "Note": "No Rev, combining fields"})
        elif not m_date:
                mdf.loc[bn] = row
                log.append({"Action": "MERGED", "Botanical": bn, "Note": "Master has no Rev, replaced"})
        elif v_date > m_date:
                mdf.loc[bn] = row
                log.append({"Action": "MERGED", "Botanical": bn, "Note": "Verified is newer"})
        else:
                log.append({"Action": "SKIPPED", "Botanical": bn, "Note": "Master has newer or equal Rev."})


    mdf.reset_index(inplace=True)
    mdf["Plant Type"] = mdf["Plant Type"].map(lambda pt: pt if pt in PLANT_RANK else "")
    mdf["__sort_order"] = mdf["Plant Type"].map(lambda pt: PLANT_RANK.get(pt, 99))
    mdf.sort_values(by=["__sort_order", "Botanical Name"], inplace=True)
    mdf.drop(columns=["__sort_order"], inplace=True)

    # Ensure all expected columns exist
    for col in COLUMN_ORDER:
        if col not in mdf.columns:
            mdf[col] = ""

    mdf = mdf[COLUMN_ORDER]


    out_csv.parent.mkdir(exist_ok=True)
    mdf.to_csv(out_csv, index=False, quoting=csv.QUOTE_ALL)
    print(f"Merged master list saved to: {out_csv}")

    if log:
        log_path = NEW_DIR / f"{out_csv.stem}_merge_log.md"
        log_path.write_text(to_md(log), encoding="utf-8")
        print(f"Merge log saved to: {log_path}")


def main():
    ap = argparse.ArgumentParser(description="Clean or merge plant data files.")
    ap.add_argument("--mode", required=True, choices=["clean", "merge"], help="Run mode")
    ap.add_argument("--input", required=True, type=Path, help="Input CSV (dirty file or verified)")
    ap.add_argument("--out", type=Path, help="Optional output CSV (auto-names if clean mode)")
    ap.add_argument("--master", type=Path, help="Optional path to masterlist CSV (for merge)")
    args = ap.parse_args()

    if args.mode == "clean" and not args.out:
        args.out = Path("Outputs") / f"{args.input.stem}_CLEAN.csv"

    if args.mode == "clean":
        clean_csv(args.input, args.out)
    elif args.mode == "merge":
        merge_csv(args.input, args.master)
    else:
        sys.exit("Invalid mode.")

if __name__ == "__main__":
    main()
