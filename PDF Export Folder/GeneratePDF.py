# generate_plant_pdf.py
# Styled PDF plant guide generator with title page, TOC, and hyperlinked entries

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.errors import FPDFException
from pathlib import Path
import pandas as pd
import re
from PIL import Image
from datetime import datetime


# ─── Constants ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "Plants_Links_Filled_Master_Copy.csv"
IMG_DIR = BASE_DIR.parent / "PDF Export Folder" / "pdf_images" / "jpeg"
OUTPUT = BASE_DIR / "Plant_Guide_EXPORT.pdf"

# ─── Load and Prepare Data ────────────────────────────────────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
df["Plant Type"] = df["Plant Type"].str.upper()
df["Page in PDF"] = pd.to_numeric(df["Page in PDF"], errors="coerce")

PLANT_TYPE_ORDER = [
    "HERBACEOUS, PERENNIAL",
    "FERNS",
    "GRASSES, SEDGES, AND RUSHES",
    "SHRUBS",
    "TREES"
]

# ─── Helpers ──────────────────────────────────────────────────────────────
def safe_text(text: str) -> str:
    text = str(text).replace("\x00", "").replace("\r", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[^\x20-\x7E]+", "", text)
    return text.strip()

def primary_common_name(name):
    if "/" in name:
        return name.split("/")[0].strip()
    elif " or " in name:
        return name.split(" or ")[0].strip()
    return name

def name_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

# ─── PDF Class ────────────────────────────────────────────────────────────
class PlantPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.section_links = []
        self.toc = {ptype: [] for ptype in PLANT_TYPE_ORDER}
        self.set_auto_page_break(auto=True, margin=20)
        self.skip_footer = False
        self.footer_links = (None, None)


    def footer(self):
        if self.skip_footer:
            return
        self.set_y(-10)
        self.set_font("Helvetica", "I", 9)

        # MBG / WF links
        self.set_text_color(0, 0, 200)
        x_start = self.l_margin
        mbg, wf = self.footer_links
        if mbg:
            self.set_x(x_start)
            self.cell(self.get_string_width("[MBG]") + 2, 10, "[MBG]", link=mbg)
            x_start += self.get_string_width("[MBG]") + 8
        if wf:
            self.set_x(x_start)
            self.cell(self.get_string_width("[WF]") + 2, 10, "[WF]", link=wf)

        # Page number
        self.set_text_color(128, 128, 128)
        self.set_x(-20)
        display_page = self.page_no() - getattr(self, "_ghost_pages", 0)
        if display_page > 0:
            self.cell(0, 10, f"{display_page}", align="R")


    def add_type_divider(self, plant_type):
        self.footer_links = (None, None)
        self.skip_footer = True
        self.add_page()
        self.skip_footer = False
        link = self.add_link()
        self.set_link(link)
        self.section_links.append((plant_type, link))
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)
        self.cell(0, 20, plant_type.title(), align="C")
        self.set_text_color(0, 0, 0)

    def add_table_of_contents(self):
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
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(0, 0, 128)
                self.cell(0, 8, ptype.title(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.set_font("Helvetica", "", 11)
                self.set_text_color(0, 0, 0)
                for name, page in entries:
                    self.cell(140, 6, f"  {name}")
                    self.cell(0, 6, f"{page}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(2)

    def add_plant(self, row, plant_type):
        bot_name = safe_text(row.get("Botanical Name", ""))
        base_name = name_slug(bot_name)
        mbg = row.get("Link: Missouri Botanical Garden", "").strip()
        wf = row.get("Link: Wildflower.org", "").strip()
        self.add_page()
        self.footer_links = (mbg if mbg else None, wf if wf else None)

        display_page = self.page_no() - getattr(self, "_ghost_pages", 0)
        self.toc[plant_type].append((bot_name, display_page))

        self.set_font("Helvetica", "I", 18)
        self.set_text_color(22, 92, 34)
        self.multi_cell(0, 8, bot_name, align="C")

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


        # Draw Images
        images = sorted(IMG_DIR.glob(f"*_{base_name}_*.jpg"))
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
                self.rect(x, y0, img_w, img_h_fixed)
            x += img_w + gap

        self.set_y(y0 + img_h_fixed + 6)

        # Characteristics
        chars = safe_text(row.get("Characteristics", ""))
        if chars:
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(0, 0, 0)
            self.cell(0, 8, "Characteristics", ln=1)
            self.set_font("Helvetica", "", 12)
            for part in chars.split("|"):
                label, _, desc = part.strip().partition(":")
                self.set_font("Helvetica", "B", 12)
                self.write(6, f"- {label.strip()}: ")
                self.set_font("Helvetica", "", 12)
                self.multi_cell(0, 6, desc.strip())
            self.ln(6)

        # Appearance
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, "Appearance", ln=1)
        self.set_font("Helvetica", "", 12)

        appearance_parts = []
        ht = safe_text(row.get("Height (ft)", ""))
        if ht:
            appearance_parts.append(("Height:", f"{ht} ft"))
        sp = safe_text(row.get("Spread (ft)", ""))
        if sp:
            appearance_parts.append(("Spread:", f"{sp} ft"))

        color_text = safe_text(row.get("Bloom Color", ""))
        if color_text:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Bloom Color: ")
            self.set_font("Helvetica", "", 12)
            for i, color in enumerate(color_text.split(",")):
                color = color.strip()
                if color.lower() != "white":
                    hex_color = {
                        "red": (200, 0, 0),
                        "pink": (255, 105, 180),
                        "purple": (128, 0, 128),
                        "blue": (0, 0, 200),
                        "yellow": (200, 180, 0),
                        "orange": (255, 140, 0),
                        "green": (34, 139, 34),
                    }.get(color.lower(), (0, 0, 0))
                    self.set_text_color(*hex_color)
                else:
                    self.set_text_color(0, 0, 0)
                self.write(6, color)
                if i < len(color_text.split(",")) - 1:
                    self.write(6, ", ")
            self.set_text_color(0, 0, 0)
            self.ln(6)

        time = safe_text(row.get("Bloom Time", ""))
        if time:
            appearance_parts.append(("Bloom Time:", time))

        for i, (label, val) in enumerate(appearance_parts):
            self.set_font("Helvetica", "B", 12)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 12)
            self.write(6, val)
            if i < len(appearance_parts) - 1:
                self.write(6, "   |   ")
        self.ln(10)

        # Site & Wildlife Details
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, "Site & Wildlife Details", ln=1)
        self.set_font("Helvetica", "", 12)

        site_parts = []
        sun = safe_text(row.get("Sun", ""))
        if sun:
            site_parts.append(("Sun:", sun))
        water = safe_text(row.get("Water", ""))
        if water:
            site_parts.append(("Water:", water))
        dist = safe_text(row.get("Distribution", ""))
        if dist:
            site_parts.append(("Zone:", dist))

        for i, (label, val) in enumerate(site_parts):
            self.set_font("Helvetica", "B", 12)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 12)
            self.write(6, val)
            if i < len(site_parts) - 1:
                self.write(6, "   |   ")
        self.ln(8)

        # Wildlife Benefits
        wb = safe_text(row.get("Wildlife Benefits", ""))
        if wb:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Wildlife Benefits: ")
            self.set_font("Helvetica", "", 12)
            self.multi_cell(0, 6, wb)
            self.ln(6)

        # Habitats
        habitats = safe_text(row.get("Habitats", ""))
        if habitats:
            self.set_font("Helvetica", "B", 12)
            self.write(6, "Habitats: ")
            self.set_font("Helvetica", "", 12)
            self.multi_cell(0, 6, habitats)

