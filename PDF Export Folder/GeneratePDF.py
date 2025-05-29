# generate_plant_pdf.py
# Styled PDF plant guide generator with title page, TOC, and hyperlinked entries

from fpdf import FPDF
from pathlib import Path
import pandas as pd
import re
from PIL import Image
from datetime import datetime

# ─── Constants ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "Plants_Links_Filled.csv"
IMG_DIR = BASE_DIR / "pdf_images"
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

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"{self.page_no()}", align="R")


    def draw_images_or_placeholders(self, base_name: str):
        images = sorted(IMG_DIR.glob(f"_{base_name}_*.png"))
        count = max(1, min(len(images), 3))
        margin = self.l_margin
        avail_w = self.w - margin - self.r_margin
        gap = 5
        img_w = (avail_w - (count - 1) * gap) / count
        img_h = img_w * 0.66
        x = margin
        y0 = self.get_y()
        for i in range(count):
            if i < len(images):
                self.image(str(images[i]), x=x, y=y0, w=img_w, h=img_h)
            else:
                self.rect(x, y0, img_w, img_h)
            x += img_w + gap
        self.ln(img_h + 4)

    def add_type_divider(self, plant_type):
        self.add_page()
        link = self.add_link()
        self.set_link(link)
        self.section_links.append((plant_type, link))
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(0, 70, 120)
        self.ln(80)
        self.cell(0, 20, plant_type.title(), align="C")
        self.set_text_color(0, 0, 0)

    def add_plant(self, row, plant_type):
        self.add_page()
        self.toc[plant_type].append((safe_text(row.get("Botanical Name", "")), self.page_no()))
        self.set_font("Helvetica", "I", 14)
        self.set_text_color(22, 92, 34)
        self.multi_cell(0, 8, safe_text(row.get("Botanical Name", "")), align="C")

        common = primary_common_name(safe_text(row.get("Common Name", "")))
        mbg = row.get("Link: Missouri Botanical Garden", "").strip()
        wf  = row.get("Link: Wildflower.org", "").strip()

        if common:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(60, 60, 60)
            common_width = self.get_string_width(common)
            link_width = 0
            if mbg:
                link_width += self.get_string_width(" [MBG]")
            if wf:
                link_width += self.get_string_width(" [WF]")

            total_width = common_width + link_width
            x_start = (self.w - total_width) / 2
            self.set_x(x_start)
            self.write(6, common)

            self.set_font("Helvetica", "B", 10)
            self.set_text_color(0, 0, 200)
            if mbg:
                self.write(6, " [MBG]", link=mbg)
            if wf:
                self.write(6, " [WF]", link=wf)

            self.set_text_color(0, 0, 0)
            self.ln(6)

        # Draw Images (original height)
        base_name = name_slug(row.get("Botanical Name", ""))
        images = sorted(IMG_DIR.glob(f"*_{base_name}_*.png"))
        count = max(1, min(len(images), 3))
        margin = self.l_margin
        avail_w = self.w - margin - self.r_margin
        gap = 5
        img_w = (avail_w - (count - 1) * gap) / count
        img_h = img_w * 0.66
        x = margin
        y0 = self.get_y()
        for i in range(count):
            if i < len(images):
                self.image(str(images[i]), x=x, y=y0, w=img_w, h=img_h)
            else:
                self.rect(x, y0, img_w, img_h)
            x += img_w + gap

        # 🔒 Dynamically anchor content just below image row
        self.set_y(y0 + img_h + 6)

        # Characteristics
        chars = safe_text(row.get("Characteristics", ""))
        if chars:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, "Characteristics", ln=1)
            self.set_font("Helvetica", "", 11)
            for part in chars.split("|"):
                label, _, desc = part.strip().partition(":")
                self.set_font("Helvetica", "B", 11)
                self.write(6, f"- {label.strip()}: ")
                self.set_font("Helvetica", "", 11)
                self.multi_cell(0, 6, desc.strip())
            self.ln(2)

        # Appearance
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "Appearance", ln=1)
        self.set_font("Helvetica", "", 11)
        appearance_parts = []

        ht = safe_text(row.get("Height (ft)", ""))
        if ht:
            appearance_parts.append(("Height:", f"{ht} ft"))
        sp = safe_text(row.get("Spread (ft)", ""))
        if sp:
            appearance_parts.append(("Spread:", f"{sp} ft"))
        color = safe_text(row.get("Bloom Color", ""))
        if color:
            appearance_parts.append(("Bloom Color:", color))
        time = safe_text(row.get("Bloom Time", ""))
        if time:
            appearance_parts.append(("Bloom Time:", time))

        for i, (label, val) in enumerate(appearance_parts):
            self.set_font("Helvetica", "B", 11)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 11)
            self.write(6, val)
            if i < len(appearance_parts) - 1:
                self.write(6, "   |   ")
        self.ln(8)

        # Site & Wildlife Details
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "Site & Wildlife Details", ln=1)
        self.set_font("Helvetica", "", 11)

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
            self.set_font("Helvetica", "B", 11)
            self.write(6, f"{label} ")
            self.set_font("Helvetica", "", 11)
            self.write(6, val)
            if i < len(site_parts) - 1:
                self.write(6, "   |   ")
        self.ln(8)

        # Wildlife Benefits
        wb = safe_text(row.get("Wildlife Benefits", ""))
        if wb:
            self.set_font("Helvetica", "B", 11)
            self.write(6, "Wildlife Benefits: ")
            self.set_font("Helvetica", "", 11)
            self.multi_cell(0, 6, wb)

        # Leave room for footer
        remaining = self.h - self.get_y() - 20
        if remaining < 10:
            self.add_page()

        # Habitats at bottom
        habitats = safe_text(row.get("Habitats", ""))
        if habitats:
            self.set_font("Helvetica", "B", 11)
            self.write(6, "Habitats: ")
            self.set_font("Helvetica", "", 11)
            self.multi_cell(0, 6, habitats)

    def add_table_of_contents(self):
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 12, "Table of Contents", ln=1)
        self.set_font("Helvetica", "", 12)
        self.ln(4)
        for ptype in PLANT_TYPE_ORDER:
            entries = self.toc.get(ptype, [])
            if entries:
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(0, 0, 128)
                self.cell(0, 8, ptype.title(), ln=1)
                self.set_font("Helvetica", "", 11)
                self.set_text_color(0, 0, 0)
                for name, page in entries:
                    self.cell(140, 6, f"  {name}")
                    self.cell(0, 6, f"{page}", align="R", ln=1)
                self.ln(2)

