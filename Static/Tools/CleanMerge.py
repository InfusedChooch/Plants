#!/usr/bin/env python3
"""
merge_masterlist.py  –  Overwrite rows where Botanical Name matches,
                         keep fixed column order,
                         custom-sort by Plant Type hierarchy,
                         enforce 'NA' only with Rev,
                         output merged CSV + Markdown log to Outputs/NewMaster/.
"""
from __future__ import annotations
import argparse, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# ───────────────────────────────────────── Configuration ──────────────────── #
MATCH_KEY = "Botanical Name"
NEW_DIR   = Path("Outputs/NewMaster")
MISSING   = {"", "NA", "N/A", "na"}

COLUMN_ORDER = [
    "Plant Type","Key","Botanical Name","Common Name","Height (ft)","Spread (ft)",
    "Bloom Color","Bloom Time","Sun","Water","AGCP Regional Status",
    "USDA Hardiness Zone","Attracts","Tolerates","Soil Description",
    "Condition Comments","MaintenanceLevel","Native Habitats","Culture","Uses",
    "UseXYZ","WFMaintenance","Problems",
    "Link: Missouri Botanical Garden","Link: Wildflower.org",
    "Link: Pleasantrunnursery.com","Link: Newmoonnursery.com",
    "Link: Pinelandsnursery.com","Rev",
]
LINK_COLS = COLUMN_ORDER[-6:-1]

