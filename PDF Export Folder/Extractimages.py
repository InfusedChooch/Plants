# extract_images_by_page.py — improved naming & output

import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
import re

# ─── PATH SETUP ───────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent
PDF_FILE  = BASE / "Plant Guide Data Base.pdf"
CSV_FILE  = BASE / "Plants_Links_Filled.csv"
OUT_DIR   = BASE / "pdf_images"
MAP_CSV   = BASE / "image_map.csv"
OUT_DIR.mkdir(exist_ok=True)

# ─── Load CSV to map page → names ─────────────────────────────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
page_to_name = {
    int(row["Page in PDF"]): (row["Botanical Name"], row.get("Common Name", ""))
    for _, row in df.iterrows() if row.get("Page in PDF", "").isdigit()
}

# ─── Helper: Slugify botanical names for filenames ────────────────────────
def name_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ─── Open PDF and extract images ─────────────────────────────────────────
doc = fitz.open(PDF_FILE)
image_rows = []

page_image_count = {}

for page_index, page in enumerate(doc, start=1):
    images = page.get_images(full=True)
    if not images:
        continue

    bot_name, com_name = page_to_name.get(page_index, ("", ""))
    base_name = name_slug(bot_name) or f"page_{page_index}"
    page_image_count.setdefault(base_name, 0)

    for img_index, img in enumerate(images, start=1):
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)

        image_num = page_image_count[base_name] + 1
        filename = f"{page_index:03d}_{base_name}_{image_num}.png"
        output_path = OUT_DIR / filename

        if pix.n < 5:
            pix.save(output_path)
        else:
            pix_rgb = fitz.Pixmap(fitz.csRGB, pix)
            pix_rgb.save(output_path)
            pix_rgb = None
        pix = None

        page_image_count[base_name] += 1

        image_rows.append({
            "Image Filename": filename,
            "Page Number": page_index,
            "Botanical Name": bot_name,
            "Common Name": com_name,
        })

# ─── Save mapping ────────────────────────────────────────────────────────
pd.DataFrame(image_rows).to_csv(MAP_CSV, index=False)
print(f"✅ Extracted {len(image_rows)} images")
print(f"🗂  Image mapping written to → {MAP_CSV}")

# ─── Optional: Convert extracted PNGs to JPEGs ───────────────────────────
from PIL import Image

jpeg_dir = OUT_DIR / "jpeg"
jpeg_dir.mkdir(exist_ok=True)

converted = 0
for png_file in OUT_DIR.glob("*.png"):
    img = Image.open(png_file).convert("RGB")
    jpg_file = jpeg_dir / (png_file.stem + ".jpg")
    img.save(jpg_file, "JPEG", quality=85)
    converted += 1

print(f"📸 Converted {converted} PNG images to JPEGs in → {jpeg_dir}")
