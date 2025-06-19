#!/usr/bin/env python3
# GeneratePDF.py – produce a printable plant guide PDF
# This script reads plant data from a CSV, formats it, and outputs a printable PDF guide.
# Major features: title page, table of contents, plant pages with images, color-coded links, and more.
# todo fix the TOC to not bleed into the next section
# todo figure out how to handle spacing for 1 page, OR make it bleed to 2 pages for each plant seperated at Maintenance
from pathlib import Path
import sys, argparse, logging, re
from datetime import datetime
from PIL import Image
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.errors import FPDFException
import yaml

# * GLOBALS: These are set in main() and used throughout the script
args = None
REPO = CSV_FILE = IMG_DIR = OUTPUT = TEMPLATE_CSV = LOGO_DIR = None
STYLE_FILE = None
_style_rules = []
df = pd.DataFrame()

# * PLANT TYPE ORDER: Controls the order of sections in the PDF
PLANT_TYPE_ORDER = [
    "HERBACEOUS, PERENNIAL",
    "FERNS",
    "GRASSES, SEDGES, AND RUSHES",
    "SHRUBS",
    "TREES",
]
# LM: Change this list to change the order or add/remove plant type sections.

# * LINK LABELS/LEGEND: Used for source links in the footer and TOC
LINK_LABELS = [
    ("Link: Missouri Botanical Garden", "MBG"),
    ("Link: Wildflower.org", "WF"),
    ("Link: Pleasantrunnursery.com", "PRN"),
    ("Link: Newmoonnursery.com", "NMN"),
    ("Link: Pinelandsnursery.com", "PNL"),
]
LINK_LEGEND = {
    "MBG": "Missouri Botanical Garden",
    "WF": "Wildflower",
    "PRN": "Pleasant Run Nursery",
    "NMN": "New Moon Nursery",
    "PNL": "Pinelands Nursery",
}
LINK_COLORS = {
    "MBG": (0, 70, 120),
    "WF": (200, 0, 0),
    "PRN": (128, 0, 128),
    "NMN": (255, 140, 0),
    "PNL": (34, 139, 34),
    "OTH": (0, 0, 200),
}
# LM: Change LINK_COLORS to change the color of link labels in the PDF.

