from pathlib import Path
import importlib.util
import sys
import pandas as pd


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("fillmod", path)
    module = importlib.util.module_from_spec(spec)
    orig_argv = sys.argv
    sys.argv = [orig_argv[0]]  # prevent argparse from consuming pytest args
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = orig_argv
    return module


def test_fill_csv_matches_manual(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    mod = load_module(repo_root / "SampleTest" / "FillMissingData_Test.py")

    in_csv = repo_root / "SampleTest" / "Plants_Linked.csv"
    master = repo_root / "Templates" / "0610_Masterlist_New_Beta_Nodata.csv"
    # write inside repo so relative_to(REPO) succeeds
    out_csv = repo_root / "SampleTest" / "Plants_Linked_Filled_Test.csv"

    mod.fill_csv(in_csv, out_csv, master)

    df_generated = pd.read_csv(out_csv, dtype=str).fillna("")
    df_manual = pd.read_csv(repo_root / "SampleTest" / "Plants_Linked_FIlled_Manual.csv", dtype=str).fillna("")

    if not df_generated.equals(df_manual):
        diffs = []
        diff_mask = df_generated != df_manual
        for idx in df_generated.index:
            if diff_mask.loc[idx].any():
                for col in df_generated.columns[diff_mask.loc[idx]]:
                    diffs.append(
                        f"row {idx} col '{col}': '{df_generated.at[idx, col]}' != '{df_manual.at[idx, col]}'"
                    )
        diff_report = "\n".join(diffs[:10])
        assert False, f"DataFrames differ:\n{diff_report}"