# ─── Build PDF ────────────────────────────────────────────────────────────
pdf = PlantPDF()
pdf._ghost_pages = 4  # only title page is unnumbered

# ─── Title Page (page 1) ──────────────────────────────────────────────────
pdf.skip_footer = True
pdf.add_page()
left_logo = BASE_DIR / "pdf_images" / "RutgersLeft.png"
right_logo = BASE_DIR / "pdf_images" / "RutgersRight.png"
pdf.image(str(left_logo), x=pdf.l_margin, y=20, h=30)
pdf.image(str(right_logo), x=pdf.w - pdf.r_margin - 50, y=20, h=30)

pdf.set_y(70)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(0, 70, 120)
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
pdf.set_text_color(0, 0, 0)

# ─── Reserve 3 pages for TOC (pages 2–4) ──────────────────────────────────
pdf.skip_footer = False
pdf.add_page()
pdf.add_page()
pdf.add_page()

# ─── Add Plant Pages (starting on page 5) ─────────────────────────────────
for plant_type in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == plant_type]
    if not group.empty:
        pdf.add_type_divider(plant_type)
        for _, row in group.iterrows():
            if row.get("Botanical Name", "").strip():
                pdf.add_plant(row, plant_type)

# ─── Fill TOC into pages 2–4 ──────────────────────────────────────────────
pdf.page = 2
pdf.add_table_of_contents()

# ─── Output PDF ───────────────────────────────────────────────────────────
pdf.output(str(OUTPUT))
print(f"✅ Exported with TOC on pages 2–4 and plants starting on page 5 → {OUTPUT}")

