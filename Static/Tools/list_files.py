# Tools/list_files.py
# Output filtered file/folder list to file_paths.md, respecting skip rules

import os
from pathlib import Path

EXCLUDED_DIRS = {".venv", "__pycache__", ".git", ".idea", ".vscode", "vendor"}

# Directories to skip files *within* (but still list the folder itself)
NO_FILE_DIRS = {
    Path("Static/GoogleChromePortable"),
    Path("Outputs/html_cache"),
    Path("Outputs/Images/Plants"),
}

def skip_files_in_dir(rel_path: Path) -> bool:
    """Check if files in this folder should be skipped."""
    return any(rel_path == p or p in rel_path.parents for p in NO_FILE_DIRS)

def list_all_paths(base_dir: Path) -> list[str]:
    base_dir = base_dir.resolve()
    output = []

    for root, dirs, files in os.walk(base_dir):
        rel_root = Path(root).relative_to(base_dir)

        # Skip system directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        # Always include the folder path
        output.append(rel_root.as_posix() if rel_root != Path(".") else ".")

        # Conditionally skip files
        if not skip_files_in_dir(rel_root):
            for file in files:
                output.append((rel_root / file).as_posix())

    return output

if __name__ == "__main__":
    cwd = Path.cwd()
    out_file = cwd / "file_paths.md"
    paths = list_all_paths(cwd)
    out_file.write_text("\n".join(paths), encoding="utf-8")
    print(f"[OK] Wrote {len(paths)} paths to {out_file}")
