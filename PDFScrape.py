# plants/PDFScrape.py
# Reads the Rutgers PDF & fills raw data into Plants_FROM_PDF_ONLY.csv

import re
from pathlib import Path

import pandas as pd
import pdfplumber
from tqdm import tqdm

# ─── configuration ──────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
INPUT_CSV  = BASE_DIR / "Plants and Links.csv"
OUTPUT_CSV = BASE_DIR / "Plants_FROM_PDF_ONLY.csv"
PDF_PATH   = BASE_DIR / "Plant Guid Data Base.pdf"

FIELDS = {                       # csv-column aliases
    "height":       "Height (ft)",
    "spread":       "Spread (ft)",
    "color":        "Bloom Color",
    "bloom":        "Bloom Time",
    "sun":          "Sun",
    "water":        "Water",
    "wet":          "Wetland Status",
    "habitat":      "Habitats",
    "char":         "Characteristics",
    "wildlife":     "Wildlife Benefits",
    "dist":         "Distribution",
    "type":         "Type",
    "planttype":    "Plant Type",
}

# ─── tiny formatters ────────────────────────────────────────────────────────
def std_height_range(val: str | None) -> str | None:
    if not val:
        return None
    val = val.replace("–", "-").replace("to", "-")
    nums = re.findall(r"[\d.]+", val)
    return f"{nums[0]} - {nums[1]}" if len(nums) == 2 else val.strip()


def std_color(val: str | None) -> str | None:
    if not val:
        return None
    val = val.replace(",", "/").replace(" or ", "/").replace(" and ", "/")
    return re.sub(r"\s*/\s*", "/", val.strip())


def std_bloom(val: str | None) -> str | None:
    if not val:
        return None
    months = re.findall(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)",
        val,
        flags=re.I,
    )
    if len(months) >= 2:
        return f"{months[0].title()} - {months[1].title()}"
    if months:
        return months[0].title()
    return val.strip()


def std_sun(val: str | None) -> str | None:
    if not val:
        return None
    parts = re.split(r",|;| or ", val.lower())
    return ", ".join(p.strip().capitalize() for p in parts if p.strip())


def key_from_name(name: str, used: set[str]) -> str:
    """Generate a short key (e.g. Amsonia tabernaemontana → ATa)."""
    g, *rest = name.split()
    s = rest[0] if rest else ""
    base = (g[0] + s[:2]).title()
    if base not in used:
        used.add(base)
        return base
    # fallback: add numeric suffix
    idx = 1
    while f"{base}{idx}" in used:
        idx += 1
    used.add(f"{base}{idx}")
    return f"{base}{idx}"


# ─── PDF scraping helper ────────────────────────────────────────────────────
def pdf_lookup(bot_name: str, page_hint: int | None) -> tuple[dict, int | None]:
    """
    Return a dict of scraped values + the page number found (1-based, may be None).
    Skips pages 21-22 (per user rule).
    """
    data = {k: None for k in FIELDS}
    found_page = None

    with pdfplumber.open(PDF_PATH) as pdf:
        # choose pages to inspect ------------------------------------------------
        if page_hint and 1 <= page_hint <= len(pdf.pages) and page_hint not in (21, 22):
            indices = [page_hint - 1]
        else:
            indices = [i for i in range(len(pdf.pages)) if i + 1 not in (21, 22)]

        # loop pages ------------------------------------------------------------
        for i in indices:
            page = pdf.pages[i]
            txt = page.extract_text() or ""
            if "Appearance:" not in txt:
                continue
            found_page = i + 1

            # process 'Appearance:' block line-by-line
            lines = txt.splitlines()
            start = next((j for j, l in enumerate(lines) if "Appearance:" in l), None)
            if start is None:
                continue

            for ln in lines[start + 1:]:
                ln = ln.strip("•–—- ").replace("–", "-")
                if not ln or re.match(r"^[A-Z][a-z]+:", ln):
                    break
                ll = ln.lower()

                if "height" in ll:
                    if m := re.search(r"height\s*[-–]\s*([\d.\- to]+)\s*ft", ll):
                        data["height"] = std_height_range(m.group(1))
                elif "spread" in ll:
                    if m := re.search(r"spread\s*[-–]\s*([\d.\- to]+)\s*ft", ll):
                        data["spread"] = std_height_range(m.group(1))
                elif "flower color" in ll:
                    if m := re.search(r"flower color\s*[-–]\s*(.+)", ln, flags=re.I):
                        data["color"] = std_color(m.group(1))
                elif "flowering period" in ll:
                    if m := re.search(r"flowering period\s*[-–]\s*(.+)", ln, flags=re.I):
                        data["bloom"] = std_bloom(m.group(1))

            # other fields in the full page ------------------------------------
            grabs = [
                ("sun",          r"Sun:\s*([^\n]+)", std_sun),
                ("water",        r"Water:\s*([^\n]+)", lambda x: x.strip()),
                ("wet",          r"Wetland Status:\s*([^\n]+)", lambda x: x.strip()),
                ("habitat",      r"Habitats?:\s*([^\n]+)", lambda x: x.strip()),
                ("char",         r"Characteristics?:\s*([^\n]+)", lambda x: x.strip()),
                ("wildlife",     r"(Attracts [^\n]+)", lambda x: x.strip().rstrip(".")),
                ("dist",         r"Distribution:\s*([^\n]+)", lambda x: x.strip()),
                ("type",         r"Type:\s*([^\n]+)", lambda x: x.strip()),
                ("planttype",    r"Plant Type:\s*([^\n]+)", lambda x: x.strip()),
            ]
            for key, pat, fn in grabs:
                if data[key]:
                    continue
                if m := re.search(pat, txt):
                    data[key] = fn(m.group(1))

            break  # stop after first relevant page

    return data, found_page


# ─── main routine ───────────────────────────────────────────────────────────
def main() -> None:
    df         = pd.read_csv(INPUT_CSV, dtype=str).fillna("")
    used_keys  = set()

    # ensure required columns exist ------------------------------------------
    for col in list(FIELDS.values()) + ["Page in PDF", "Key"]:
        if col not in df.columns:
            df[col] = ""

    # iterate plants ----------------------------------------------------------
    for idx in tqdm(df.index, desc="PDF scrape"):
        name      = df.at[idx, "Botanical Name"]
        page_hint = int(df.at[idx, "Page in PDF"]) if str(df.at[idx, "Page in PDF"]).isdigit() else None

        scraped, page = pdf_lookup(name, page_hint)

        for k, csv_col in FIELDS.items():
            if not df.at[idx, csv_col]:
                df.at[idx, csv_col] = scraped[k] or ""

        if not df.at[idx, "Page in PDF"]:
            df.at[idx, "Page in PDF"] = page or ""

        if not df.at[idx, "Key"]:
            df.at[idx, "Key"] = key_from_name(name, used_keys)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅  Done.  Output saved → {OUTPUT_CSV.name}")


if __name__ == "__main__":
    main()
