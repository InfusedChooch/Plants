# plants/FillwithLinks.py
# Scrapes MBG + Wildflower.org to complete missing fields,
# then writes Plants_COMPLETE.csv in the final 17-column order.

from __future__ import annotations
import re, csv, time
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── paths ─────────────────────────────────────────────────────────────────
BASE         = Path(__file__).resolve().parent
IN_CSV       = BASE / "Plants_FROM_PDF_ONLY.csv"
MASTER_CSV   = BASE / "Plants and Links.csv"      # desired column template
OUT_CSV      = BASE / "Plants_COMPLETE.csv"

# ─── scraping settings ────────────────────────────────────────────────────
UA            = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
TIMEOUT       = 30
SLEEP_BETWEEN = 1.2

# ─── shared helpers ───────────────────────────────────────────────────────
PLANT_TYPES = {
    "Herbaceous Perennials", "Ferns", "Grasses", "Sedges", "Rushes",
    "Shrubs", "Trees", "Grasses, Sedges, and Rushes"
}

def strip_types(txt: Optional[str]) -> Optional[str]:
    if not txt: return None
    for t in PLANT_TYPES:
        txt = re.sub(rf"\b{re.escape(t)}\b", "", txt, flags=re.I)
    return re.sub(r"\s{2,}"," ",txt).strip(",; ").strip()

def ws(val: Optional[str]) -> Optional[str]:
    return re.sub(r"\s+"," ",val.strip()) if isinstance(val,str) else None

def _fmt(n:str)->str:
    try:
        f=float(n); return str(int(f)) if f.is_integer() else str(f).rstrip("0").rstrip(".")
    except: return n.strip()

def rng(txt:Optional[str])->Optional[str]:
    if not txt: return None
    txt=re.sub(r"\b(feet|foot|ft\.?|')\b","",txt,flags=re.I).replace("–"," to ")
    nums=[m.group() for m in re.finditer(r"[\d.]+",txt)]
    return f"{_fmt(nums[0])} - {_fmt(nums[1])}" if len(nums)>=2 else _fmt(nums[0]) if nums else ws(txt)

def month_rng(txt:Optional[str])->Optional[str]:
    if not txt: return None
    return ws(re.sub(r"\s*(to|–)\s*"," - ",txt.title()))

def conditions(txt:Optional[str])->Optional[str]:
    if not txt: return None
    txt=txt.lower().replace(" to ",",").replace(" and ",",").replace(" or ",",").replace("; ",",")
    parts=[p.strip() for p in txt.split(",") if p.strip()]
    seen:list[str]=[]
    [seen.append(p) for p in parts if p not in seen]
    return ", ".join(p.capitalize() for p in seen)

def fetch(url:str)->str|None:
    try:
        r=requests.get(url,headers={"User-Agent":UA},timeout=TIMEOUT)
        r.raise_for_status(); return r.text
    except Exception as e:
        print(f"⚠️  {url} → {e}"); return None

def grab(txt:str,label:str)->Optional[str]:
    m=re.search(fr"(?:{label}):?\s*(.+)",txt,flags=re.I)
    return ws(m.group(1).split("\n",1)[0]) if m else None

# ─── site parsers ─────────────────────────────────────────────────────────
def parse_mbg(html:str)->Dict[str,Optional[str]]:
    soup=BeautifulSoup(html,"lxml"); text=soup.get_text("\n",strip=True)
    return {
        "Height (ft)"     : rng(grab(text,"Height")),
        "Spread (ft)"     : rng(grab(text,"Spread")),
        "Bloom Color"     : grab(text,"Bloom Description"),
        "Bloom Time"      : month_rng(grab(text,"Bloom Time")),
        "Sun"             : conditions(grab(text,"Sun")),
        "Water"           : conditions(grab(text,"Water")),
        "Wetland Status"  : grab(text,"Wetland Status"),
        "Habitats"        : grab(text,"Habitats?"),
        "Characteristics" : strip_types(grab(text,"Characteristics?")),
        "Wildlife Benefits":grab(text,"Attracts"),
        "Distribution"    : grab(text,"Native Range|Distribution"),
        "Plant Type"      : grab(text,"Type"),   # stays if wanted
        "Type"            : grab(text,"Type"),
    }

def parse_wf(html:str)->Dict[str,Optional[str]]:
    soup=BeautifulSoup(html,"lxml"); text=soup.get_text("\n",strip=True)
    return {
        "Height (ft)"     : rng(grab(text,"Height")),
        "Spread (ft)"     : rng(grab(text,"Spread")),
        "Bloom Color"     : grab(text,"Bloom Color"),
        "Bloom Time"      : month_rng(grab(text,"Bloom Time")),
        "Sun"             : conditions(grab(text,"Sun")),
        "Water"           : conditions(grab(text,"Moisture")),
        "Distribution"    : grab(text,"USDA Native Status|Distribution"),
        "Wildlife Benefits":grab(text,"Attracts"),
    }

# ─── main workflow ────────────────────────────────────────────────────────
def main()->None:
    df=pd.read_csv(IN_CSV,dtype=str).fillna("")
    for idx,row in tqdm(df.iterrows(),total=len(df),desc="Website Fill"):
        # MBG pass ----------------------------------------------------------
        mbg=row.get("Link: Missouri Botanical Garden","").strip()
        if mbg.startswith("http"):
            if html:=fetch(mbg):
                for k,v in parse_mbg(html).items():
                    if v and not row.get(k): df.at[idx,k]=v
            time.sleep(SLEEP_BETWEEN)

        # Wildflower pass ---------------------------------------------------
        wf=row.get("Link: Wildflower.org","").strip()
        if wf.startswith("http"):
            if html:=fetch(wf):
                for k,v in parse_wf(html).items():
                    if v and not row.get(k): df.at[idx,k]=v
            time.sleep(SLEEP_BETWEEN)

    # order / trim columns --------------------------------------------------
    template=list(pd.read_csv(MASTER_CSV,nrows=0).columns)
    extra=[c for c in df.columns if c not in template]
    df=df[template+extra]   # preserves required 17 columns first

    df.to_csv(OUT_CSV,index=False,quoting=csv.QUOTE_MINIMAL)
    print(f"✅  Saved → {OUT_CSV.name}")

if __name__=="__main__":
    main()
