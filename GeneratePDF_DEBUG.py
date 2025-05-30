# Static/Python/GeneratePDF.py
# Generates a styled PDF plant guide with title page, TOC, and individual plant pages with images and data.

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from pathlib import Path
import pandas as pd
import re
import argparse
from datetime import datetime
from PIL import Image

# ─── CLI ──────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Generate plant guide PDF")
parser.add_argument("--in_csv", default="Static/Templates/Plants_Linked_Filled_Master.csv", help="Input CSV file")
parser.add_argument("--out_pdf", default="Static/Outputs/Plant_Guide_EXPORT.pdf", help="Output PDF file")
parser.add_argument("--img_dir", default="Static/Outputs/pdf_images/jpeg", help="Image directory")
args = parser.parse_args()

# ─── Paths ────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / args.in_csv
IMG_DIR = BASE / args.img_dir
OUT_PDF = BASE / args.out_pdf

# ─── Load Data ────────────────────────────────────────────────
df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
df["Plant Type"] = df["Plant Type"].str.upper()
df["Page in PDF"] = pd.to_numeric(df["Page in PDF"], errors="coerce")

PLANT_TYPE_ORDER = [
    "HERBACEOUS, PERENNIAL", "FERNS", "GRASSES, SEDGES, AND RUSHES", "SHRUBS", "TREES"
]

def name_slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

def safe(text):
    text = str(text).replace("\x00", "").replace("\r", "")
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[^\x20-\x7E]+", "", text)
    return text.strip()

class PlantPDF(FPDF):
    def __init__(self):
        super().__init__(format="Letter")
        self.set_auto_page_break(auto=True, margin=20)
        self.toc = {ptype: [] for ptype in PLANT_TYPE_ORDER}
        self.section_links = []
        self.current_plant_type = ""
        self.footer_links = (None, None)
        self.skip_footer = False
        self._ghost_pages = 0

    def footer(self):
        if self.skip_footer:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "I", 9)
        if self.current_plant_type:
            self.set_text_color(90, 90, 90)
            self.set_x(0)
            self.cell(0, 6, self.current_plant_type.title(), align="C")
            self.ln(3)
        self.set_text_color(0, 0, 200)
        x = self.l_margin
        mbg, wf = self.footer_links
        if mbg:
            self.set_x(x)
            self.cell(self.get_string_width("[MBG]")+2, 6, "[MBG]", link=mbg)
            x += self.get_string_width("[MBG]") + 8
        if wf:
            self.set_x(x)
            self.cell(self.get_string_width("[WF]")+2, 6, "[WF]", link=wf)
        self.set_text_color(128, 128, 128)
        self.set_x(-20)
        pg = self.page_no() - self._ghost_pages
        if pg > 0:
            self.cell(0, 6, str(pg), align="R")

    def add_type_divider(self, plant_type):
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
                for name, page, link, mbg, wf in entries:
                    self.set_x(self.l_margin)
                    self.cell(self.get_string_width(name)+2, 6, name, link=link)
                    if mbg:
                        self.set_text_color(0, 0, 200)
                        self.cell(self.get_string_width(" [MBG]")+1, 6, " [MBG]", link=mbg)
                    if wf:
                        self.cell(self.get_string_width(" [WF]")+1, 6, " [WF]", link=wf)
                    dot_x = self.get_x()
                    pg_str = str(page)
                    dot_width = self.get_string_width(pg_str) + 2
                    dots = "." * int((self.w - self.r_margin - dot_x - dot_width) / self.get_string_width("."))
                    self.cell(self.get_string_width(dots), 6, dots, align="L")
                    self.cell(dot_width, 6, pg_str, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def add_plant(self, row, plant_type):
        bot_name = safe(row.get("Botanical Name", ""))
        slug = name_slug(bot_name)
        mbg = row.get("Link: Missouri Botanical Garden", "").strip()
        wf  = row.get("Link: Wildflower.org", "").strip()
        self.current_plant_type = plant_type
        self.add_page()
        self.footer_links = (mbg or None, wf or None)
        display_page = self.page_no() - self._ghost_pages
        link = self.add_link()
        self.set_link(link)
        self.toc[plant_type].append((bot_name, display_page, link, mbg or None, wf or None))
        self.set_font("Helvetica", "I", 18)
        self.set_text_color(22, 92, 34)
        self.multi_cell(0, 8, bot_name, align="C")
        common = safe(row.get("Common Name", ""))
        if common:
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(0, 0, 0)
            self.multi_cell(0, 8, common, align="C")
        self.ln(2)
        images = sorted(list(IMG_DIR.glob(f"*_{slug}_*.jpg")) + list(IMG_DIR.glob(f"*_{slug}_*.png")))
        count = max(1, min(len(images), 3))
        margin = self.l_margin
        avail_w = self.w - margin - self.r_margin
        gap = 5
        img_w = (avail_w - (count-1)*gap) / count
        img_h = 100
        x = margin
        y0 = self.get_y()
        for i in range(count):
            if i < len(images):
                path = str(images[i])
                with Image.open(path) as im:
                    aspect = im.height / im.width
                h = min(img_w * aspect, img_h)
                w = h / aspect
                self.image(path, x=x+(img_w-w)/2, y=y0+(img_h-h)/2, w=w, h=h)
            else:
                self.rect(x, y0, img_w, img_h)
            x += img_w + gap
        self.set_y(y0 + img_h + 6)

# ─── BUILD PDF ───────────────────────────────────────────────────────────
pdf = PlantPDF()
pdf.skip_footer = True
pdf.add_page()

def try_logo(name):
    for ext in [".jpg", ".png"]:
        p = IMG_DIR / "jpeg" / f"{name}{ext}"
        if p.exists():
            return p
    return None

left = try_logo("001_rutgers_cooperative_extension_1")
right = try_logo("001_rutgers_cooperative_extension_2")
if left: pdf.image(str(left), x=pdf.l_margin, y=20, h=30)
if right: pdf.image(str(right), x=pdf.w - pdf.r_margin - 50, y=20, h=30)

pdf.set_y(70)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(0, 70, 120)
pdf.cell(0, 12, "PLANT FACT SHEETS", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "", 16)
pdf.cell(0, 10, "for Rain Gardens / Bioretention Systems", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "", 14)
pdf.cell(0, 10, "Rutgers Cooperative Extension", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.cell(0, 10, "Water Resources Program", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(10)
pdf.set_font("Helvetica", "I", 12)
pdf.cell(0, 10, f"{datetime.today():%B %Y}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(0, 0, 0)
pdf.skip_footer = False

# ─── TOC Pages 2–4 ───────────────────────────────────────────
pdf.add_page(); pdf.add_page(); pdf.add_page()
pdf._ghost_pages = 3

# ─── Add Plants ─────────────────────────────────────────────
for ptype in PLANT_TYPE_ORDER:
    group = df[df["Plant Type"] == ptype]
    if not group.empty:
        pdf.add_type_divider(ptype)
        for _, row in group.iterrows():
            if row.get("Botanical Name", "").strip():
                pdf.add_plant(row, ptype)

pdf.page = 2
pdf.add_table_of_contents()

pdf.output(str(OUT_PDF))
print(f"✅ Exported with TOC on pages 1–3 → {OUT_PDF}")