# * Helper: Find the root of the project folder
def repo_dir() -> Path:
    """Return the root of the project folder (handles frozen EXE)."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (
            exe_dir.name.lower() == "helpers"
            and exe_dir.parent.name.lower() == "_internal"
        ):
            return exe_dir.parent.parent
        return exe_dir.parent
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Templates").is_dir() and (parent / "Outputs").is_dir():
            return parent
    return here.parent.parent

# * Text cleaning and style application
def safe_text(text: str) -> str:
    """Clean text for PDF core fonts (Latin-1)."""
    text = str(text).replace("\x00", "").replace("\r", "")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[^\x20-\x7E]+", "", text)  # strip non-Latin-1
    text = text.strip()
    if text.upper() == "NA":
        return ""
    return apply_style(text)

def apply_style(text: str) -> str:
    # Applies regex-based substitutions from style_rules.yaml (if present)
    for pat, repl in _style_rules:
        text = pat.sub(repl, text)
    return text

# * Utility: Get the primary common name (first if multiple)
def primary_common_name(name: str) -> str:
    if "/" in name:
        return name.split("/")[0].strip()
    if " or " in name:
        return name.split(" or ")[0].strip()
    return name

# * Utility: Truncate text to a max length, add ... if needed
def truncate_text(text: str, max_len: int, plant: str, field: str) -> str:
    if len(text) > max_len:
        logging.warning("Truncating %s for %s", field, plant)
        return text[: max_len - 3] + "..."
    return text

# * Utility: Make a slug (safe filename) from a string
def name_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# * Utility: Parse "other" links from CSV
OTHER_LINK_PATTERN = re.compile(
    r"\[(?P<tag>[^,\]]+),\"(?P<url>[^\"]+)\",\"(?P<label>[^\"]+)\"\]"
)
def parse_other_links(text: str) -> list[tuple[str, str, str]]:
    return OTHER_LINK_PATTERN.findall(text or "")

# * Draw the legend (source links) on the title page
def flush_columns(pdf, legend_items, col_count=3):
    # LM: Draws a table of legend items in columns
    max_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = max_w / col_count
    h = 6
    rows = (len(legend_items) + col_count - 1) // col_count
    table = [[] for _ in range(rows)]
    for idx, item in enumerate(legend_items):
        table[idx % rows].append(item)
    for row in table:
        pdf.set_x(pdf.l_margin)
        for abbr, label in row:
            pdf.set_text_color(*LINK_COLORS.get(abbr, (0, 0, 200)))
            pdf.cell(18, h, f"[{abbr}]", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_w - 18, h, label, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(h)

def draw_wrapped_legend(pdf):
    # LM: Draws the legend for standard and "other" links
    std, oth = [], []
    for abbr, label in LINK_LEGEND.items():
        (std if abbr in {"MBG", "WF", "PRN", "NMN", "PNL"} else oth).append(
            (abbr, label)
        )
    pdf.set_font("Times", "", 11)
    flush_columns(pdf, sorted(std), 3)
    if oth:
        pdf.set_text_color(*LINK_COLORS["OTH"])
        pdf.set_font("Times", "B", 11)
        pdf.cell(0, 8, "Other Links", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Times", "", 11)
        pdf.set_text_color(0, 0, 0)
        flush_columns(pdf, sorted(set(oth)), 3)
    pdf.set_font("Times", "", 12)

# * Draw characteristics in a wrapped, labeled format
def draw_labeled_parts(pdf, parts, sep=" | "):
    # LM: Draws labeled characteristics (e.g., "Height: 3 ft | Spread: 2 ft")
    max_w = pdf.w - pdf.l_margin - pdf.r_margin
    buf, line_w = [], 0
    sep_w = pdf.get_string_width(sep)

    def to_segs(val):
        return val if isinstance(val, list) else [(str(val), None)]

    def flush():
        nonlocal buf, line_w
        if not buf:
            return
        pdf.set_x(pdf.l_margin)
        for i, (lab, segs) in enumerate(buf):
            pdf.set_font("Times", "B", 12)
            pdf.write(6, f"{lab} ")
            pdf.set_font("Times", "", 12)
            for txt, clr in segs:
                pdf.set_text_color(*(clr if clr else (0, 0, 0)))
                pdf.write(6, txt)
            pdf.set_text_color(0, 0, 0)
            if i < len(buf) - 1:
                pdf.write(6, sep)
        pdf.ln(6)
        buf, line_w = [], 0

    for lab, val in parts:
        segs = to_segs(val)
        part_w = pdf.get_string_width(lab + " ") + sum(
            pdf.get_string_width(t) for t, _ in segs
        )
        if buf and line_w + sep_w + part_w > max_w:
            flush()
        if buf:
            line_w += sep_w
        buf.append((lab, segs))
        line_w += part_w
    flush()

# * Gather links for the footer
def gather_footer_links(row):
    links = [
        (lab, row[col].strip()) for col, lab in LINK_LABELS if row.get(col, "").strip()
    ]
    links += [
        (tag, url) for tag, url, _ in parse_other_links(row.get("Link: Others", ""))
    ]
    return links

# * Fetch images for a plant by slug
def fetch_images(bot_name: str):
    slug = name_slug(bot_name)
    yield from sorted(IMG_DIR.glob(f"{slug}_*.jpg"))
    yield from sorted(IMG_DIR.glob(f"{slug}_*.png"))

# * Draw Attracts/Tolerates line
def draw_line_of_tags(pdf, row, *, left="Attracts", right="Tolerates"):
    l_txt, r_txt = safe_text(row.get(left, "")), safe_text(row.get(right, ""))
    if not (l_txt or r_txt):
        return
    pdf.set_font("Times", "B", 12)
    pdf.write(6, f"{left}: ")
    pdf.set_font("Times", "", 12)
    pdf.write(6, l_txt or "-")
    if r_txt:
        pdf.set_font("Times", "B", 12)
        pdf.write(6, f"  |  {right}: ")
        pdf.set_font("Times", "", 12)
        pdf.write(6, r_txt)
    pdf.ln(6)

# * Main PDF class
class PlantPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.current_plant_type = ""
        self.current_rev = None
        self.section_links = []
        self.toc = {t: [] for t in PLANT_TYPE_ORDER}
        self.skip_footer = False
        self.footer_links = []
        self.set_auto_page_break(auto=True, margin=20)  # LM: Change margin for more/less space at bottom

    # * Footer: Shows links, plant type, and page number
    def footer(self):
        if self.skip_footer:
            return
        self.set_y(-12)
        self.set_font("Times", "I", 9)
        # LM: Draws source links centered at the bottom
        gap = 4
        widths = [self.get_string_width(f"[{lab}]") + 2 for lab, _ in self.footer_links]
        total_w = sum(widths) + gap * max(0, len(widths) - 1)
        start_x = max(self.l_margin, (self.w - total_w) / 2)
        self.set_x(start_x)
        for i, ((lab, url), w) in enumerate(zip(self.footer_links, widths)):
            self.set_text_color(*LINK_COLORS.get(lab, (0, 0, 200)))
            self.cell(w, 6, f"[{lab}]", link=url, align="C")
            if i < len(self.footer_links) - 1:
                self.cell(gap, 6, "")
        self.set_text_color(0, 0, 0)
        # LM: Plant type centered
        if self.current_plant_type:
            cx = self.w / 2 - self.get_string_width(self.current_plant_type.title()) / 2
            self.set_xy(cx, -8)
            self.set_text_color(90, 90, 90)
            self.cell(0, 6, self.current_plant_type.title())
        # LM: Page number right
        pg = str(self.page_no())
        self.set_text_color(128, 128, 128)
        self.set_xy(self.w - self.r_margin - self.get_string_width(pg), -12)
        self.cell(0, 6, pg)
        self.set_text_color(0, 0, 0)

    # * Section divider page (e.g., "TREES")
    def add_type_divider(self, plant_type):
        self.add_page()
        self.skip_footer = True
        self.current_rev = None
        self.footer_links = []
        link = self.add_link()
        self.set_link(link)
        self.section_links.append((plant_type, link))
        self.set_font("Times", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)
        self.cell(0, 20, plant_type.title(), align="C")
        self.skip_footer = False

    # * Add a single plant page
    def add_plant(self, row, plant_type):
        """
        Add a single plant page using Layoutmk1 structure.
        If the content is too long, it will shrink/truncate to fit up to 2 pages.
        """
        bot_name = safe_text(row.get("Botanical Name", ""))
        base_name = name_slug(bot_name)
        links = []

        # Helper to avoid smushing into footer
        def ensure_space(pdf, needed=30):
            if pdf.get_y() > pdf.h - pdf.b_margin - needed:
                pdf.add_page()

        # * Gather links for the footer
        for col, label in LINK_LABELS:
            url = row.get(col, "").strip()
            if url and url.upper() != "NA":
                links.append((label, url))
        for tag, url, label_name in parse_other_links(row.get("Link: Others", "")):
            if url and url.upper() != "NA":
                links.append((tag, url))
                LINK_LEGEND.setdefault(tag, label_name)
                LINK_COLORS.setdefault(tag, LINK_COLORS.get("OTH", (0, 0, 200)))

        self.current_plant_type = plant_type
        self.current_rev = safe_text(row.get("Rev", "")) or None
        link = self.add_link()
        max_pages = 1  # Only allow one page per plant
        max_len = 240  # You can adjust this for more/less text before truncation

        self.set_auto_page_break(auto=False)
        self.add_page()
        page_start = self.page_no()
        self.footer_links = links
        self.set_link(link)

        # * Revision marker (top left)
        if self.current_rev:
            rev_txt = f"Rev: {self.current_rev}"
            self.set_font("Times", "I", 9)
            self.set_text_color(150, 150, 150)
            self.set_xy(self.l_margin, 6)
            self.cell(self.get_string_width(rev_txt) + 1, 5, rev_txt)
            self.set_text_color(0, 0, 0)

        # * Botanical/Common Name (centered)
        self.ln(2)
        self.set_font("Times", "I", 18)
        self.set_text_color(22, 92, 34)
        w_bot = self.get_string_width(bot_name)
        self.set_x((self.w - w_bot) / 2)
        self.cell(
            w_bot + 1, 8, bot_name, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

        common = primary_common_name(safe_text(row.get("Common Name", ""))).strip()
        if common:
            self.set_font("Times", "B", 13)
            self.set_text_color(0, 0, 0)
            w_com = self.get_string_width(common)
            self.set_x((self.w - w_com) / 2)
            self.cell(
                w_com + 1, 6, common, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )

        self.ln(2)

        # * Images (up to 3, or placeholder boxes)
        images = sorted(
            list(IMG_DIR.glob(f"{base_name}_*.jpg"))
            + list(IMG_DIR.glob(f"{base_name}_*.png"))
        )
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

        self.set_y(y0 + img_h_fixed + 4)

        # * Characteristics section
        ensure_space(self, 40)
        self.set_font("Times", "B", 13)
        self.cell(0, 8, "Characteristics:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Times", "", 12)
        char_parts = []

        # * Add labeled characteristics (color, height, spread, etc.)
        color_text = safe_text(row.get("Bloom Color", ""))
        if color_text:
            segments = []
            for i, color in enumerate([c.strip() for c in color_text.split(",")]):
                rgb = (
                    {
                        "red": (200, 0, 0),
                        "pink": (255, 105, 180),
                        "purple": (128, 0, 128),
                        "blue": (0, 0, 200),
                        "yellow": (200, 180, 0),
                        "orange": (255, 140, 0),
                        "green": (34, 139, 34),
                        "indigo": (75, 0, 130),
                        "violet": (148, 0, 211),
                        "brown": (139, 69, 19),
                        "lavender": (230, 230, 250),
                    }.get(color.lower(), (0, 0, 0))
                    if color.lower() != "white"
                    else (0, 0, 0)
                )
                segments.append((color, rgb))
                if i < len(color_text.split(",")) - 1:
                    segments.append((", ", None))
            char_parts.append(("Bloom Color:", segments))

        if h := safe_text(row.get("Height (ft)", "")):
            char_parts.append(("Height:", f"{h} ft"))
        if s := safe_text(row.get("Spread (ft)", "")):
            char_parts.append(("Spread:", f"{s} ft"))
        if b := safe_text(row.get("Bloom Time", "")):
            char_parts.append(("Bloom Time:", b))

        self.ln(1)
        if sun := safe_text(row.get("Sun", "")):
            char_parts.append(("Sun:", sun))
        if water := safe_text(row.get("Water", "")):
            char_parts.append(("Water:", water))
        if agcp := safe_text(row.get("AGCP Regional Status", "")):
            char_parts.append(("AGCP Status:", agcp))
        zone_raw = safe_text(
            row.get("USDA Hardiness Zone", "") or row.get("Zone", "")
        )
        zone_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)", zone_raw)
        zone = (
            f"{zone_match.group(1)} - {zone_match.group(2)}"
            if zone_match
            else zone_raw
        )
        if zone:
            char_parts.append(("USDA Hardiness Zone:", zone))

        draw_labeled_parts(self, char_parts)
        self.ln(1)

        # * Attracts + Tolerates (inline)
        ensure_space(self, 18)
        attracts = truncate_text(
            safe_text(row.get("Attracts", "")), max_len, bot_name, "Attracts"
        )
        tolerates = truncate_text(
            safe_text(row.get("Tolerates", "")), max_len, bot_name, "Tolerates"
        )
        if attracts or tolerates:
            self.set_font("Times", "B", 12)
            self.write(6, "Attracts: ")
            self.set_font("Times", "", 12)
            self.write(6, attracts or "-")
            if tolerates:
                self.set_font("Times", "B", 12)
                self.write(6, "  |  Tolerates: ")
                self.set_font("Times", "", 12)
                self.write(6, tolerates)
            self.ln(6)

        # * Soil / Habitat
        ensure_space(self, 24)
        for label, key in [
            ("Native Habitats", "Native Habitats"),
            ("Soil Description", "Soil Description"),
        ]:
            val = truncate_text(
                safe_text(row.get(key, "") or row.get("Habitats", "")),
                max_len,
                bot_name,
                key,
            )
            if val:
                self.set_font("Times", "B", 12)
                self.write(6, f"{label}: ")
                self.set_font("Times", "", 12)
                self.multi_cell(0, 6, val)
        self.ln(4)

        # * Recommended Uses
        ensure_space(self, 24)
        self.set_font("Times", "B", 13)
        self.cell(0, 8, "Recommended Uses:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Times", "", 12)

        usexyz = safe_text(row.get("UseXYZ", ""))
        if usexyz:
            if "|" in usexyz:
                pieces = [t.strip() for t in usexyz.split("|") if t.strip()]
            else:
                pat = re.compile(r"(?=Use [^:]+:)")
                pieces = [t.strip(", ") for t in pat.split(usexyz) if t.strip(", ")]
            for i, tag in enumerate(pieces):
                head, body = (
                    (p.strip() for p in tag.split(":", 1))
                    if ":" in tag
                    else (tag, "")
                )
                if body:
                    self.set_font("Times", "B", 12)
                    self.write(6, f"{head}:")
                    self.set_font("Times", "", 12)
                    self.write(6, f" {body}")
                else:
                    self.set_font("Times", "B", 12)
                    self.write(6, head)
                if i < len(pieces) - 1:
                    self.write(6, "  |  ")
            self.ln(6)  # LM: Spacing below UseXYZ block

        # * General Maintenance Level
        ensure_space(self, 14)
        level = safe_text(row.get("MaintenanceLevel", "")).capitalize()
        color = {
            "Low": (34, 139, 34),
            "Medium": (255, 140, 0),
            "High": (200, 0, 0),
        }.get(level, (90, 90, 90))
        self.set_font("Times", "B", 13)
        self.write(6, "General Maintenance Level")
        self.set_text_color(*color)
        self.write(6, f" - {level}")
        self.set_text_color(0, 0, 0)
        self.ln(6)  # LM: Gap before next bold label

        # * Maintenance Details
        ensure_space(self, 16)
        val = truncate_text(
            safe_text(row.get("WFMaintenance", "")),
            max_len,
            bot_name,
            "WFMaintenance",
        )
        if val:
            # Remove redundant prefixes
            lower = val.lower().lstrip()
            for p in ("maintenance:", "maintenace:", "maintenence:"):
                if lower.startswith(p):
                    val = val[len(p) :].lstrip()
                    break

            self.set_font("Times", "B", 12)
            self.write(6, "Maintenance: ")
            self.set_font("Times", "", 12)
            self.write(6, val)
            self.ln(6)

        for key in ["Problems", "Condition Comments"]:
            ensure_space(self, 14)
            val = truncate_text(safe_text(row.get(key, "")), max_len, bot_name, key)
            if val:
                self.set_font("Times", "B", 12)
                self.write(6, f"{key.replace('_', ' ')}: ")
                self.set_font("Times", "", 12)
                self.write(6, val)
                self.ln(6)

        end_page = self.page_no()
        pages_used = end_page - page_start + 1
        self.set_auto_page_break(auto=True, margin=20)

        if pages_used > max_pages:
            logging.warning(f"Plant {bot_name} content truncated to fit one page.")
        display_page = self.page_no()
        self.toc[plant_type].append((bot_name, display_page, link, links))

    # * Table of Contents (TOC)
    def add_table_of_contents(self):
        # LM: This method auto-breaks pages so TOC sections/entries never bleed into each other.
        self.footer_links = []
        self.skip_footer = False
        self.current_plant_type = "Table of Contents"
        self.set_y(20)
        self.set_font("Times", "B", 16)
        self.cell(0, 12, "Table of Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)
        self.set_font("Times", "", 12)
        y_limit = self.h - 25  # LM: bottom margin
        entry_height = 10      # Height needed for each entry (increased for clarity)
        section_header_height = 18

        for ptype in PLANT_TYPE_ORDER:
            ent = self.toc.get(ptype, [])
            if ent:
                # * Check if there's enough space for the section header AND at least one entry
                if self.get_y() > y_limit - (section_header_height + entry_height):
                    self.add_page()
                    self.set_font("Times", "B", 16)
                    self.cell(0, 12, "Table of Contents (cont.)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    self.ln(4)
                    self.set_font("Times", "", 12)
                self.set_font("Times", "B", 13)
                self.set_text_color(0, 0, 128)
                self.cell(0, 8, ptype.title(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_font("Times", "", 11)
                self.set_text_color(0, 0, 0)
            for name, page, link, links in ent:
                # Check if there's enough space for the entry
                if self.get_y() > y_limit - entry_height:
                    self.add_page()
                    self.set_font("Times", "B", 16)
                    self.cell(0, 12, "Table of Contents (cont.)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    self.ln(4)
                    self.set_font("Times", "B", 13)
                    self.set_text_color(0, 0, 128)
                    self.cell(0, 8, ptype.title() + " (cont.)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    self.set_font("Times", "", 11)
                    self.set_text_color(0, 0, 0)
                self.set_x(self.l_margin)
                self.cell(self.get_string_width(name) + 2, 6, name, link=link)
                for lab, url in links:
                    self.set_text_color(*LINK_COLORS.get(lab, (0, 0, 200)))
                    ab = f" [{lab}]"
                    self.cell(self.get_string_width(ab) + 1, 6, ab, link=url)
                self.set_text_color(0, 0, 0)
                dot_x = self.get_x()
                pg = str(page)
                dots = "." * int(
                    (self.w - self.r_margin - dot_x - self.get_string_width(pg) - 2)
                    / self.get_string_width(".")
                )
                self.cell(self.get_string_width(dots), 6, dots, align="L")
                self.cell(
                    self.get_string_width(pg) + 2,
                    6,
                    pg,
                    align="R",
                    new_x=XPos.LMARGIN,
                    new_y=YPos.NEXT,
                )
                self.ln(2)  # Add extra space after each entry for clarity

    # * Helpers for fitting/shrinking text (used for advanced fitting)
    def get_text_height(pdf, text, width, font_family, font_style, font_size):
        pdf.set_font(font_family, font_style, font_size)
        lines = pdf.multi_cell(width, pdf.font_size_pt * 1.2, text, split_only=True)
        return len(lines) * pdf.font_size_pt * 1.2

    def fit_text_to_space(pdf, text, width, max_height, font_family="Times", font_style="", min_font=8, max_font=12):
        for font_size in range(max_font, min_font - 1, -1):
            height = pdf.get_text_height(text, width, font_family, font_style, font_size)
            if height <= max_height:
                return font_size, text
        # If nothing fits, truncate text
        truncated = text
        while pdf.get_text_height(truncated, width, font_family, font_style, min_font) > max_height and len(truncated) > 10:
            truncated = truncated[:-10]
        if len(truncated) < len(text):
            truncated = truncated.rstrip() + "..."
        return min_font, truncated

    def write_section(self, label, text, max_len, font_size=11, line_height=5):
        if text:
            self.set_font("Times", "B", font_size)
            self.cell(0, line_height, label, ln=1)
            self.set_font("Times", "", font_size)
            self.multi_cell(0, line_height, truncate_text(text, max_len))
            self.ln(1)

    def fit_section(self, label, text, max_len, min_font=8, max_font=11, line_height=4):
        for font_size in range(max_font, min_font - 1, -1):
            self.set_font("Times", "", font_size)
            n_lines = len(self.multi_cell(0, line_height, truncate_text(text, max_len), split_only=True))
            needed_height = n_lines * line_height
            if self.get_y() + needed_height < self.h - 20:
                self.set_font("Times", "B", font_size)
                self.cell(0, line_height, label, ln=1)
                self.set_font("Times", "", font_size)
                self.multi_cell(0, line_height, truncate_text(text, max_len))
                self.ln(1)
                return
        # If nothing fits, truncate more
        self.set_font("Times", "B", min_font)
        self.cell(0, line_height, label, ln=1)
        self.set_font("Times", "", min_font)
        self.multi_cell(0, line_height, truncate_text(text, int(max_len * 0.7)) + "...")
        self.ln(1)

# * MAIN: Parse arguments, load data, and build the PDF
def main() -> None:
    """
    Parse arguments and generate the PDF.
    You can change the input/output files and image/logo folders here.
    """
    global args, REPO, CSV_FILE, IMG_DIR, OUTPUT, TEMPLATE_CSV, LOGO_DIR
    global STYLE_FILE, _style_rules, df

    parser = argparse.ArgumentParser(description="Generate plant guide PDF")
    parser.add_argument(
        "--in_csv",
        default="Outputs/Plants_Linked_Filled.csv",
        help="Input CSV file with filled data",
    )
    parser.add_argument(
        "--out_pdf", default="Outputs/Plant_Guide_EXPORT.pdf", help="Output PDF file"
    )
    parser.add_argument(
        "--img_dir",
        default="Outputs/Images/Plants",
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

    # * Set up paths
    REPO = repo_dir()
    CSV_FILE = (REPO / args.in_csv).resolve()
    IMG_DIR = (REPO / args.img_dir).resolve()
    OUTPUT = (REPO / args.out_pdf).resolve()
    TEMPLATE_CSV = (REPO / args.template_csv).resolve()
    LOGO_DIR = (REPO / args.logo_dir).resolve()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # * Load plant data
    df = (
        pd.read_csv(CSV_FILE, dtype=str, keep_default_na=False)
        .fillna("")
        .replace("Needs Review", "")
    )
    template_cols = list(
        pd.read_csv(TEMPLATE_CSV, nrows=0, keep_default_na=False).columns
    )
    df = df.reindex(
        columns=template_cols + [c for c in df.columns if c not in template_cols]
    )
    df["Plant Type"] = df["Plant Type"].str.upper()
    if "Page in PDF" in df.columns:
        df["Page in PDF"] = pd.to_numeric(df["Page in PDF"], errors="coerce")

    # * Load style rules (if present)
    STYLE_FILE = REPO / "Templates" / "style_rules.yaml"
    _style_rules = []
    if STYLE_FILE.exists():
        with open(STYLE_FILE, "r", encoding="utf-8") as f:
            subs = yaml.safe_load(f) or {}
            subs = subs.get("substitutions", subs)
        for pattern, repl in subs.items():
            pat = re.compile(pattern)
            _style_rules.append(
                (pat, (lambda m: m.group(0).lower()) if repl == "<<lower>>" else repl)
            )
    else:
        logging.warning("Style file not found: %s (continuing without it)", STYLE_FILE)

    # * Extend link legend with "other" links found in data
    if "Link: Others" in df.columns:
        for cell in df["Link: Others"]:
            for tag, url, label in parse_other_links(cell):
                LINK_LEGEND.setdefault(tag, label)
                LINK_COLORS.setdefault(tag, LINK_COLORS["OTH"])

    # * Build the PDF
    pdf = PlantPDF()

    # * Title page
    pdf.skip_footer = True
    pdf.add_page()

    # * Draw logos on title page
    def find_logo(base: Path, names: list[str]) -> Path | None:
        for stem in names:
            for ext in ("", ".png", ".jpg", ".jpeg"):
                p = base / f"{stem}{'' if stem.lower().endswith(ext) else ext}"
                if p.exists():
                    return p
        return None

    left_logo = find_logo(LOGO_DIR, ["Rutgers_Logo"])
    right_logo = find_logo(LOGO_DIR, ["NJAES_Logo"])

    def draw_logos(pdf: FPDF, left: Path, right: Path, *, y=16, h=24, gap=4):
        if not (left and right):
            return
        with Image.open(left) as im:
            w_left = h * im.width / im.height
        with Image.open(right) as im:
            w_right = h * im.width / im.height
        total = w_left + gap + w_right
        x0 = (pdf.w - total) / 2
        pdf.image(str(left), x=x0, y=y, h=h)
        pdf.image(str(right), x=x0 + w_left + gap, y=y, h=h)

    draw_logos(pdf, left_logo, right_logo)

    # * Title and legend
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
        0,
        10,
        f"{datetime.today():%B %Y}",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_font("Times", "", 10)
    draw_wrapped_legend(pdf)
    pdf.set_font("Times", "", 12)

    # * Reserve TOC pages (will be overwritten later)
    pdf.skip_footer = False
    pdf.add_page()
    pdf.add_page()
    pdf.add_page()
    pdf.add_page()  # Increased from 3 to 4 pages for TOC

    # * Add plant pages by type
    for ptype in PLANT_TYPE_ORDER:
        grp = df[df["Plant Type"] == ptype]
        if not grp.empty:
            if pdf.page < 6:  # Ensure a page break after TOC if needed
                pdf.add_page()
            pdf.add_type_divider(ptype)
            for _, row in grp.iterrows():
                if row.get("Botanical Name", "").strip():
                    start_page = len(pdf.pages) + 1
                    pdf.add_plant(row, ptype)
                    end_page = len(pdf.pages)
                    pages_used = end_page - start_page + 1
                    if pages_used > 2:
                        logging.warning("Plant %s spans %d pages, consider revising", row.get("Botanical Name", ""), pages_used)

    last_type = pdf.current_plant_type
    last_links = pdf.footer_links
    # * Fill TOC (overwrite reserved pages)
    pdf.page = 2
    pdf.add_table_of_contents()
    pdf.current_plant_type = ""

    # * Ensure footer on last page
    pdf.page = len(pdf.pages)
    pdf.current_plant_type = last_type
    pdf.footer_links = last_links
    pdf.skip_footer = False
    pdf.set_auto_page_break(False)

    pdf.set_y(-15)
    pdf.set_font("Times", "", 1)
    pdf.cell(0, 1, "")
    pdf.footer()

    # * Save the PDF
    pdf.output(str(OUTPUT))
    print(f"[OK] Exported PDF -> {OUTPUT}")

if __name__ == "__main__":
    main()