PLANT_ORDER = [
    "Herbaceous, Perennial",
    "Ferns",
    "Grasses, Sedges, and Rushes",
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

def parse_rev_date(rev: str) -> datetime | None:
    rev = rev.strip()
    if len(rev) >= 8 and rev[:8].isdigit():
        try:
            return datetime.strptime(rev[:8], "%Y%m%d")
        except ValueError:
            return None
    return None

def clean_csv_from_excel(input_csv: Path, template_csv: Path, output_csv: Path) -> None:
    df = pd.read_csv(input_csv, dtype=str, encoding="cp1252", keep_default_na=False).fillna("")
    template_df = pd.read_csv(template_csv, dtype=str, keep_default_na=False, nrows=0)
    desired_cols = list(template_df.columns)
    log = []


    # Step 1: Drop metadata row with known tag keywords
    TAG_WORDS = ["Masterlist", "FillMissingData", "GetLinks"]
    df = df[~df.apply(lambda row: any(any(tag in str(cell) for tag in TAG_WORDS) for cell in row), axis=1)]


    # Step 2: Drop "Mark Reviewed" column if it exists
    if "Mark Reviewed" in df.columns:
        df.drop(columns=["Mark Reviewed"], inplace=True)

    # Step 3: Strip "Needs Review" and log
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

    # Step 4: Link cleanup
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

    # Step 5: Reorder and fill missing columns
    for col in desired_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[desired_cols]

    output_csv.parent.mkdir(exist_ok=True)
    df.to_csv(output_csv, index=False, na_rep="")
    print(f"Cleaned CSV saved to: {output_csv}")

    # Step 6: Save log
    if log:
        log_path = NEW_DIR / "Plants_Linked_Filled_Reviewed_Clean_log.md"
        log_path.write_text(to_md(log), encoding="utf-8")
        print(f"Clean log saved to: {log_path}")
    else:
        print("No cleaning log to save — no changes found.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["merge", "clean"], default="clean", help="Choose: merge (default) or clean")

    ap.add_argument("--master",   default="Templates/0612_Masterlist_RO.csv")
    ap.add_argument("--verified", default="Outputs/Plants_Linked_Filled_Reviewed_Clean.csv")
    ap.add_argument("--template", default="Templates/Plants_Template.csv")
    ap.add_argument("--input",    default="Outputs/Plants_Linked_Filled_Reviewed.csv")

    tag = datetime.now().strftime("%m%d")
    ap.add_argument("--out", default=f"{tag}_Masterlist_Merged.csv")
    args = ap.parse_args(argv)

    if args.mode == "clean":
        clean_csv_from_excel(
            input_csv=Path(args.input),
            template_csv=Path(args.template),
            output_csv=Path("Outputs/Plants_Linked_Filled_Reviewed_Clean.csv")
        )
        return

    try:
        master   = pd.read_csv(args.master, dtype=str, keep_default_na=False).fillna("")
        verified = pd.read_csv(args.verified, dtype=str, keep_default_na=False).fillna("")
    except FileNotFoundError as e:
        sys.exit(f"❌ File not found: {e.filename}")
    if MATCH_KEY not in master.columns or MATCH_KEY not in verified.columns:
        sys.exit(f"❌ Column '{MATCH_KEY}' missing in one of the files.")

    m_idx = master.set_index(MATCH_KEY)
    v_idx = verified.set_index(MATCH_KEY)
    log   = []

    overlap = m_idx.index.intersection(v_idx.index)
    for bn in overlap:
        rev_m = str(m_idx.at[bn, "Rev"]).strip() if isinstance(m_idx.at[bn, "Rev"], str) else str(m_idx.loc[bn, "Rev"].iloc[0]).strip()
        rev_v = str(v_idx.at[bn, "Rev"]).strip() if isinstance(v_idx.at[bn, "Rev"], str) else str(v_idx.loc[bn, "Rev"].iloc[0]).strip()

        date_m = parse_rev_date(rev_m)
        date_v = parse_rev_date(rev_v)

        if not rev_m or not rev_v or not date_m or not date_v:
            for col in v_idx.columns:
                if col not in m_idx.columns:
                    continue
                val_master = str(m_idx.at[bn, col]).strip()
                val_verified = str(v_idx.at[bn, col]).strip()
                if (not val_master or val_master in MISSING) and val_verified and val_verified not in MISSING:
                    m_idx.at[bn, col] = val_verified
                    reason = "Rev missing" if not rev_m or not rev_v else "Rev parse failed"
                    log.append(dict(Action="UPDATED", Botanical=bn,
                                    Note=f"Filled missing field ({reason}): {col}"))
        else:
            if date_v > date_m:
                m_idx.loc[bn] = v_idx.loc[bn]
                log.append(dict(Action="OVERWRITTEN", Botanical=bn,
                                Note=f"Replaced (newer Rev: {rev_v} > {rev_m})"))
            else:
                log.append(dict(Action="SKIPPED", Botanical=bn,
                                Note=f"Kept (older or equal Rev: {rev_v} <= {rev_m})"))

    new_rows = v_idx.loc[v_idx.index.difference(m_idx.index)]
    if not new_rows.empty:
        m_idx = pd.concat([m_idx, new_rows])
        for bn in new_rows.index:
            log.append(dict(Action="ADDED", Botanical=bn, Note="Row added from verified file"))
        print(f"➕ Added {len(new_rows)} new plant(s).")

    out_path = NEW_DIR / Path(args.out).name
    NEW_DIR.mkdir(exist_ok=True)

    merged = m_idx.reset_index()
    for col in COLUMN_ORDER:
        if col not in merged.columns:
            merged[col] = ""
    extra = [c for c in merged.columns if c not in COLUMN_ORDER]
    merged = merged[COLUMN_ORDER + extra]

    for col in LINK_COLS:
        merged[col] = merged[col].fillna("").astype(str).str.strip()
        merged["Rev"] = merged["Rev"].fillna("").astype(str).str.strip()

        no_rev = merged["Rev"].str.len() == 0
        has_rev = ~no_rev

        stripped = (no_rev & (merged[col] == "NA"))
        for idx in merged[stripped].index:
            log.append(dict(Action="CLEANED", Botanical=merged.at[idx, "Botanical Name"],
                            Note=f"Cleared '{col}' (NA not allowed without Rev)"))
        merged.loc[stripped, col] = ""
        merged.loc[has_rev & (merged[col] == ""), col] = "NA"

    merged["__rank"] = merged["Plant Type"].map(lambda v: PLANT_RANK.get(v, len(PLANT_ORDER)))
    merged = merged.sort_values(["__rank", "Botanical Name"], kind="mergesort").drop(columns="__rank")

    merged.to_csv(out_path, index=False, na_rep="")
    print(f" Merged CSV -> {out_path.resolve()}")

    if log:
        log_path = out_path.with_name(out_path.stem + "_merge_log.md")
        log_path.write_text(to_md(log), encoding="utf-8")
        print(f" Log -> {log_path.resolve()}")
    else:
        print("No differences found – nothing to log.")

if __name__ == "__main__":
    main()
