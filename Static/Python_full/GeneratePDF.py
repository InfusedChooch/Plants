#!/usr/bin/env python3
# GeneratePDF.py - Produce a printable plant-guide PDF (2025-06-05, portable paths)
# Auto-detect link tags from the CSV and populate the legend.

"""
Generate a title page, TOC and a page per plant with images using fpdf2.
"""

from pathlib import Path
import sys, argparse, logging, re
from datetime import datetime
from PIL import Image
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.errors import FPDFException
import yaml


# --- CLI ------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Generate plant guide PDF")
parser.add_argument(
    "--in_csv",
    default="Outputs/Plants_Linked_Filled.csv",  # <- moved
    help="Input CSV file with filled data",
)
parser.add_argument(
    "--out_pdf",
    default="Outputs/Plant_Guide_EXPORT.pdf",  # <- moved
    help="Output PDF file",
)
parser.add_argument(
    "--img_dir",
    default="Outputs/Images/Plants",  # <- moved
    help="Folder that holds plant JPEGs",
)
parser.add_argument(
    "--logo_dir",
    default="Outputs/Images",
    help="Folder that holds Rutgers and NJAES logos",
)

parser.add_argument(
    "--template_csv",
    default="Templates/20250612_Masterlist_Master.csv",
    help="CSV file containing column template (must include 'Link: Others')",
)
args = parser.parse_args()


# --- Path helpers ---------------------------------------------------------
def repo_dir() -> Path:
    """
    Return the root of the project folder.
    Supports:
    - frozen .exe inside `_internal/helpers`
    - or running from source
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        # If we're in .../_internal/helpers/, go up 2
        if (
            exe_dir.name.lower() == "helpers"
            and exe_dir.parent.name.lower() == "_internal"
        ):
            return exe_dir.parent.parent
        return exe_dir.parent  # fallback: go up 1
    # for source .py files
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Templates").is_dir() and (parent / "Outputs").is_dir():
            return parent
    return here.parent.parent


REPO = repo_dir()
CSV_FILE = (REPO / args.in_csv).resolve()
IMG_DIR = (REPO / args.img_dir).resolve()
OUTPUT = (REPO / args.out_pdf).resolve()
TEMPLATE_CSV = (REPO / args.template_csv).resolve()
LOGO_DIR = (REPO / args.logo_dir).resolve()

# auto-create Outputs on first run from a clean flash-drive
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# --- Load and Prepare Data ------------------------------------------------
df = (
    pd.read_csv(CSV_FILE, dtype=str, keep_default_na=False)
    .fillna("")
    .replace("Needs Review", "")
)  # Read CSV, empty cells -> ""
template_cols = list(pd.read_csv(TEMPLATE_CSV, nrows=0, keep_default_na=False).columns)
df = df.reindex(
    columns=template_cols + [c for c in df.columns if c not in template_cols]
)
df["Plant Type"] = df["Plant Type"].str.upper()  # Normalize plant types to uppercase
if "Page in PDF" in df.columns:
    df["Page in PDF"] = pd.to_numeric(
        df["Page in PDF"], errors="coerce"
    )  # Ensure page numbers are numeric

PLANT_TYPE_ORDER = [  # Desired order of sections
    "HERBACEOUS, PERENNIAL",
    "FERNS",
    "GRASSES, SEDGES, AND RUSHES",
    "SHRUBS",
    "TREES",
]

# Mapping of link columns to short footer labels
# ("Link: Others" is handled separately to allow custom tags per entry)
LINK_LABELS = [
    ("Link: Missouri Botanical Garden", "MBG"),
    ("Link: Wildflower.org", "WF"),
    ("Link: Pleasantrunnursery.com", "PRN"),
    ("Link: Newmoonnursery.com", "NMN"),
    ("Link: Pinelandsnursery.com", "PNL"),
]

# Mapping of link abbreviations to their full names for the legend
LINK_LEGEND = {
    "MBG": "Missouri Botanical Garden",
    "WF": "Wildflower",
    "PRN": "Pleasant Run Nursery",
    "NMN": "New Moon Nursery",
    "PNL": "Pinelands Nursery",
    "OTH": "Other Sources",
}

# Colors assigned to each link abbreviation for legend and footers
LINK_COLORS = {
    "MBG": (0, 70, 120),
    "WF": (200, 0, 0),
    "PRN": (128, 0, 128),
    "NMN": (255, 140, 0),
    "PNL": (34, 139, 34),
    "OTH": (0, 0, 200),
}

# --- Discover extra link tags from the data -----------------------------



# --- Helpers --------------------------------------------------------------
def safe_text(text: str) -> str:
    """Clean text: remove null chars, collapse newlines, strip non-printable."""
    text = str(text).replace("\x00", "").replace("\r", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[^\x20-\x7E]+", "", text)
    text = text.strip()
    return apply_style(text)


# --- Style-sheet enforcement ---------------------------------------------
STYLE_FILE = REPO / "Templates" / "style_rules.yaml"
_style_rules = []

if STYLE_FILE.exists():
    with open(STYLE_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        subs = data.get("substitutions", data)

    for pattern, repl in subs.items():
        pat = re.compile(pattern)
        if repl == "<<lower>>":
            _style_rules.append((pat, lambda m: m.group(0).lower()))
        else:
            _style_rules.append((pat, repl))
else:
    logging.warning("Style file not found: %s (continuing without it)", STYLE_FILE)


def apply_style(text: str) -> str:
    """Run the loaded style-sheet rules over a piece of text."""
    for pat, repl in _style_rules:
        text = pat.sub(repl, text)
    return text


def primary_common_name(name):
    """Return first common name if multiple (split on '/' or ' or ')."""
    if "/" in name:
        return name.split("/")[0].strip()
    elif " or " in name:
        return name.split(" or ")[0].strip()
    return name


def truncate_text(text: str, max_len: int, plant_name: str, field: str) -> str:
    """Truncate overly long sections to keep each plant on a single page."""
    if len(text) > max_len:
        logging.warning("Truncating %s for %s", field, plant_name)
        return text[: max_len - 3] + "..."
    return text


def name_slug(text: str) -> str:
    """Convert name to filesystem-safe lowercase slug (letters/numbers -> underscore)."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


