import os

# Folders to ignore (by full normalized relative path from base)
EXCLUDED_DIRS = {
    ".venv", "__pycache__", ".git", ".idea", ".vscode", "vendor",
    os.path.normpath("Static/Outputs/pdf_images"),
    os.path.normpath("Static/GoogleChromePortable"),
}

def should_skip(path, base_dir):
    # Convert absolute path to normalized relative for comparison
    rel_path = os.path.relpath(path, base_dir)
    norm_path = os.path.normpath(rel_path)
    for excluded in EXCLUDED_DIRS:
        if norm_path == excluded or norm_path.startswith(excluded + os.sep):
            return True
    return False

def list_all_files(base_dir):
    base_dir = os.path.abspath(base_dir)
    for root, dirs, files in os.walk(base_dir):
        # Remove excluded subdirectories before continuing
        dirs[:] = [d for d in dirs if not should_skip(os.path.join(root, d), base_dir)]

        if should_skip(root, base_dir):
            continue

        for file in files:
            path = os.path.relpath(os.path.join(root, file), base_dir)
            print(path)

if __name__ == "__main__":
    list_all_files(".")


#python list_files.py > file_paths.md