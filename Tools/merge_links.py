#!/usr/bin/env python3
"""
merge_masterlist.py - Overwrite or extend the master plant list with data
                      from Plants_Linked_Verified.csv.

Defaults:
  --master   Templates/0610_Masterlist_New_Beta_Nodata.csv
  --verified Templates/Plants_Linked_Verified.csv
  --out      <mmdd>_Masterlist_New_Beta_Nodata_NEW.csv  (saved to project root)
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration
MATCH_KEY = "Key"                         # column used to identify plants
MISSING_STRINGS = {"", "NA", "N/A", "na"} # what counts as blank
# --------------------------------------------------------------------------- #

def is_missing(value) -> bool:
    """True if *value* is blank or NA."""
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() in MISSING_STRINGS:
        return True
    return False

def merge_rows(master_row: pd.Series, verified_row: pd.Series) -> pd.Series:
    """Copy every non-blank field from verified_row into master_row."""
    for col, v_val in verified_row.items():
        if col == MATCH_KEY:
            continue
        if not is_missing(v_val):
            master_row[col] = v_val
    return master_row

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge verified plants into master list.")
    parser.add_argument("--master", default="Templates/0611_Masterlist_New_Beta_Nodata.csv",
                        help="Path to current master list CSV")
    parser.add_argument("--verified", default="Templates/Plants_Linked_Verified.csv",
                        help="Path to verified plants CSV")
    today_tag = datetime.now().strftime("%m%d")
    default_out = f"{today_tag}_Masterlist_New_Beta_Nodata_NEW.csv"
    parser.add_argument("--out", default=default_out,
                        help="Output CSV filename (saved to script folder)")
    args = parser.parse_args(argv)

    # Load CSVs as strings (so existing NA strings survive)
    try:
        master_df = pd.read_csv(args.master, dtype=str).fillna("")
    except FileNotFoundError as e:
        sys.exit(f"Master list not found: {e.filename}")
    try:
        verified_df = pd.read_csv(args.verified, dtype=str).fillna("")
    except FileNotFoundError as e:
        sys.exit(f"Verified file not found: {e.filename}")

    # Merge
    verified_index = verified_df.set_index(MATCH_KEY)
    for idx, m_row in master_df.set_index(MATCH_KEY).iterrows():
        if idx in verified_index.index:
            updated = merge_rows(m_row, verified_index.loc[idx])
            master_df.loc[master_df[MATCH_KEY] == idx] = updated.values

    # Append brand-new plants
    new_rows = verified_df[~verified_df[MATCH_KEY].isin(master_df[MATCH_KEY])]
    if not new_rows.empty:
        master_df = pd.concat([master_df, new_rows], ignore_index=True)
        print(f"Added {len(new_rows)} new plant(s) from verified file.")

    # Save
    out_path = Path(args.out)
    master_df.to_csv(out_path, index=False, na_rep="")
    print(f"Merged master list written to {out_path.resolve()}")

if __name__ == "__main__":
    main()
