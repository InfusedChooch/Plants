
from __future__ import annotations
import argparse, sys, csv
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# ───────────── CLI ────────────────────────────────────────────────────────
def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diff two plant CSVs.")
    p.add_argument(
        "test_csv",
        nargs="?",
        default="ReviewFiles\SampleTest\Plants_Linked_Filled_Test.csv",
        help="Scraper output CSV (default: %(default)s)",
    )
    p.add_argument(
        "gold_csv",
        nargs="?",
        default="ReviewFiles\SampleTest\Plants_Linked_FIlled_Manual.csv",
        help="Hand-filled gold standard CSV (default: %(default)s)",
    )
    p.add_argument(
        "--out",
        default="SampleTest/DiffReport.csv",
        metavar="FILE",
        help="Write mismatches to CSV (default: %(default)s)",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        metavar="N",
        help="Show only first N mismatches in console",
    )
    return p.parse_args()


# ──────────── helpers ─────────────────────────────────────────────────────
LINK_COL_PREFIX = "Link:"


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        console.print(f"[red]ERROR:[/red] file not found → {path}")
        sys.exit(2)
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")


def row_key(row: pd.Series) -> str:
    """Unique row identifier: Key if present, else Botanical Name."""
    return (row.get("Key") or row.get("Botanical Name") or "").strip()


def diff_frames(test: pd.DataFrame, gold: pd.DataFrame) -> list[tuple]:
    """Return list of mismatches (key, column, gold, test)."""
    t_index = {row_key(r): i for i, r in test.iterrows()}
    g_index = {row_key(r): i for i, r in gold.iterrows()}

    mismatches: list[tuple] = []
    shared_cols = [
        c
        for c in gold.columns
        if not c.startswith(LINK_COL_PREFIX) and c in test.columns
    ]

    for key, g_i in g_index.items():
        if key == "":
            continue
        if key not in t_index:
            mismatches.append((key, "<ROW>", "", "<missing in test CSV>"))
            continue
        t_i = t_index[key]
        for col in shared_cols:
            want = str(gold.at[g_i, col]).strip()
            got = str(test.at[t_i, col]).strip()
            if want != got:
                mismatches.append((key, col, want, got))

    # rows present only in test
    for key in t_index.keys() - g_index.keys():
        mismatches.append((key, "<ROW>", "<missing in gold CSV>", ""))

    return mismatches


def write_csv(rows: list[tuple], out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Key / Botanical", "Column", "Gold value", "Scraper value","Rev Note"])
        w.writerows(rows)
    console.print(f"[cyan]Diff written → {out_file}[/cyan]")


# ───────────── main ───────────────────────────────────────────────────────
def main() -> None:
    args = parse_cli()

    test_df = load(Path(args.test_csv))
    gold_df = load(Path(args.gold_csv))

    diffs = diff_frames(test_df, gold_df)

    if not diffs:
        console.print("[green]✓ No differences found.[/green]")
        sys.exit(0)

    # pretty console table
    table = Table(
        "Key/Botanical",
        "Column",
        "Gold",
        "Scraper",
        show_lines=True,
    )
    shown = 0
    for row in diffs:
        if args.max is not None and shown >= args.max:
            break
        table.add_row(*row)
        shown += 1

    console.print(table)
    if args.max and shown < len(diffs):
        console.print(f"[bold]{len(diffs) - shown}[/bold] more mismatch(es) …")

    # export full diff
    write_csv(diffs, Path(args.out))
    sys.exit(1)


if __name__ == "__main__":
    main()
