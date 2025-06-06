#!/usr/bin/env python3
# GeneratePDF.py – Produce a printable plant-guide PDF (2025-06-05, portable paths)

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


# ─── CLI ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Generate plant guide PDF")
parser.add_argument(
    "--in_csv",
    default="Outputs/Plants_Linked_Filled.csv",           # ← moved
    help="Input CSV file with filled data",
)
parser.add_argument(
    "--out_pdf",
    default="Outputs/Plant_Guide_EXPORT.pdf",             # ← moved
    help="Output PDF file",
)
parser.add_argument(
    "--img_dir",
    default="Outputs/pdf_images/jpeg",                    # ← moved
    help="Folder that holds plant JPEGs",
)
parser.add_argument(
    "--template_csv",
    default="Templates/Plants_Linked_Filled_Master.csv",  # ← moved
    help="CSV file containing column template",
)
args = parser.parse_args()


# ─── Path helpers ─────────────────────────────────────────────────────────
def repo_dir() -> Path:
    """Return bundle root when frozen, or repo root when running from source."""
    if getattr(sys, "frozen", False):          # PyInstaller helper EXE
        return Path(sys.executable).resolve().parent
    # source layout: Static/Python/GeneratePDF.py → ../../ (repo root)
    return Path(__file__).resolve().parent.parent.parent


REPO = repo_dir()
CSV_FILE      = (REPO / args.in_csv).resolve()
IMG_DIR       = (REPO / args.img_dir).resolve()
OUTPUT        = (REPO / args.out_pdf).resolve()
TEMPLATE_CSV  = (REPO / args.template_csv).resolve()

# auto-create Outputs on first run from a clean flash-drive
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ─── Load and Prepare Data ────────────────────────────────────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")  # Read CSV, empty cells → ""
template_cols = list(pd.read_csv(TEMPLATE_CSV, nrows=0).columns)
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
    "WF": "Wildflower.org",
    "PRN": "Pleasantrunnursery.com",
    "NMN": "Newmoonnursery.com",
    "PNL": "Pinelandsnursery.com",
}

# Colors assigned to each link abbreviation for legend and footers
LINK_COLORS = {
    "MBG": (0, 70, 120),
    "WF": (200, 0, 0),
    "PRN": (128, 0, 128),
    "NMN": (255, 140, 0),
    "PNL": (34, 139, 34),
}


