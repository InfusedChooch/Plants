# /Static/Python/PDFScraper.py
"""Extract plant data, hyperlinks and images from a source PDF."""

import argparse
import re
import csv
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Set, List, Dict
import sys

import pandas as pd
import pdfplumber
from tqdm import tqdm
import fitz  # PyMuPDF
from PIL import Image

# --- CLI Arguments --------------------------------------------------------
parser = argparse.ArgumentParser(description="Extract plant data from a PDF guide.")
parser.add_argument(
    "--in_pdf",
    default="Templates/Plant Guide 2025 Update.pdf",  # <- moved
    help="PDF input file",
)
parser.add_argument(
    "--out_csv",
    default="Outputs/Plants_NeedLinks.csv",  # <- moved
    help="CSV output file",
)
parser.add_argument(
    "--img_dir",
    default="Outputs/pdf_images",  # <- moved
    help="Directory for PNG dump",
)
parser.add_argument(
    "--map_csv",
    default="Outputs/image_map.csv",  # <- moved
    help="Image -> plant map CSV",
)
args = parser.parse_args()


# --- Path helpers --------------------------------------------------------
def repo_dir() -> Path:
    """Return bundle root when frozen, or repo root when running from source."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        return exe_dir.parent if exe_dir.name.lower() == "helpers" else exe_dir
    # scripts now live in `Python/` -> repo is two parents up
    return Path(__file__).resolve().parent.parent


REPO = repo_dir()


def repo_path(rel: str | Path) -> Path:
    """
    Convert a relative CLI string ('Outputs/...', 'Templates/...', 'Static/...')
    into an absolute path under REPO. Absolute paths pass through unchanged.
    """
    p = Path(rel).expanduser()
    if p.is_absolute():
        return p
    if p.parts and p.parts[0].lower() in {"outputs", "templates", "static"}:
        return (REPO / p).resolve()
    # fallback: make it relative to script, then repo
    cand = (Path(__file__).resolve().parent / p).resolve()
    return cand if cand.exists() else (REPO / p).resolve()


PDF_PATH = repo_path(args.in_pdf)
OUT_CSV = repo_path(args.out_csv)
IMG_DIR = repo_path(args.img_dir)
MAP_CSV = repo_path(args.map_csv)

# ensure folders exist when running from a fresh flash-drive
IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)


# --- Safe Print ----------------------------------------------------------
def safe_print(*objs, **kw):
    try:
        print(*objs, **kw)
    except UnicodeEncodeError:
        txt = " ".join(str(o) for o in objs)
        fallback = txt.encode(sys.stdout.encoding or "ascii", "ignore").decode()
        print(fallback, **kw)


# --- CSV Columns ---------------------------------------------------------
MASTER_CSV = Path("Static/Templates/Plants_Linked_Filled_Master.csv").resolve()
template_cols = list(pd.read_csv(MASTER_CSV, nrows=0).columns)

master_df = pd.read_csv(MASTER_CSV, dtype=str).fillna("")
master_idx = master_df.set_index("Botanical Name")

COLUMNS = ["Page in PDF"] + template_cols

# --- Regex Patterns ------------------------------------------------------
BOT_LINE_RE = re.compile(
    r"^[A-Z][A-Za-z×\-]+\s+[A-Za-z×\-]*[a-z][A-Za-z×\-]*(?:\s+[A-Za-z×\-]+){0,3}$"
)
BOT_ANY_RE = re.compile(
    r"\b([A-Z][A-Za-z×\-]+ [A-Za-z×\-]*[a-z][A-Za-z×\-]*(?: [A-Za-z×\-]+){0,3})\b"
)
STOPWORDS = {
    "Plant Fact",
    "Plant Fact Sheet",
    "Plant Symbol",
    "Plant Materials",
    "Plant Materials Programs",
    "Contributed by",
}
HEIGHT_RE = re.compile(
    r"height[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[--]|to)\s*([\d.]+))?\s*ft", re.I
)
SPREAD_RE = re.compile(
    r"(?:spread|aerial spread)[^:;\n]*?(?:up to\s*)?([\d.]+)(?:\s*(?:[--]|to)\s*([\d.]+))?\s*ft",
    re.I,
)


# --- Utility Functions ---------------------------------------------------
def clean(line: str) -> str:
    return re.split(r"[,(--]", line, 1)[0].strip()


def is_all_caps_common(l: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9\s\-]{1,}$", l)) and 1 <= len(l.split()) <= 5


def guess_common(lines: List[str], bot_idx: int) -> str:
    for i in range(bot_idx - 1, max(-1, bot_idx - 6), -1):
        ln = lines[i]
        if is_all_caps_common(ln) and all(sw not in ln for sw in STOPWORDS):
            return ln
    for ln in lines[bot_idx + 1 :]:
        if not any(
            tag in ln.lower()
            for tag in ["plant symbol", "description", "contributed by"]
        ):
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


def guess_botanical_from_links(links: List[str]) -> str:
    """Try to infer the botanical name from embedded hyperlinks."""
    for url in links:
        parsed = urlparse(url)
        slug = unquote(parsed.path.rsplit("/", 1)[-1])
        words = [w for w in re.split(r"[-_]", slug) if w]
        cand = " ".join(words[:3])
        if BOT_ANY_RE.match(cand.title()):
            parts = cand.split()
            return parts[0].capitalize() + (
                " " + " ".join(parts[1:]) if len(parts) > 1 else ""
            )
    return ""


# --- Link & Type Mapping -------------------------------------------------
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
    last_type = ""
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").upper()
            match = next((v for k, v in valid_types.items() if k in text), "")
            if match:
                last_type = match
            page_type_map[idx] = last_type
    return page_type_map


# --- Row & Image Extraction ----------------------------------------------
def extract_rows() -> List[Dict[str, str]]:
    rows = []
    used_keys = set(master_df.get("Key", []))
    page_type_map = build_page_type_map(PDF_PATH)
    skip_pages = {p for p, t in page_type_map.items() if not t}
    link_map = extract_links_by_page(PDF_PATH)

    with pdfplumber.open(PDF_PATH) as pdf:
        for idx, pg in enumerate(tqdm(pdf.pages, desc="Scanning PDF")):
            page_num = idx + 1
            if page_num in skip_pages:
                continue
            text = pg.extract_text() or ""
            if re.search(r"table of contents", text, re.I):
                continue
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if sum("..." in ln for ln in lines) >= 3:
                continue
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
                bot_name = guess_botanical_from_links(link_map.get(page_num, []))
                if bot_name:
                    lines.insert(0, bot_name)
                    com_name = guess_common(lines, 0)
                else:
                    continue

            body = "\n".join(lines)
            height = (
                f"{m.group(1)} - {m.group(2)}"
                if (m := HEIGHT_RE.search(body)) and m.group(2)
                else (m.group(1) if m else "")
            )
            spread = (
                f"{m.group(1)} - {m.group(2)}"
                if (m := SPREAD_RE.search(body)) and m.group(2)
                else (m.group(1) if m else "")
            )
            links = link_map.get(page_num, [])
            if len(bot_name.split()) == 2:
                guessed = guess_botanical_from_links(links)
                if guessed.lower().startswith(bot_name.lower()):
                    bot_name = guessed
            mbg = next((l for l in links if "missouribotanicalgarden" in l.lower()), "")
            wf = next((l for l in links if "wildflower.org" in l.lower()), "")
            pr = next((l for l in links if "pleasantrunnursery.com" in l.lower()), "")
            nm = next((l for l in links if "newmoonnursery.com" in l.lower()), "")
            pn = next((l for l in links if "pinelandsnursery.com" in l.lower()), "")

            if bot_name in master_idx.index:
                row_data = master_idx.loc[bot_name].to_dict()
                used_keys.add(row_data.get("Key", ""))
            else:
                row_data = {c: "" for c in template_cols}
                row_data["Key"] = gen_key(bot_name, used_keys)
            row_data.update(
                {
                    "Page in PDF": str(page_num),
                    "Plant Type": page_type_map.get(page_num, ""),
                    "Botanical Name": bot_name,
                    "Common Name": com_name,
                    "Height (ft)": height,
                    "Spread (ft)": spread,
                    "Link: Missouri Botanical Garden": mbg,
                    "Link: Wildflower.org": wf,
                    "Link: Pleasantrunnursery.com": pr,
                    "Link: Newmoonnursery.com": nm,
                    "Link: Pinelandsnursery.com": pn,
                }
            )
            rows.append(row_data)
    return rows


def extract_images(df: pd.DataFrame) -> None:
    doc = fitz.open(PDF_PATH)
    image_rows = []
    page_to_name = {
        int(r["Page in PDF"]): (r["Botanical Name"], r.get("Common Name", ""))
        for _, r in df.iterrows()
        if r.get("Page in PDF", "").isdigit()
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
            image_rows.append(
                {
                    "Image Filename": filename,
                    "Page Number": page_index,
                    "Botanical Name": bot_name,
                    "Common Name": com_name,
                }
            )
    pd.DataFrame(image_rows).to_csv(MAP_CSV, index=False, na_rep="")
    safe_print(f"[IMG] Extracted {len(image_rows)} images to {IMG_DIR}")
    safe_print(f"[MAP]  Mapping written to {MAP_CSV}")

    jpeg_dir = IMG_DIR / "jpeg"
    jpeg_dir.mkdir(exist_ok=True)
    converted = 0
    for png_file in IMG_DIR.glob("*.png"):
        img = Image.open(png_file).convert("RGB")
        jpg_file = jpeg_dir / (png_file.stem + ".jpg")
        img.save(jpg_file, "JPEG", quality=85)
        converted += 1
    safe_print(f"[IMG] Converted {converted} PNG images to JPEGs in {jpeg_dir}")


# --- Main ----------------------------------------------------------------
def main():
    df = pd.DataFrame(extract_rows(), columns=COLUMNS)
    extract_images(df)
    df.drop(columns=["Page in PDF"], inplace=True, errors="ignore")
    df.to_csv(OUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL, na_rep="")
    safe_print(f"[OK] Saved -> {OUT_CSV.name} ({len(df)} rows)")


if __name__ == "__main__":
    main()