# Parse "Link: Others" cell -> list of (tag, url, label)
OTHER_LINK_PATTERN = re.compile(r"\[(?P<tag>[^,\]]+),\"(?P<url>[^\"]+)\",\"(?P<label>[^\"]+)\"\]")

def parse_other_links(text: str) -> list[tuple[str, str, str]]:
    """Return (tag, url, label) tuples from the Link: Others column."""
    return OTHER_LINK_PATTERN.findall(text or "")


# Scan dataframe for additional tags and extend legend/color maps
if "Link: Others" in df.columns:
    for cell in df["Link: Others"]:
        for tag, url, label in parse_other_links(cell):
            LINK_LEGEND.setdefault(tag, label)
            LINK_COLORS.setdefault(tag, LINK_COLORS.get("OTH", (0, 0, 200)))

def flush_columns(pdf, legend_items, col_count=3):
    """Render legend entries in equal-width columns."""
    max_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = max_w / col_count
    row_height = 6

    rows = (len(legend_items) + col_count - 1) // col_count
    table = [[] for _ in range(rows)]
    for idx, (abbr, label) in enumerate(legend_items):
        table[idx % rows].append((abbr, label))

    for row in table:
        pdf.set_x(pdf.l_margin)
        for abbr, label in row:
            color = LINK_COLORS.get(abbr, (0, 0, 200))
            pdf.set_text_color(*color)
            pdf.cell(18, row_height, f"[{abbr}]", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_width - 18, row_height, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(row_height)

def draw_wrapped_legend(pdf) -> None:
    """Draw the link legend with [OTH] as a group header and all items in columns."""
    standard_items = []
    other_items = []

    STANDARD_TAGS = {"MBG", "WF", "PRN", "NMN", "PNL"}

    for abbr, label in LINK_LEGEND.items():
        if abbr in STANDARD_TAGS:
            standard_items.append((abbr, label))
        elif abbr != "OTH":
            other_items.append((abbr, label))

    # ── Standard Legend Entries ──
    pdf.set_font("Times", "", 11)
    flush_columns(pdf, sorted(standard_items, key=lambda x: x[0]), col_count=3)

    # ── Other Sources ──
    if other_items:
        other_items = sorted(set(other_items), key=lambda x: x[0])  # alphabetically
        pdf.set_text_color(*LINK_COLORS.get("OTH", (0, 0, 200)))
        pdf.set_font("Times", "B", 11)
        pdf.cell(0, 8, "Other Links", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Times", "", 11)
        pdf.set_text_color(0, 0, 0)
        flush_columns(pdf, other_items, col_count=3)

    # Reset formatting
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Times", "", 12)




def draw_labeled_parts(pdf, parts, sep=" | ") -> None:
    """Write (label, value) tuples with wrapping and optional colored segments."""
    max_w = pdf.w - pdf.l_margin - pdf.r_margin
    line_parts = []
    line_width = 0

    def to_segments(val):
        if isinstance(val, list):
            segs = []
            for seg in val:
                if isinstance(seg, tuple):
                    segs.append(seg)
                else:
                    segs.append((str(seg), None))
            return segs
        return [(str(val), None)]

    def flush_line():
        nonlocal line_parts, line_width
        if not line_parts:
            return
        pdf.set_x(pdf.l_margin)
        for i, (label, segs) in enumerate(line_parts):
            pdf.set_font("Times", "B", 12)
            pdf.write(6, f"{label} ")
            pdf.set_font("Times", "", 12)
            for text, color in segs:
                if color:
                    pdf.set_text_color(*color)
                else:
                    pdf.set_text_color(0, 0, 0)
                pdf.write(6, text)
            pdf.set_text_color(0, 0, 0)
            if i < len(line_parts) - 1:
                pdf.write(6, sep)
        pdf.ln(6)
        line_parts = []
        line_width = 0

    for label, value in parts:
        segs = to_segments(value)
        seg_width = pdf.get_string_width(f"{label} ") + sum(
            pdf.get_string_width(text) for text, _ in segs
        )
        sep_w = pdf.get_string_width(sep) if line_parts else 0
        if line_width + sep_w + seg_width > max_w:
            flush_line()
        if line_parts:
            line_width += pdf.get_string_width(sep)
        line_parts.append((label, segs))
        line_width += seg_width

    flush_line()


# --- PDF Class ------------------------------------------------------------
class PlantPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")  # Use US Letter size
        self.current_plant_type = ""  # Track current section for footer
        self.section_links = []  # Store links to section dividers
        self.toc = {ptype: [] for ptype in PLANT_TYPE_ORDER}  # TOC entries per section
        self.set_auto_page_break(auto=True, margin=20)  # Auto page breaks with margin
        self.skip_footer = False  # Flag to disable footer temporarily
        self.footer_links = []  # list of (label, url) for footer

    def footer(self):
        if self.skip_footer:
            return

        self.set_y(-12)
        self.set_font("Times", "I", 9)

        links = self.footer_links
        page_str = str(self.page_no() - getattr(self, "_ghost_pages", 0))
        self.set_y(-12)

        # LEFT: source links
        self.set_x(self.l_margin)
        for i, (label, url) in enumerate(links):
            text = f"[{label}]"
            color = LINK_COLORS.get(label, (0, 0, 200))
            self.set_text_color(*color)
            self.cell(self.get_string_width(text) + 2, 6, text, link=url)
            if i < len(links) - 1:
                self.set_text_color(0, 0, 0)
                self.cell(4, 6, "")
        self.set_text_color(0, 0, 0)

        # CENTER: Plant type
        if self.current_plant_type:
            self.set_text_color(90, 90, 90)
            center_x = (
                self.w / 2 - self.get_string_width(self.current_plant_type.title()) / 2
            )
            self.set_xy(center_x, -8.)  # or try -10, -10.25
            self.cell(
                self.get_string_width(self.current_plant_type.title()) + 2,
                6,
                self.current_plant_type.title(),
            )

        # RIGHT: Page number
        self.set_text_color(128, 128, 128)
        self.set_xy(self.w - self.r_margin - self.get_string_width(page_str), -12)
        self.cell(0, 6, page_str)

    def add_type_divider(self, plant_type):
        # DO NOT clear or disable footer until after rendering previous page's footer
        self.add_page()  # this triggers footer for the previous page

        self.footer_links = []      # Clear for divider page only
        self.skip_footer = True     # Disable just for the divider page

        link = self.add_link()
        self.set_link(link)
        self.section_links.append((plant_type, link))

        self.set_font("Times", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)
        self.cell(0, 20, plant_type.title(), align="C")
        self.set_text_color(0, 0, 0)

        self.skip_footer = False  # Re-enable footer for following content


    def add_table_of_contents(self):
        """Generate the TOC pages, listing each plant with page links."""
        self.footer_links = []
        self.skip_footer = False
        self.current_plant_type = "Table of Contents"
        self.set_y(20)
        self.set_font("Times", "B", 16)
        self.cell(0, 12, "Table of Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Times", "", 12)
        self.ln(4)
        for ptype in PLANT_TYPE_ORDER:
            entries = self.toc.get(ptype, [])
            if entries:
                # Section header
                self.set_font("Times", "B", 13)
                self.set_text_color(0, 0, 128)
                self.cell(0, 8, ptype.title(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_font("Times", "", 11)
                self.set_text_color(0, 0, 0)
            for name, page, link, links in entries:
                self.set_x(self.l_margin)
                # Plant name (clickable)
                self.cell(self.get_string_width(name) + 2, 6, name, link=link)
                for label, url in links:
                    color = LINK_COLORS.get(label, (0, 0, 200))
                    self.set_text_color(*color)
                    abbrev = f" [{label}]"
                    self.cell(self.get_string_width(abbrev) + 1, 6, abbrev, link=url)
                self.set_text_color(0, 0, 0)
                # Dots and right-aligned page number
                dot_x = self.get_x()
                page_str = str(page)
                dot_width = self.get_string_width(page_str) + 2
                dots = "." * int(
                    (self.w - self.r_margin - dot_x - dot_width)
                    / self.get_string_width(".")
                )
                self.cell(self.get_string_width(dots), 6, dots, align="L")
                self.cell(
                    dot_width,
                    6,
                    page_str,
                    align="R",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )

    def add_plant(self, row, plant_type):
        """Add a single plant page using Layoutmk1 structure."""
        bot_name = safe_text(row.get("Botanical Name", ""))
        base_name = name_slug(bot_name)
        links = []

        for col, label in LINK_LABELS:
            url = row.get(col, "").strip()
            if url:
                links.append((label, url))

        for tag, url, label_name in parse_other_links(row.get("Link: Others", "")):
            links.append((tag, url))
            LINK_LEGEND.setdefault(tag, label_name)
            LINK_COLORS.setdefault(tag, LINK_COLORS.get("OTH", (0, 0, 200)))

        self.current_plant_type = plant_type
        link = self.add_link()
        max_len = 240

        while True:
            self.set_auto_page_break(auto=False)
            self.add_page()
            page_start = self.page_no()
            self.footer_links = links
            self.set_link(link)

            # --- Header: Botanical and Common Name ---
            self.set_font("Times", "I", 18)
            self.set_text_color(22, 92, 34)
            self.multi_cell(0, 8, bot_name, align="C")

            common = primary_common_name(safe_text(row.get("Common Name", ""))).strip()
            if common:
                self.set_font("Times", "B", 13)
                self.set_text_color(0, 0, 0)
                try:
                    self.multi_cell(0, 8, common, align="C")
                except FPDFException:
                    self.set_x((self.w - self.get_string_width(common)) / 2)
                    self.cell(self.get_string_width(common) + 1, 8, common)

            self.ln(2)

            # --- Images ---
            images = sorted(list(IMG_DIR.glob(f"{base_name}_*.jpg")) +
                            list(IMG_DIR.glob(f"{base_name}_*.png")))
            count = max(1, min(len(images), 3))
            margin = self.l_margin
            avail_w = self.w - margin - self.r_margin
            gap = 5
            img_w = (avail_w - (count - 1) * gap) / count
            img_h_fixed = 100
            y0 = self.get_y()

            for i in range(count):
                x_pos = margin + i * (img_w + gap)
                if i < len(images):
                    img_path = str(images[i])
                    with Image.open(img_path) as im:
                        aspect = im.height / im.width
                    scaled_h = min(img_w * aspect, img_h_fixed)
                    scaled_w = scaled_h / aspect
                    x_img = x_pos + (img_w - scaled_w) / 2
                    y_img = y0 + (img_h_fixed - scaled_h) / 2
                    self.image(img_path, x=x_img, y=y_img, w=scaled_w, h=scaled_h)
                else:
                    self.rect(x_pos, y0, img_w, img_h_fixed)

            self.set_y(y0 + img_h_fixed + 6)

            # --- Characteristics ---
            self.set_font("Times", "B", 13)
            self.cell(0, 8, "Characteristics:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_font("Times", "", 12)
            char_parts = []

            color_text = safe_text(row.get("Bloom Color", ""))
            if color_text:
                segments = []
                for i, color in enumerate([c.strip() for c in color_text.split(",")]):
                    rgb = {
                        "red": (200, 0, 0), "pink": (255, 105, 180),
                        "purple": (128, 0, 128), "blue": (0, 0, 200),
                        "yellow": (200, 180, 0), "orange": (255, 140, 0),
                        "green": (34, 139, 34), "indigo": (75, 0, 130),
                        "violet": (148, 0, 211), "brown": (139, 69, 19),
                    }.get(color.lower(), (0, 0, 0)) if color.lower() != "white" else (0, 0, 0)
                    segments.append((color, rgb))
                    if i < len(color_text.split(",")) - 1:
                        segments.append((", ", None))
                char_parts.append(("Bloom Color:", segments))
            if (h := safe_text(row.get("Height (ft)", ""))):
                char_parts.append(("Height:", f"{h} ft"))
            if (s := safe_text(row.get("Spread (ft)", ""))):
                char_parts.append(("Spread:", f"{s} ft"))
            if (b := safe_text(row.get("Bloom Time", ""))):
                char_parts.append(("Bloom Time:", b))
            self.ln(1)
            
            if (sun := safe_text(row.get("Sun", ""))):
                char_parts.append(("Sun:", sun))
            if (water := safe_text(row.get("Water", ""))):
                char_parts.append(("Water:", water))
            if (agcp := safe_text(row.get("AGCP Regional Status", ""))):
                char_parts.append(("AGCP Status:", agcp))
            zone_raw = safe_text(row.get("USDA Hardiness Zone", "") or row.get("Zone", ""))
            zone_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", zone_raw)
            zone = f"{zone_match.group(1)} - {zone_match.group(2)}" if zone_match else zone_raw
            if zone:
                char_parts.append(("USDA Hardiness Zone:", zone))
            draw_labeled_parts(self, char_parts)
            self.ln(1)

            # --- Attracts + Tolerates inline ---
            attracts = truncate_text(safe_text(row.get("Attracts", "")), max_len, bot_name, "Attracts")
            tolerates = truncate_text(safe_text(row.get("Tolerates", "")), max_len, bot_name, "Tolerates")
            if attracts or tolerates:
                self.set_font("Times", "B", 12)
                self.write(6, "Attracts: ")
                self.set_font("Times", "", 12)
                self.write(6, attracts or "—")
                if tolerates:
                    self.set_font("Times", "B", 12)
                    self.write(6, "  |  Tolerates: ")
                    self.set_font("Times", "", 12)
                    self.write(6, tolerates)
                self.ln(6)

            # --- Soil / Habitat ---
            for label, key in [("Soil Description", "Soil Description"),
                            ("Native Habitats", "Native Habitats")]:
                val = truncate_text(safe_text(row.get(key, "") or row.get("Habitats", "")), max_len, bot_name, key)
                if val:
                    self.set_font("Times", "B", 12)
                    self.write(6, f"{label}: ")
                    self.set_font("Times", "", 12)
                    self.multi_cell(0, 6, val)
            self.ln(1)

            # --- Recommended Uses ---
            self.set_font("Times", "B", 13)
            self.cell(0, 8, "Recommended Uses:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_font("Times", "", 12)

            usexyz = safe_text(row.get("UseXYZ", ""))
            if usexyz:
                tags = [t.strip() for t in usexyz.split("|") if t.strip()]
                self.set_font("Times", "", 12)
                for i, tag in enumerate(tags):
                    self.write(6, f"{tag}")
                    if i < len(tags) - 1:
                        self.write(6, "  |  ")
                self.ln(6)



            uses = truncate_text(safe_text(row.get("Uses", "")), max_len, bot_name, "Uses")
            if uses:
                self.set_font("Times", "B", 12)
                self.write(6, "General Uses: ")
                self.set_font("Times", "", 12)
                self.multi_cell(0, 6, uses)

            culture = truncate_text(safe_text(row.get("Culture", "")), max_len, bot_name, "Culture")
            if culture:
                self.set_font("Times", "B", 12)
                self.write(6, "Culture: ")
                self.set_font("Times", "", 12)
                self.multi_cell(0, 6, culture)

            note = row.get("Extra Notes", "")
            if note:
                note = truncate_text(safe_text(note), max_len, bot_name, "Extra Notes")
                self.set_font("Times", "", 12)
                self.multi_cell(0, 6, note)

            # --- General Maintenance Level ---
            level = safe_text(row.get("MaintenanceLevel", "")).capitalize()
            color = {"Low": (34, 139, 34), "Medium": (255, 140, 0), "High": (200, 0, 0)}.get(level, (90, 90, 90))

            self.set_font("Times", "B", 13)
            self.write(6, "General Maintenance Level")
            self.set_text_color(*color)
            self.write(6, f" - {level}\n")
            self.set_text_color(0, 0, 0)

            for key in ["WFMaintenance", "Problems", "Condition Comments"]:
                val = truncate_text(safe_text(row.get("WFMaintenance", "")), max_len, bot_name, "WFMaintenance")
                if val:
                    self.set_font("Times", "B", 12)
                    self.write(6, "Maintenance: ")
                    self.set_font("Times", "", 12)
                    self.multi_cell(0, 6, val)

                for key in ["Problems", "Condition Comments"]:
                    val = truncate_text(safe_text(row.get(key, "")), max_len, bot_name, key)
                    if val:
                        self.set_font("Times", "B", 12)
                        self.write(6, f"{key.replace('_', ' ')}: ")
                        self.set_font("Times", "", 12)
                        self.multi_cell(0, 6, val)

                    self.ln(1)


            end_page = self.page_no()
            pages_used = end_page - page_start + 1
            self.set_auto_page_break(auto=True, margin=20)

            if pages_used > 1:
                logging.warning("Truncating %s to fit on a single page", bot_name)
                for _ in range(pages_used):
                    if self.page in self.pages:
                        del self.pages[self.page]
                        self.page -= 1
                max_len = max(80, max_len - 80)
                continue

            display_page = self.page_no() - getattr(self, "_ghost_pages", 0)
            self.toc[plant_type].append((bot_name, display_page, link, links))
            break


# --- Build PDF ------------------------------------------------------------
pdf = PlantPDF()  # Instantiate PDF generator
pdf._ghost_pages = 0  # Title page unnumbered

# --- Title Page ----------------------------------------------------------
from pathlib import Path
import os

pdf.skip_footer = True
pdf.add_page()


# ------------------------------------------------------------------------
# 1.  Robust path lookup ─ tolerate .png/.jpg/.jpeg and missing extension
# ------------------------------------------------------------------------
def find_logo(base_dir: Path, basenames: list[str]) -> Path | None:
    exts = ("", ".png", ".jpg", ".jpeg")
    for stem in basenames:
        for ext in exts:
            p = base_dir / (stem if stem.lower().endswith(ext) else f"{stem}{ext}")
            if p.exists():
                return p
    return None


left_logo = find_logo(LOGO_DIR, ["Rutgers_Logo"])  # <-- “R” + text
right_logo = find_logo(LOGO_DIR, ["NJAES_Logo"])  # <-- green swoosh


# ------------------------------------------------------------------------
# 2.  Helper to draw both logos next to each other, centred on the page
# ------------------------------------------------------------------------
def draw_logos(
    pdf: FPDF, left: Path, right: Path, *, y: float = 16, h: float = 24, gap: float = 4
) -> None:
    """Place *left* and *right* logos on one line, centred horizontally."""
    if not (left and right):
        return  # quietly skip if either file is missing

    from PIL import Image  # local import to avoid shipping PIL if not needed

    # scaled widths that keep original aspect ratios
    with Image.open(left) as im:
        w_left = h * im.width / im.height
    with Image.open(right) as im:
        w_right = h * im.width / im.height

    total_w = w_left + gap + w_right
    x0 = (pdf.w - total_w) / 2  # centre the pair on the page width

    pdf.image(str(left), x=x0, y=y, h=h)
    pdf.image(str(right), x=x0 + w_left + gap, y=y, h=h)


# ------------------------------------------------------------------------
# 3.  Draw the banner (remove the old individual image() calls)
# ------------------------------------------------------------------------
draw_logos(pdf, left_logo, right_logo)


pdf.set_y(70)
pdf.set_font("Times", "B", 22)
pdf.set_text_color(0, 70, 120)
pdf.cell(0, 12, "PLANT FACT SHEETS", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Times", "", 16)
pdf.ln(4)
pdf.cell(
    0,
    10,
    "for Rain Gardens / Bioretention Systems",
    align="C",
    new_x=XPos.LMARGIN,
    new_y=YPos.NEXT,
)
pdf.ln(10)
pdf.set_font("Times", "", 14)
pdf.cell(
    0,
    10,
    "Rutgers Cooperative Extension",
    align="C",
    new_x=XPos.LMARGIN,
    new_y=YPos.NEXT,
)
pdf.cell(
    0, 10, "Water Resources Program", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
)
pdf.ln(10)
pdf.set_font("Times", "I", 12)
pdf.cell(
    0, 10, f"{datetime.today():%B %Y}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
)
pdf.set_text_color(0, 0, 0)
pdf.ln(4)
pdf.set_font("Times", "", 10)
draw_wrapped_legend(pdf)
pdf.set_font("Times", "", 12)

# --- Reserve TOC pages (2-4) ---------------------------------------------
pdf.skip_footer = False
pdf.add_page()
pdf.add_page()
pdf.add_page()

# --- Add plant sections and pages ----------------------------------------
for plant_type in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == plant_type]  # Filter by type
    if not group.empty:
        pdf.add_type_divider(plant_type)
        for _, row in group.iterrows():
            if row.get("Botanical Name", "").strip():
                pdf.add_plant(row, plant_type)

# --- Insert TOC content --------------------------------------------------
pdf.page = 2
pdf.add_table_of_contents()

# --- Save PDF -----------------------------------------------------------
pdf.output(str(OUTPUT))
print(f"[OK] Exported with TOC on pages 1-3 -> {OUTPUT}")
