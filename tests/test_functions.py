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