# ─── Helpers ──────────────────────────────────────────────────────────────
def safe_text(text: str) -> str:
    """Clean text: remove null chars, collapse newlines, strip non-printable."""
    text = str(text).replace("\x00", "").replace("\r", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[^\x20-\x7E]+", "", text)
    return text.strip()


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
    """Convert name to filesystem‐safe lowercase slug (letters/numbers → underscore)."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def draw_wrapped_legend(pdf) -> None:
    """Draw the link legend centered and wrapped by available width."""
    parts = list(LINK_LEGEND.items())
    max_w = pdf.w - pdf.l_margin - pdf.r_margin
    line_parts = []
    line_width = 0

    def flush_line():
        nonlocal line_parts, line_width
        if not line_parts:
            return
        total_w = 0
        for i, (text, color) in enumerate(line_parts):
            total_w += pdf.get_string_width(text)
            if i < len(line_parts) - 1:
                total_w += pdf.get_string_width(" | ")
        start_x = pdf.l_margin + (max_w - total_w) / 2
        pdf.set_x(start_x)
        for i, (text, color) in enumerate(line_parts):
            pdf.set_text_color(*color)
            pdf.write(6, text)
            if i < len(line_parts) - 1:
                pdf.set_text_color(0, 0, 0)
                pdf.write(6, " | ")
        pdf.ln(6)
        line_parts = []
        line_width = 0

    for idx, (abbr, name) in enumerate(parts):
        seg_text = f"[{abbr}] {name}"
        seg_width = pdf.get_string_width(seg_text)
        sep_width = pdf.get_string_width(" | ") if line_parts else 0
        if line_width + seg_width + sep_width > max_w:
            flush_line()
        if line_parts:
            line_width += pdf.get_string_width(" | ")
        line_parts.append((seg_text, LINK_COLORS.get(abbr, (0, 0, 200))))
        line_width += seg_width

    flush_line()
    pdf.set_text_color(0, 0, 0)


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
            pdf.set_font("Helvetica", "B", 12)
            pdf.write(6, f"{label} ")
            pdf.set_font("Helvetica", "", 12)
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


# ─── PDF Class ────────────────────────────────────────────────────────────
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
        self.set_font("Helvetica", "I", 9)

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
            self.set_xy(center_x, -12)
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
        """Insert a full-page section divider with title and link anchor."""
        self.footer_links = []  # No links on divider page
        self.skip_footer = True  # Temporarily hide footer
        self.add_page()  # New page
        self.skip_footer = False  # Re-enable footer for subsequent pages
        link = self.add_link()  # Add internal link target
        self.set_link(link)
        self.section_links.append((plant_type, link))
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)  # Vertical spacing
        self.cell(0, 20, plant_type.title(), align="C")
        self.set_text_color(0, 0, 0)

    def add_table_of_contents(self):
        """Generate the TOC pages, listing each plant with page links."""
        self.footer_links = []
        self.skip_footer = False
        self.current_plant_type = "Table of Contents"
        self.set_y(20)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 12, "Table of Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 12)
        self.ln(4)
        for ptype in PLANT_TYPE_ORDER:
            entries = self.toc.get(ptype, [])
            if entries:
                # Section header
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(0, 0, 128)
                self.cell(0, 8, ptype.title(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_font("Helvetica", "", 11)
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
        """Add a single plant page. Regenerate with shorter text if needed."""
        bot_name = safe_text(row.get("Botanical Name", ""))
        base_name = name_slug(bot_name)
        links = []
        for col, label in LINK_LABELS:
            url = row.get(col, "").strip()
            if url:
                links.append((label, url))

        self.current_plant_type = plant_type
        link = self.add_link()
        max_len = 300

        while True:
            self.set_auto_page_break(auto=False)
            self.add_page()
            page_start = self.page_no()
            self.footer_links = links
            self.set_link(link)

            # Botanical name
            self.set_font("Helvetica", "I", 18)
            self.set_text_color(22, 92, 34)
            self.multi_cell(0, 8, bot_name, align="C")

            # Common name, if present
            common = primary_common_name(safe_text(row.get("Common Name", ""))).strip()
            if common:
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(0, 0, 0)
                try:
                    self.multi_cell(0, 8, common, align="C")
                except FPDFException:
                    self.set_x((self.w - self.get_string_width(common)) / 2)
                    self.cell(self.get_string_width(common) + 1, 8, common)
            self.ln(2)

            # ── Images ──
            images = sorted(
                list(IMG_DIR.glob(f"{base_name}_*.jpg"))
                + list(IMG_DIR.glob(f"{base_name}_*.png"))
            )  # Find up to 3 images
            count = max(1, min(len(images), 3))
            margin = self.l_margin
            avail_w = self.w - margin - self.r_margin
            gap = 5
            img_w = (avail_w - (count - 1) * gap) / count
            img_h_fixed = 100
            x = margin
            y0 = 40
            self.set_y(y0)
            for i in range(count):
                if i < len(images):
                    img_path = str(images[i])
                    with Image.open(img_path) as im:
                        aspect = im.height / im.width
                    scaled_h = min(img_w * aspect, img_h_fixed)
                    scaled_w = scaled_h / aspect
                    x_img = x + (img_w - scaled_w) / 2
                    y_img = y0 + (img_h_fixed - scaled_h) / 2
                    self.image(img_path, x=x_img, y=y_img, w=scaled_w, h=scaled_h)
                else:
                    self.rect(x, y0, img_w, img_h_fixed)  # Empty box if no image
                x += img_w + gap
            self.set_y(y0 + img_h_fixed + 6)

            # ── Characteristics section ──
            tolerates = truncate_text(
                safe_text(row.get("Tolerates", "")), max_len, bot_name, "Tolerates"
            )
            maintenance = truncate_text(
                safe_text(row.get("Maintenance", "")), max_len, bot_name, "Maintenance"
            )
            agcp = truncate_text(
                safe_text(row.get("AGCP Regional Status", "")),
                max_len,
                bot_name,
                "AGCP",
            )
            if any([tolerates, maintenance, agcp]):
                self.set_font("Helvetica", "B", 13)
                self.cell(
                    0,
                    8,
                    "Characteristics",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
                self.set_font("Helvetica", "", 12)
                char_parts = []
                if tolerates:
                    char_parts.append(("Tolerates:", tolerates))
                if maintenance:
                    char_parts.append(("Maintenance:", maintenance))
                if agcp:
                    char_parts.append(("AGCP Status:", agcp))
                draw_labeled_parts(self, char_parts)
                self.ln(2)

            # ── Appearance ──
            self.set_font("Helvetica", "B", 13)
            self.cell(
                0,
                8,
                "Appearance",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            self.set_font("Helvetica", "", 12)
            appearance_parts = []
            color_text = safe_text(row.get("Bloom Color", ""))
            if color_text:
                segments = []
                colors = [c.strip() for c in color_text.split(",")]
                for i, color in enumerate(colors):
                    rgb = (
                        {
                            "red": (200, 0, 0),
                            "pink": (255, 105, 180),
                            "purple": (128, 0, 128),
                            "blue": (0, 0, 200),
                            "yellow": (200, 180, 0),
                            "orange": (255, 140, 0),
                            "green": (34, 139, 34),
                        }.get(color.lower(), (0, 0, 0))
                        if color.lower() != "white"
                        else (0, 0, 0)
                    )
                    segments.append((color, rgb))
                    if i < len(colors) - 1:
                        segments.append((", ", None))
                appearance_parts.append(("Bloom Color:", segments))
            ht = safe_text(row.get("Height (ft)", ""))
            if ht:
                appearance_parts.append(("Height:", f"{ht} ft"))
            sp = safe_text(row.get("Spread (ft)", ""))
            if sp:
                appearance_parts.append(("Spread:", f"{sp} ft"))
            bloom_time = safe_text(row.get("Bloom Time", ""))
            if bloom_time:
                appearance_parts.append(("Bloom Time:", bloom_time))
            draw_labeled_parts(self, appearance_parts)
            self.ln(6)

            # ── Site & Wildlife Details ──
            self.set_font("Helvetica", "B", 13)
            self.cell(
                0,
                8,
                "Site & Wildlife Details",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            self.set_font("Helvetica", "", 12)
            site_parts = []
            sun = safe_text(row.get("Sun", ""))
            water = safe_text(row.get("Water", ""))
            zone_raw = safe_text(
                row.get("Distribution Zone", "") or row.get("Zone", "")
            )
            zone_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", zone_raw)
            zone = (
                f"{zone_match.group(1)} to {zone_match.group(2)}"
                if zone_match
                else zone_raw.replace("USDA Hardiness Zone", "").strip()
            )
            if sun:
                site_parts.append(("Sun:", sun))
            if water:
                site_parts.append(("Water:", water))
            if zone:
                site_parts.append(("USDA Hardiness Zone:", zone))
            draw_labeled_parts(self, site_parts)
            self.ln(4)

            # Attracts
            attracts = truncate_text(
                safe_text(row.get("Attracts", "")), max_len, bot_name, "Attracts"
            )
            if attracts:
                self.set_font("Helvetica", "B", 12)
                self.write(6, "Attracts: ")
                self.set_font("Helvetica", "", 12)
                self.multi_cell(0, 6, attracts)
                self.ln(6)

            # Soil Description
            soil = truncate_text(
                safe_text(row.get("Soil Description", "")),
                max_len,
                bot_name,
                "Soil Description",
            )
            if soil:
                self.set_font("Helvetica", "B", 12)
                self.write(6, "Soil Description: ")
                self.set_font("Helvetica", "", 12)
                self.multi_cell(0, 6, soil)
                self.ln(6)

            # Habitats
            habitats = truncate_text(
                safe_text(row.get("Native Habitats", "") or row.get("Habitats", "")),
                max_len,
                bot_name,
                "Habitats",
            )
            if habitats:
                self.set_font("Helvetica", "B", 12)
                self.write(6, "Habitats: ")
                self.set_font("Helvetica", "", 12)
                self.multi_cell(0, 6, habitats)

            # Verify single-page layout
            end_page = self.page_no()
            end_y = self.get_y()
            allowed_height = self.h - self.b_margin
            overflow = end_page != page_start or end_y > allowed_height
            self.set_auto_page_break(auto=True, margin=20)
            if overflow:
                logging.warning(
                    "Truncating content for %s to fit on one page", bot_name
                )
                if self.page in self.pages:
                    del self.pages[self.page]
                    self.page -= 1
                max_len = max(50, max_len - 50)
                continue
            display_page = self.page_no() - getattr(self, "_ghost_pages", 0)
            self.toc[plant_type].append((bot_name, display_page, link, links))
            break


# ─── Build PDF ────────────────────────────────────────────────────────────
pdf = PlantPDF()  # Instantiate PDF generator
pdf._ghost_pages = 0  # Title page unnumbered

# ─── Title Page ──────────────────────────────────────────────────────────
pdf.skip_footer = True  # Disable footer on cover
pdf.add_page()


def try_image_path(base_dir, filenames):
    for name in filenames:
        path = base_dir / name
        if path.exists():
            return path
    return None


left_logo = try_image_path(
    logo_dir,
    ["page_1_0.jpg", "page_1_0.png"],
)
right_logo = try_image_path(
    logo_dir,
    ["page_1_1.jpg", "page_1_1.png"],
)
if left_logo:
    pdf.image(str(left_logo), x=pdf.l_margin, y=20, h=30)
if right_logo:
    pdf.image(str(right_logo), x=pdf.w - pdf.r_margin - 50, y=20, h=30)


pdf.set_y(70)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(0, 70, 120)
pdf.cell(0, 12, "PLANT FACT SHEETS", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "", 16)
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
pdf.set_font("Helvetica", "", 14)
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
pdf.set_font("Helvetica", "I", 12)
pdf.cell(
    0, 10, f"{datetime.today():%B %Y}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
)
pdf.set_text_color(0, 0, 0)
pdf.ln(4)
pdf.set_font("Helvetica", "", 11)
draw_wrapped_legend(pdf)

# ─── Reserve TOC pages (2–4) ─────────────────────────────────────────────
pdf.skip_footer = False
pdf.add_page()
pdf.add_page()
pdf.add_page()

# ─── Add plant sections and pages ────────────────────────────────────────
for plant_type in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == plant_type]  # Filter by type
    if not group.empty:
        pdf.add_type_divider(plant_type)
        for _, row in group.iterrows():
            if row.get("Botanical Name", "").strip():
                pdf.add_plant(row, plant_type)

# ─── Insert TOC content ──────────────────────────────────────────────────
pdf.page = 2
pdf.add_table_of_contents()

# ─── Save PDF ───────────────────────────────────────────────────────────
pdf.output(str(OUTPUT))
print(f"✅ Exported with TOC on pages 1-3 → {OUTPUT}")
