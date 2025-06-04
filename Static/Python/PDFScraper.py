# /Static/Python/PDFScraper.py
# Description: Extracts plant data, hyperlinks, and images from a PDF plant guide.

import argparse
import re
import csv
from pathlib import Path
from typing import Set, List, Dict
import sys

import pandas as pd
import pdfplumber
from tqdm import tqdm
import fitz  # PyMuPDF
from PIL import Image

# ─── CLI Arguments ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Extract plant data from a PDF guide.")
parser.add_argument("--in_pdf", default="Static/Templates/Plant Guide 2025 Update.pdf", help="PDF input file")
parser.add_argument("--out_csv", default="Static/Outputs/Plants_NeedLinks.csv", help="CSV output file")
parser.add_argument("--img_dir", default="Static/Outputs/pdf_images", help="Directory for PNG dump")
parser.add_argument("--map_csv", default="Static/Outputs/image_map.csv", help="Image → plant map CSV")
args = parser.parse_args()

# ─── Paths ───────────────────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent
PDF_PATH = Path(args.in_pdf).resolve()
OUT_CSV  = Path(args.out_csv).resolve()
IMG_DIR  = Path(args.img_dir).resolve()
MAP_CSV  = Path(args.map_csv).resolve()
IMG_DIR.mkdir(exist_ok=True)

# ─── Safe Print ──────────────────────────────────────────────────────────
def safe_print(*objs, **kw):
    try:
        print(*objs, **kw)
    except UnicodeEncodeError:
        txt = " ".join(str(o) for o in objs)
        fallback = txt.encode(sys.stdout.encoding or "ascii", "ignore").decode()
        print(fallback, **kw)

# ─── CSV Columns ─────────────────────────────────────────────────────────
COLUMNS = [
    "Page in PDF", "Plant Type", "Key",
    "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)",
    "Bloom Color", "Bloom Time", "Sun", "Water",
    "Characteristics", "Habitats",
    "Wildlife Benefits", "Zone",
    "MBG Link", "WF Link",
]

