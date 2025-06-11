from pathlib import Path
import ast
import types


def load_function(path: str | Path, name: str):
    """Load a single function from a Python file without executing the script."""
    source = Path(path).read_text()
    tree = ast.parse(source, filename=str(path))
    module = types.ModuleType("temp")
    module.__dict__["__file__"] = str(path)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            exec(compile(ast.Module([node], type_ignores=[]), str(path), "exec"), module.__dict__)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            exec(compile(ast.Module([node], type_ignores=[]), str(path), "exec"), module.__dict__)
            return getattr(module, name)
    raise AttributeError(f"{name} not found in {path}")


def test_repo_dir_detects_project_root():
    repo_dir = load_function("Static/Python_lite/Excelify2.py", "repo_dir")
    root = repo_dir()
    assert (root / "Templates").is_dir()
    assert (root / "Outputs").is_dir()


def test_name_slug_simple_cases():
    name_slug = load_function("Static/Python_lite/GeneratePDF.py", "name_slug")
    assert name_slug("Hello World!") == "hello_world"
    assert name_slug(" Plant--Name! ") == "plant_name"
    assert name_slug("Plant 123? ok") == "plant_123_ok"


def test_month_list_range_handling():
    month_list = load_function("SampleTest/FillMissingData_Test.py", "month_list")
    month_list.__globals__["MONTHS"] = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    assert month_list("Feb - Jul") == "Feb, Mar, Apr, May, Jun, Jul"

def test_color_list_examples():
    color_list = load_function("SampleTest/FillMissingData_Test.py", "color_list")
    clean = load_function("SampleTest/FillMissingData_Test.py", "clean")
    NORMALISE = {
        "full sun to part shade": "Full Sun, Part Shade",
        "dry to medium": "dry, medium",
    }
    color_list.__globals__["clean"] = clean
    clean.__globals__["NORMALISE"] = NORMALISE
    assert color_list("red and yellow") == "Red, Yellow"
    assert color_list("white/pink") == "White, Pink"
    assert color_list("blue with white") == "Blue, White"
    assert color_list("red, red") == "Red"


def test_merge_field_stable_ordering():
    merge_field = load_function("SampleTest/FillMissingData_Test.py", "merge_field")
    a = merge_field("Butterflies, Bees", "Birds")
    b = merge_field("Bees, Butterflies", "Birds")
    assert a == "Bees, Birds, Butterflies"
    assert a == b