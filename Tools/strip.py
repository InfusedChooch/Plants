# strip_number_prefixes.py
# Removes 3-digit number prefix from filenames in image folders.

from pathlib import Path
import re


def strip_prefix(folder: Path):
    for file in folder.glob("*.*"):
        match = re.match(r"^\d{3}_(.+)", file.name)
        if match:
            new_name = match.group(1)
            new_path = file.parent / new_name
            if not new_path.exists():
                file.rename(new_path)
                print(f"✅ Renamed: {file.name} → {new_name}")
            else:
                print(f"⚠️ Skipped (already exists): {new_name}")
        else:
            print(f"⏭️ No prefix match: {file.name}")


if __name__ == "__main__":
    base = Path("Static/Outputs/pdf_images")
    jpeg = base / "jpeg"

    print("📁 Cleaning:", base)
    strip_prefix(base)

    print("\n📁 Cleaning:", jpeg)
    strip_prefix(jpeg)