# ─── Build PDF ────────────────────────────────────────────────────────────

pdf = PlantPDF()

# Title Page
pdf.add_page()
left_logo = BASE_DIR / "pdf_images" / "RutgersLeft.png"
right_logo = BASE_DIR / "pdf_images" / "RutgersRight.png"
pdf.image(str(left_logo), x=pdf.l_margin, y=20, h=30)
pdf.image(str(right_logo), x=pdf.w - pdf.r_margin - 50, y=20, h=30)

pdf.set_y(70)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(0, 70, 120)
pdf.cell(0, 12, "PLANT FACT SHEETS", ln=1, align="C")

pdf.set_font("Helvetica", "", 16)
pdf.ln(4)
pdf.cell(0, 10, "for Rain Gardens / Bioretention Systems", ln=1, align="C")

pdf.ln(10)
pdf.set_font("Helvetica", "", 14)
pdf.cell(0, 10, "Rutgers Cooperative Extension", ln=1, align="C")
pdf.cell(0, 10, "Water Resources Program", ln=1, align="C")

pdf.ln(10)
pdf.set_font("Helvetica", "I", 12)
pdf.cell(0, 10, f"{datetime.today():%B %Y}", ln=1, align="C")
pdf.set_text_color(0, 0, 0)

# TOC + Plant Entries

for plant_type in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == plant_type]
    if not group.empty:
        pdf.add_type_divider(plant_type)
        for _, row in group.iterrows():
            if row.get("Botanical Name", "").strip():
                pdf.add_plant(row, plant_type)

pdf.add_table_of_contents()
pdf.output(OUTPUT)
print(f"✅ Exported → {OUTPUT.resolve()}")
