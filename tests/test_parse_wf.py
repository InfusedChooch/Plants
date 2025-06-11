from pathlib import Path
from tests.REM_test_fill_csv import load_module


def test_parse_wf_native_habitat():
    repo_root = Path(__file__).resolve().parents[1]
    mod = load_module(repo_root / "SampleTest" / "FillMissingData_Test.py")
    html = (repo_root / "SampleTest" / "html_cache" / "www_wildflower_org_plants_result_php_50c22c56894c.html").read_text()
    data = mod.parse_wf(html)
    assert "Native Habitats" in data
    assert "Wet Meadow" in data["Native Habitats"]
