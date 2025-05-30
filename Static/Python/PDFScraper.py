# PDFScraper.py
# Description: Extracts plant data, hyperlinks, and images from a PDF plant guide
import argparse
import re  # built-in library for regular expressions (pattern matching in text)
import csv  # built-in library for reading/writing CSV files
from pathlib import Path  # to work with filesystem paths in a cross-platform way
from typing import Set, List, Dict  # type annotations for better code clarity

import pandas as pd  # popular library for data manipulation and CSV export
import pdfplumber  # library to extract text content from PDF pages
from tqdm import tqdm  # shows a progress bar when iterating over long loops
import fitz  # PyMuPDF: advanced PDF handling, used here for links and images
from PIL import Image  # Python Imaging Library (Pillow) for image conversion and saving

# ─── CLI Arguments ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Extract plant data from a PDF guide.")
parser.add_argument("--in_pdf", default="Static/Templates/Plant Guide 2025 Update.pdf", help="PDF input file")
parser.add_argument("--out_csv", default="Static/Outputs/Plants_NeedLinks.csv", help="CSV output file")
parser.add_argument("--img_dir", default= "Static/Outputs/pdf_images", help="Directory for PNG Dump")
parser.add_argument("--map_csv", default= "Static/Outputs/image_map.csv", help="Directory for IMG Map")

args = parser.parse_args()

# ─── Paths ───────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent  # directory where this script resides
PDF_PATH = BASE / args.in_pdf
OUT_CSV  = BASE / args.out_csv
IMG_DIR = BASE / args.img_dir
MAP_CSV = BASE / args.map_csv  # CSV that maps saved image files to plant entries

# create the image directory if it doesn't already exist
IMG_DIR.mkdir(exist_ok=True)

# ─── CSV Columns ─────────────────────────────────────────────────────────
# the exact order and names of columns in our final CSV output
COLUMNS = [
    "Page in PDF", "Plant Type", "Key",
    "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)",
    "Bloom Color", "Bloom Time", "Sun", "Water",
    "Characteristics", "Habitats",
    "Wildlife Benefits", "Distribution",
    "Link: Missouri Botanical Garden", "Link: Wildflower.org",
]

