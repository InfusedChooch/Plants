# /mnt/data/GeneratePDF.py
# Generates a styled PDF plant guide with title page, table of contents, and one page per plant including images and data.

from fpdf import FPDF                            # PDF generation library
from fpdf.enums import XPos, YPos               # Enums for text positioning
from fpdf.errors import FPDFException            # Exception for PDF text overflow
from pathlib import Path                         # Filesystem path handling
import pandas as pd                              # DataFrame handling for CSV
import re                                        # Regular expressions for text cleaning
from PIL import Image                            # Image handling for JPEGs
from datetime import datetime                    # To display current date on title page
import argparse

parser = argparse.ArgumentParser(description="Generate plant guide PDF")
parser.add_argument("--in_csv", default="Static/Templates/Plants_Linked_Filled_Master.csv", help="Input CSV file")
parser.add_argument("--out_pdf", default="Static/Outputs/Plant_Guide_EXPORT.pdf", help="Output PDF file")
parser.add_argument("--img_dir", default="Static/Outputs/pdf_images/jpeg", help="Image directory")
args = parser.parse_args()

# ─── Constants ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = Path(args.in_csv) if args.in_csv else Path("Static/Templates/Plants_Linked_Filled_Master.csv")
IMG_DIR = Path(args.img_dir) if args.img_dir else BASE_DIR / "Static/Outputs/pdf_images"
OUTPUT = Path(args.out_pdf)
logo_dir = IMG_DIR.parent if IMG_DIR.name == "jpeg" else IMG_DIR



# ─── Load and Prepare Data ────────────────────────────────────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")            # Read CSV, empty cells → ""
template_cols = list(pd.read_csv(Path("Static/Templates/Plants_Linked_Filled_Master.csv"), nrows=0).columns)
df = df.reindex(columns=template_cols + [c for c in df.columns if c not in template_cols])
df["Plant Type"] = df["Plant Type"].str.upper()             # Normalize plant types to uppercase
df["Page in PDF"] = pd.to_numeric(df["Page in PDF"], errors="coerce")  # Ensure page numbers are numeric

PLANT_TYPE_ORDER = [                                        # Desired order of sections
    "HERBACEOUS, PERENNIAL",
    "FERNS",
    "GRASSES, SEDGES, AND RUSHES",
    "SHRUBS",
    "TREES"
]

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

