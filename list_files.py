import os

EXCLUDED_DIRS = {".venv", "__pycache__", ".git", ".idea", ".vscode","vendor","pdf_images"}

def list_all_files(base_dir):
    for root, dirs, files in os.walk(base_dir):
        # Modify dirs in-place to skip excluded ones
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for file in files:
            path = os.path.relpath(os.path.join(root, file), base_dir)
            print(path)

if __name__ == "__main__":
    list_all_files(".")


#python list_files.py > file_paths.md