# ─── Regex Patterns ──────────────────────────────────────────────────────
# pattern to match lines that look like botanical names (e.g., Genus species)
BOT_LINE_RE = re.compile(r"^[A-Z][A-Za-z×\-]+\s+[A-Za-z×\-]*[a-z][A-Za-z×\-]*(?:\s+[A-Za-z×\-]+){0,3}$")
# fallback pattern to find any two-word capitalized phrase in text
BOT_ANY_RE = re.compile(r"\b([A-Z][A-Za-z×\-]+ [A-Za-z×\-]*[a-z][A-Za-z×\-]*(?: [A-Za-z×\-]+){0,3})\b")
# words to ignore when guessing where the botanical name appears in the page text
STOPWORDS = {"Plant Fact", "Plant Fact Sheet", "Plant Symbol", "Plant Materials", "Plant Materials Programs", "Contributed by"}
# pattern to extract height measurements in feet
HEIGHT_RE = re.compile(r"height[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)
# pattern to extract spread (width) measurements in feet
SPREAD_RE = re.compile(r"(?:spread|aerial spread)[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[-–]|to)\s*([\d.]+))?\s*ft", re.I)

# ─── Utility Functions ───────────────────────────────────────────────────

def clean(line: str) -> str:
    """Remove trailing commas, parentheses, or dashes and strip whitespace."""
    return re.split(r"[,(–-]", line, 1)[0].strip()


def is_all_caps_common(l: str) -> bool:
    """Return True if line is all-caps short phrase (likely a common name header)."""
    return bool(re.fullmatch(r"[A-Z][A-Z0-9\s\-]{1,}$", l)) and 1 <= len(l.split()) <= 5


def guess_common(lines: List[str], bot_idx: int) -> str:
    """
    Find a common name near the botanical name index:
    - look up to 5 lines above for an ALL CAPS line
    - otherwise, take the first non-header line after the botanical name
    """
    # check lines above for an all-caps candidate
    for i in range(bot_idx - 1, max(-1, bot_idx - 6), -1):
        ln = lines[i]
        if is_all_caps_common(ln) and all(sw not in ln for sw in STOPWORDS):
            return ln
    # fallback: pick the next non-header line below
    for ln in lines[bot_idx + 1:]:
        lower = ln.lower()
        if any(tag in lower for tag in ["plant symbol", "description", "contributed by"]):
            continue
        return ln
    return ""


def gen_key(bot_name: str, used: Set[str]) -> str:
    """
    Generate a short unique key from the botanical name initials,
    e.g., "Quercus rubra" -> "QR" or "QR1" if "QR" already used.
    """
    parts = bot_name.split()
    if len(parts) < 2:
        # if only one word, use first two letters
        base = "".join([w[0] for w in parts])[:2].upper() or "XX"
    else:
        # use first letters of genus and species
        g, s = parts[:2]
        base = (g[0] + s[0]).upper()
    suffix, i = "", 1
    # avoid duplicates by appending numbers
    while base + suffix in used:
        suffix = str(i)
        i += 1
    used.add(base + suffix)
    return base + suffix


def name_slug(text: str) -> str:
    """Convert text to lowercase underscore-separated slug for filenames."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ─── Hyperlink Extraction ────────────────────────────────────────────────

def extract_links_by_page(pdf_path: Path) -> Dict[int, List[str]]:
    """
    Open the PDF with PyMuPDF, loop pages, extract all URIs (web links),
    and return a dict mapping page number to list of unique links.
    """
    doc = fitz.open(pdf_path)
    page_links: Dict[int, List[str]] = {}
    for page_num, page in enumerate(doc, start=1):
        links = []
        for link in page.get_links():
            uri = link.get("uri") or link.get("action", {}).get("uri")
            if uri:
                links.append(uri.strip())
        if links:
            page_links[page_num] = list(set(links))  # dedupe
    return page_links

# ─── Plant Type Mapping by Page ─────────────────────────────────────────

def build_page_type_map(pdf_path: Path) -> Dict[int, str]:
    """
    Identify section headings (e.g., "HERBACEOUS PERENNIALS").
    Map every page in each section to its plant type label.
    """
    headings = {
        "HERBACEOUS PERENNIALS": "Herbaceous, Perennial",
        "FERNS": "Ferns",
        "GRASSES, SEDGES, AND RUSHES": "Grasses, Sedges, and Rushes",
        "SHRUBS": "Shrubs",
        "TREES": "Trees",
    }
    title_pages: List[tuple[int, str]] = []
    # scan first two lines of each page for section titles
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            lines = [ln.strip() for ln in (page.extract_text() or "").splitlines()]
            for line in lines[:2]:
                if line.upper() in headings:
                    title_pages.append((idx, headings[line.upper()]))
                    break
    # build map: from the start of a section to the next section start
    page_type_map: Dict[int, str] = {}
    for i, (start_page, label) in enumerate(title_pages):
        end_page = title_pages[i + 1][0] if i + 1 < len(title_pages) else float('inf')
        for p in range(start_page + 1, int(end_page)):
            page_type_map[p] = label
        # mark the heading page itself as skipped (empty type)
        page_type_map[start_page] = ""
    return page_type_map

# ─── Extract Rows of Plant Data ───────────────────────────────────────────

def extract_rows() -> List[Dict[str, str]]:
    """
    Loop through every page, skip non-data pages,
    find botanical and common names, measurements, links,
    generate a unique key, and collect a row dict.
    """
    rows: List[Dict[str, str]] = []
    used_keys: Set[str] = set()
    page_type_map = build_page_type_map(PDF_PATH)
    # skip pages that are section titles
    skip_pages = {p for p, t in page_type_map.items() if not t}
    link_map = extract_links_by_page(PDF_PATH)

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, pg in enumerate(tqdm(pdf.pages, desc="Scanning PDF")):
            page_num = idx + 1
            if page_num in skip_pages:
                continue  # skip heading pages

            text = pg.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            bot_idx = None
            bot_name = ""
            com_name = ""

            # try to find botanical name in the first 15 lines
            for i, ln in enumerate(lines[:15]):
                cand = clean(ln)
                if any(sw in cand for sw in STOPWORDS):
                    continue
                if BOT_LINE_RE.match(cand):
                    bot_idx = i
                    bot_name = cand
                    com_name = guess_common(lines, bot_idx)
                    break

            # fallback: first two lines if they fit expected patterns
            if bot_idx is None and len(lines) >= 2:
                possible_bot = clean(lines[0])
                possible_com = clean(lines[1])
                if BOT_LINE_RE.match(possible_bot):
                    bot_name = possible_bot
                    com_name = possible_com
                    bot_idx = 0

            # last resort: search entire page for any two-word capitalized phrase
            if not bot_name:
                for m in BOT_ANY_RE.finditer(text):
                    cand = clean(m.group(1))
                    if any(sw in cand for sw in STOPWORDS):
                        continue
                    bot_name = cand
                    com_name = guess_common(lines, 0)
                    lines.insert(0, cand)  # ensure botanical name is first
                    break

            if not bot_name:
                continue  # skip pages without identifiable plant

            # combine all lines for regex searching
            body = "\n".join(lines)
            height = spread = ""
            # extract height
            if (m := HEIGHT_RE.search(body)):
                height = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)
            # extract spread
            if (m := SPREAD_RE.search(body)):
                spread = f"{m.group(1)} - {m.group(2)}" if m.group(2) else m.group(1)

            # pick out MBG and WF links if present on this page
            links = link_map.get(page_num, [])
            mbg = next((l for l in links if "missouribotanicalgarden" in l.lower()), "")
            wf = next((l for l in links if "wildflower.org" in l.lower()), "")

            # assemble a row dict with all columns
            row = {
                "Page in PDF": str(page_num),
                "Plant Type": page_type_map.get(page_num, ""),
                "Key": gen_key(bot_name, used_keys),
                "Botanical Name": bot_name,
                "Common Name": com_name,
                "Height (ft)": height,
                "Spread (ft)": spread,
                # initialize other columns to empty strings
                **{c: "" for c in COLUMNS if c not in {
                    "Page in PDF","Plant Type","Key",
                    "Botanical Name","Common Name",
                    "Height (ft)","Spread (ft)",
                    "Link: Missouri Botanical Garden","Link: Wildflower.org"
                }},
                "Link: Missouri Botanical Garden": mbg,
                "Link: Wildflower.org": wf,
            }
            rows.append(row)
    return rows

# ─── Extract Images from PDF and Map to Plants ───────────────────────────

def extract_images(df: pd.DataFrame) -> None:
    """
    For each page with images,
    save all images to disk, record filename and plant mapping in a CSV,
    then convert all PNGs to JPGs for smaller file size.
    """
    doc = fitz.open(PDF_PATH)
    image_rows = []
    # build a simple map from page number to plant names
    page_to_name = {
        int(r["Page in PDF"]): (r["Botanical Name"], r.get("Common Name", ""))
        for _, r in df.iterrows() if r.get("Page in PDF", "").isdigit()
    }

    page_image_count: Dict[str, int] = {}
    for page_index, page in enumerate(doc, start=1):
        images = page.get_images(full=True)
        if not images:
            continue  # skip pages without images

        bot_name, com_name = page_to_name.get(page_index, ("Page {page_index}", ""))
        base_name = name_slug(bot_name)
        page_image_count.setdefault(base_name, 0)

        for img_index, img in enumerate(images, start=1):
            xref = img[0]  # internal reference number for the image
            pix = fitz.Pixmap(doc, xref)  # load the image as a pixmap
            count = page_image_count[base_name] + 1
            filename = f"{page_index:03d}_{base_name}_{count}.png"
            output_path = IMG_DIR / filename
            # save as PNG or convert CMYK to RGB first
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

    # write the image mapping CSV
    pd.DataFrame(image_rows).to_csv(MAP_CSV, index=False)
    print(f"📸 Extracted {len(image_rows)} images to {IMG_DIR}")
    print(f"🗂  Mapping written to {MAP_CSV}")

    # convert all saved PNGs into JPEGs for compatibility and smaller size
    jpeg_dir = IMG_DIR / "jpeg"
    jpeg_dir.mkdir(exist_ok=True)
    converted = 0
    for png_file in IMG_DIR.glob("*.png"):
        img = Image.open(png_file).convert("RGB")
        jpg_file = jpeg_dir / (png_file.stem + ".jpg")
        img.save(jpg_file, "JPEG", quality=85)
        converted += 1
    print(f"📸 Converted {converted} PNG images to JPEGs in → {jpeg_dir}")

# ─── Main Entry Point ────────────────────────────────────────────────────

def main() -> None:
    """Run the full PDF scrape: rows first, then images."""
    # extract data rows and write to CSV
    df = pd.DataFrame(extract_rows(), columns=COLUMNS)
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"✅ Saved → {OUT_CSV.name} ({len(df)} rows)")
    # extract images based on the CSV we just wrote
    extract_images(df)

if __name__ == "__main__":
    main()  # run the script if called directly