def name_slug(text: str) -> str:
    """Convert name to filesystem‐safe lowercase slug (letters/numbers → underscore)."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ─── PDF Class ────────────────────────────────────────────────────────────
class PlantPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")         # Use US Letter size
        self.current_plant_type = ""              # Track current section for footer
        self.section_links = []                   # Store links to section dividers
        self.toc = {ptype: [] for ptype in PLANT_TYPE_ORDER}  # TOC entries per section
        self.set_auto_page_break(auto=True, margin=20)        # Auto page breaks with margin
        self.skip_footer = False                  # Flag to disable footer temporarily
        self.footer_links = (None, None)          # Store MBG/WF links for footer

    def footer(self):
        if self.skip_footer:
            return

        self.set_y(-12)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(0, 0, 200)

        mbg, wf = self.footer_links
        page_str = str(self.page_no() - getattr(self, "_ghost_pages", 0))
        self.set_y(-12)

        # LEFT: MBG / WF
        self.set_x(self.l_margin)
        if mbg:
            label = "[Missouri Botanical Garden]"
            self.cell(self.get_string_width(label) + 2, 6, label, link=mbg)
            self.cell(4, 6, "")
        if wf:
            label = "[Wildflower.org]"
            self.cell(self.get_string_width(label) + 2, 6, label, link=wf)

        # CENTER: Plant type
        if self.current_plant_type:
            self.set_text_color(90, 90, 90)
            center_x = self.w / 2 - self.get_string_width(self.current_plant_type.title()) / 2
            self.set_xy(center_x, -12)
            self.cell(self.get_string_width(self.current_plant_type.title()) + 2, 6, self.current_plant_type.title())

        # RIGHT: Page number
        self.set_text_color(128, 128, 128)
        self.set_xy(self.w - self.r_margin - self.get_string_width(page_str), -12)
        self.cell(0, 6, page_str)


    def add_type_divider(self, plant_type):
        """Insert a full-page section divider with title and link anchor."""
        self.footer_links = (None, None)        # No links on divider page
        self.skip_footer = True                 # Temporarily hide footer
        self.add_page()                         # New page
        self.skip_footer = False                # Re-enable footer for subsequent pages
        link = self.add_link()                  # Add internal link target
        self.set_link(link)
        self.section_links.append((plant_type, link))
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)                             # Vertical spacing
        self.cell(0, 20, plant_type.title(), align="C")
        self.set_text_color(0, 0, 0)

    def add_table_of_contents(self):
        """Generate the TOC pages, listing each plant with page links."""
        self.footer_links = (None, None)
        self.skip_footer = True
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
            for name, page, link, mbg, wf in entries:
                self.set_x(self.l_margin)
                # Plant name (clickable)
                self.cell(self.get_string_width(name)+2, 6, name, link=link)
                # Inline MBG/WF
                if mbg:
                    self.set_text_color(0, 0, 200)
                    self.cell(self.get_string_width(" [MBG]")+1, 6, " [MBG]", link=mbg)
                if wf:
                    self.cell(self.get_string_width(" [WF]")+1, 6, " [WF]", link=wf)
                # Dots and right-aligned page number
                dot_x = self.get_x()
                page_str = str(page)
                dot_width = self.get_string_width(page_str) + 2
                dots = "." * int((self.w - self.r_margin - dot_x - dot_width) / self.get_string_width("."))
                self.cell(self.get_string_width(dots), 6, dots, align="L")
                self.cell(dot_width, 6, page_str, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_plant(self, row, plant_type):
        """Add a single plant page: title, images, and all details."""
        bot_name = safe_text(row.get("Botanical Name", ""))      # Clean botanical name
        base_name = name_slug(bot_name)                          # Slug for image filenames
        mbg = row.get("MBG Link", "").strip()
        wf  = row.get("WF Link", "").strip()
        self.current_plant_type = plant_type
        self.add_page()                                          # New PDF page
        self.footer_links = (mbg or None, wf or None)            # Links for footer

        # Add internal TOC entry
        display_page = self.page_no() - getattr(self, "_ghost_pages", 0)
        link = self.add_link()
        self.set_link(link)
        self.toc[plant_type].append((bot_name, display_page, link, mbg or None, wf or None))

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
                self.cell(self.get_string_width(common)+1, 8, common)
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
        img_w = (avail_w - (count-1)*gap) / count
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
                x_img = x + (img_w - scaled_w)/2
                y_img = y0 + (img_h_fixed - scaled_h)/2
                self.image(img_path, x=x_img, y=y_img, w=scaled_w, h=scaled_h)
            else:
                self.rect(x, y0, img_w, img_h_fixed)             # Empty box if no image
            x += img_w + gap
        self.set_y(y0 + img_h_fixed + 6)

        # ── Characteristics section ──
        chars = safe_text(row.get("Characteristics", ""))
        if chars:
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 8, "Characteristics", ln=1)
            self.set_font("Helvetica", "", 12)
            for part in chars.split("|"):
                label, _, desc = part.strip().partition(":")
                self.set_font("Helvetica", "B", 12)
                self.write(6, f"- {label.strip()}: ")
                self.set_font("Helvetica", "", 12)
                self.multi_cell(0, 6, desc.strip())
            self.ln(6)

        # ── Appearance ──
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, "Appearance", ln=1)
        self.set_font("Helvetica", "", 12)
        appearance_parts = []
        ht = safe_text(row.get("Height (ft)", ""))
        if ht:
            appearance_parts.append(("Height:", f"{ht} ft"))
        sp = safe_text(row.get("Spread (ft)", ""))
        if sp:
            appearance_parts.append(("Spread:", f"{sp} ft"))
        # Bloom color with colored text
        color_text = safe_text(row.get("Bloom Color", ""))
        if color_text:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Bloom Color: ")
            self.set_font("Helvetica", "", 12)
            for i, color in enumerate(color_text.split(",")):
                color = color.strip()
                if color.lower() != "white":
                    hex_color = {
                        "red": (200,0,0), "pink": (255,105,180),
                        "purple": (128,0,128), "blue": (0,0,200),
                        "yellow": (200,180,0), "orange": (255,140,0),
                        "green": (34,139,34)
                    }.get(color.lower(), (0,0,0))
                    self.set_text_color(*hex_color)
                else:
                    self.set_text_color(0,0,0)
                self.write(6, color)
                if i < len(color_text.split(","))-1:
                    self.write(6, ", ")
            self.set_text_color(0,0,0)
            self.ln(6)
        # Bloom time
        bloom_time = safe_text(row.get("Bloom Time", ""))
        if bloom_time:
            appearance_parts.append(("Bloom Time:", bloom_time))
        # Print height/spread/bloom time separated by bars
        for i, (label, val) in enumerate(appearance_parts):
            self.set_font("Helvetica", "B", 12)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 12)
            self.write(6, val)
            if i < len(appearance_parts)-1:
                self.write(6, "   |   ")
        self.ln(10)

        # ── Site & Wildlife Details ──
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, "Site & Wildlife Details", ln=1)
        self.set_font("Helvetica", "", 12)
        site_parts = []
        sun   = safe_text(row.get("Sun", ""))
        water = safe_text(row.get("Water", ""))
        zone  = safe_text(row.get("Zone", ""))
        if sun:
            site_parts.append(("Sun:", sun))
        if water:
            site_parts.append(("Water:", water))
        if zone:
            site_parts.append(("Zone:", zone))
        for i, (label, val) in enumerate(site_parts):
            self.set_font("Helvetica", "B", 12)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 12)
            self.write(6, val)
            if i < len(site_parts)-1:
                self.write(6, "   |   ")
        self.ln(8)

        # Attracts
        attracts = safe_text(row.get("Attracts", ""))
        if attracts:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Attracts: ")
            self.set_font("Helvetica", "", 12)
            self.multi_cell(0, 6, attracts)
            self.ln(6)

        # Soil Description
        soil = safe_text(row.get("Soil Description", ""))
        if soil:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Soil Description: ")
            self.set_font("Helvetica", "", 12)
            self.multi_cell(0, 6, soil)
            self.ln(6)

        # Habitats
        habitats = safe_text(row.get("Habitats", ""))
        if habitats:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Habitats: ")
            self.set_font("Helvetica", "", 12)
            self.multi_cell(0, 6, habitats)

# ─── Build PDF ────────────────────────────────────────────────────────────
pdf = PlantPDF()                               # Instantiate PDF generator
pdf._ghost_pages = 0                           # Title page unnumbered

# ─── Title Page ──────────────────────────────────────────────────────────
pdf.skip_footer = True                         # Disable footer on cover
pdf.add_page()
def try_image_path(base_dir, filenames):
    for name in filenames:
        path = base_dir / name
        if path.exists():
            return path
    return None

left_logo = try_image_path(logo_dir, ["rutgers_cooperative_extension_0.jpg", "rutgers_cooperative_extension_0.png"])
right_logo = try_image_path(logo_dir, ["rutgers_cooperative_extension_1.jpg", "rutgers_cooperative_extension_1.png"])
if left_logo:
    pdf.image(str(left_logo), x=pdf.l_margin, y=20, h=30)
if right_logo:
    pdf.image(str(right_logo), x=pdf.w - pdf.r_margin - 50, y=20, h=30)


pdf.set_y(70)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(0,70,120)
pdf.cell(0, 12, "PLANT FACT SHEETS", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "", 16)
pdf.ln(4)
pdf.cell(0, 10, "for Rain Gardens / Bioretention Systems", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(10)
pdf.set_font("Helvetica", "", 14)
pdf.cell(0, 10, "Rutgers Cooperative Extension", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.cell(0, 10, "Water Resources Program", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(10)
pdf.set_font("Helvetica", "I", 12)
pdf.cell(0, 10, f"{datetime.today():%B %Y}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(0,0,0)

# ─── Reserve TOC pages (2–4) ─────────────────────────────────────────────
pdf.skip_footer = False
pdf.add_page(); pdf.add_page(); pdf.add_page()

# ─── Add plant sections and pages ────────────────────────────────────────
for plant_type in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == plant_type]  # Filter by type
    if not group.empty:
        pdf.add_type_divider(plant_type)
        for _, row in group.iterrows():
            if row.get("Botanical Name","").strip():
                pdf.add_plant(row, plant_type)

# ─── Insert TOC content ──────────────────────────────────────────────────
pdf.page = 2
pdf.add_table_of_contents()

# ─── Save PDF ───────────────────────────────────────────────────────────
pdf.output(str(OUTPUT))
print(f"✅ Exported with TOC on pages 1-3 → {OUTPUT}")