# ─── Regex Patterns ──────────────────────────────────────────────────────
BOT_LINE_RE = re.compile(r"^[A-Z][A-Za-z×\-]+\s+[A-Za-z×\-]*[a-z][A-Za-z×\-]*(?:\s+[A-Za-z×\-]+){0,3}$")
BOT_ANY_RE  = re.compile(r"\b([A-Z][A-Za-z×\-]+ [A-Za-z×\-]*[a-z][A-Za-z×\-]*(?: [A-Za-z×\-]+){0,3})\b")
STOPWORDS   = {"Plant Fact", "Plant Fact Sheet", "Plant Symbol", "Plant Materials", "Plant Materials Programs", "Contributed by"}
HEIGHT_RE   = re.compile(r"height[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)
SPREAD_RE   = re.compile(r"(?:spread|aerial spread)[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)

# ─── Utility Functions ───────────────────────────────────────────────────
def clean(line: str) -> str:
    return re.split(r"[,(–-]", line, 1)[0].strip()

def is_all_caps_common(l: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9\s\-]{1,}$", l)) and 1 <= len(l.split()) <= 5

def guess_common(lines: List[str], bot_idx: int) -> str:
    for i in range(bot_idx - 1, max(-1, bot_idx - 6), -1):
        ln = lines[i]
        if is_all_caps_common(ln) and all(sw not in ln for sw in STOPWORDS):
            return ln
    for ln in lines[bot_idx + 1:]:
        if not any(tag in ln.lower() for tag in ["plant symbol", "description", "contributed by"]):
            return ln
    return ""

def gen_key(bot_name: str, used: Set[str]) -> str:
    parts = bot_name.split()
    if len(parts) < 2:
        base = "".join([w[0] for w in parts])[:2].upper() or "XX"
    else:
        base = (parts[0][0] + parts[1][0]).upper()
    suffix, i = "", 1
    while base + suffix in used:
        suffix = str(i)
        i += 1
    used.add(base + suffix)
    return base + suffix

def name_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ─── Link & Type Mapping ─────────────────────────────────────────────────
def extract_links_by_page(pdf_path: Path) -> Dict[int, List[str]]:
    doc = fitz.open(pdf_path)
    page_links = {}
    for page_num, page in enumerate(doc, start=1):
        links = []
        for link in page.get_links():
            uri = link.get("uri") or link.get("action", {}).get("uri")
            if uri:
                links.append(uri.strip())
        if links:
            page_links[page_num] = list(set(links))
    return page_links

def build_page_type_map(pdf_path: Path) -> Dict[int, str]:
    valid_types = {
        "HERBACEOUS, PERENNIAL": "Herbaceous, Perennial",
        "FERNS": "Ferns",
        "GRASSES, SEDGES, AND RUSHES": "Grasses, Sedges, and Rushes",
        "SHRUBS": "Shrubs",
        "TREES": "Trees",
    }
    page_type_map = {}
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").upper()
            match = next((v for k, v in valid_types.items() if k in text), "")
            page_type_map[idx] = match
    return page_type_map


# ─── Row & Image Extraction ──────────────────────────────────────────────
def extract_rows() -> List[Dict[str, str]]:
    rows, used_keys = [], set()
    page_type_map = build_page_type_map(PDF_PATH)
    skip_pages = {p for p, t in page_type_map.items() if not t}
    link_map = extract_links_by_page(PDF_PATH)

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, pg in enumerate(tqdm(pdf.pages, desc="Scanning PDF")):
            page_num = idx + 1
            if page_num in skip_pages:
                continue
            text = pg.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            bot_idx = None
            bot_name = com_name = ""

            for i, ln in enumerate(lines[:15]):
                cand = clean(ln)
                if any(sw in cand for sw in STOPWORDS):
                    continue
                if BOT_LINE_RE.match(cand):
                    bot_idx, bot_name = i, cand
                    com_name = guess_common(lines, bot_idx)
                    break
            if bot_idx is None and len(lines) >= 2:
                if BOT_LINE_RE.match(clean(lines[0])):
                    bot_name, com_name, bot_idx = clean(lines[0]), clean(lines[1]), 0
            if not bot_name:
                for m in BOT_ANY_RE.finditer(text):
                    cand = clean(m.group(1))
                    if any(sw in cand for sw in STOPWORDS):
                        continue
                    bot_name, com_name = cand, guess_common(lines, 0)
                    lines.insert(0, cand)
                    break
            if not bot_name:
                continue

            body = "\n".join(lines)
            height = f"{m.group(1)} - {m.group(2)}" if (m := HEIGHT_RE.search(body)) and m.group(2) else (m.group(1) if m else "")
            spread = f"{m.group(1)} - {m.group(2)}" if (m := SPREAD_RE.search(body)) and m.group(2) else (m.group(1) if m else "")
            links = link_map.get(page_num, [])
            mbg = next((l for l in links if "missouribotanicalgarden" in l.lower()), "")
            wf  = next((l for l in links if "wildflower.org" in l.lower()), "")

            rows.append({
                "Page in PDF": str(page_num),
                "Plant Type": page_type_map.get(page_num, ""),
                "Key": gen_key(bot_name, used_keys),
                "Botanical Name": bot_name,
                "Common Name": com_name,
                "Height (ft)": height,
                "Spread (ft)": spread,
                **{c: "" for c in COLUMNS if c not in {
                    "Page in PDF", "Plant Type", "Key", "Botanical Name", "Common Name", "Height (ft)", "Spread (ft)", "Link: Missouri Botanical Garden", "Link: Wildflower.org"}},
                "Link: Missouri Botanical Garden": mbg,
                "Link: Wildflower.org": wf,
            })
    return rows

def extract_images(df: pd.DataFrame) -> None:
    doc = fitz.open(PDF_PATH)
    image_rows = []
    page_to_name = {
        int(r["Page in PDF"]): (r["Botanical Name"], r.get("Common Name", ""))
        for _, r in df.iterrows() if r.get("Page in PDF", "").isdigit()
    }
    page_image_count = {}
    for page_index, page in enumerate(doc, start=1):
        images = page.get_images(full=True)
        if not images:
            continue
        bot_name, com_name = page_to_name.get(page_index, (f"Page_{page_index}", ""))
        base_name = name_slug(bot_name)
        page_image_count.setdefault(base_name, 0)
        for img_index, img in enumerate(images, start=1):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            count = page_image_count[base_name]
            filename = f"{base_name}_{count}.png"
            output_path = IMG_DIR / filename
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
    pd.DataFrame(image_rows).to_csv(MAP_CSV, index=False)
    safe_print(f"📸 Extracted {len(image_rows)} images to {IMG_DIR}")
    safe_print(f"🗂  Mapping written to {MAP_CSV}")

    jpeg_dir = IMG_DIR / "jpeg"
    jpeg_dir.mkdir(exist_ok=True)
    converted = 0
    for png_file in IMG_DIR.glob("*.png"):
        img = Image.open(png_file).convert("RGB")
        jpg_file = jpeg_dir / (png_file.stem + ".jpg")
        img.save(jpg_file, "JPEG", quality=85)
        converted += 1
    safe_print(f"📸 Converted {converted} PNG images to JPEGs in {jpeg_dir}")

# ─── Main ────────────────────────────────────────────────────────────────
def main():
    df = pd.DataFrame(extract_rows(), columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    safe_print(f"✅ Saved → {OUT_CSV.name} ({len(df)} rows)")
    extract_images(df)

if __name__ == "__main__":
    main()
