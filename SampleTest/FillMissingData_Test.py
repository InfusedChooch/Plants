#!/usr/bin/env python3
# FillMissingData.py – robust website-filler for the RU Plant Guide
# 2025-06-11 (patched with helpers restored)

from __future__ import annotations
import argparse, csv, re, sys, time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ------------------------------------------------------------------------
#  HTML-cache helper (create SampleTest/html_cache on first run)
# ------------------------------------------------------------------------
from urllib.parse import urlparse
import hashlib, re, os


# ───────────────────────────── CLI ────────────────────────────────────────
def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fill missing plant-guide fields from MBG, Wildflower.org "
        "and nursery sites."
    )
    p.add_argument("--in_csv",  default="Plants_Linked.csv")           # forward slash not needed
    p.add_argument("--out_csv", default="Plants_Linked_Filled_Test.csv")

    p.add_argument(
        "--master_csv",
        default="Templates/0610_Masterlist_New_Beta_Nodata.csv",
        help="Column template that defines final header order",
    )
    # optional helper: diff two CSVs
    p.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"), help="show CSV diff")
    return p.parse_args(argv)


ARGS = parse_cli()


# ─────────────── repo / bundle path helpers (+ icon finder) ───────────────
def repo_dir() -> Path:
    """
    Return project root whether running from source or a PyInstaller bundle:
        • source tree …/Templates, …/Outputs present
        • frozen exe  …/_internal/helpers/<tool>.exe  → go up three
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        if exe.parent.name.lower() == "helpers" and exe.parent.parent.name == "_internal":
            return exe.parent.parent.parent
        return exe.parent
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Templates").is_dir() and (parent / "Outputs").is_dir():
            return parent
    return here.parent


REPO = repo_dir()


def repo_path(p: str | Path) -> Path:
    """Resolve Outputs/… or Templates/… against repo root unless absolute."""
    p = Path(p).expanduser()
    if p.is_absolute():
        return p
    if p.parts and p.parts[0].lower() in {"outputs", "templates", "_internal"}:
        return (REPO / p).resolve()
    return (Path(__file__).resolve().parent / p).resolve()


def get_resource(rel: str | Path) -> Path:
    """
    Return absolute path to bundled resource (e.g. Static/themes/leaf.ico)
    that works both frozen (sys._MEIPASS) and from source.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / rel
    return REPO / rel


# cache lives next to the test CSVs →  <repo>/SampleTest/html_cache
CACHE_DIR = (REPO / "SampleTest" / "html_cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_name(url: str) -> Path:
    """
    Turn any URL into a safe, unique filename:
        '<domain>_<path>_<12-char-sha1>.html'
    The hash guarantees uniqueness; the slugged domain/path is only
    there to keep things human-readable when you peek in the folder.
    """
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{parsed.netloc}_{parsed.path}").strip("_")
    slug = slug[:80]  # keep filenames reasonably short for Windows
    return CACHE_DIR / f"{slug}_{h}.html"




# ───────────────────── CSV diff helper (optional) ─────────────────────────
def csv_diff(old_csv: Path, new_csv: Path) -> None:
    a = pd.read_csv(old_csv, dtype=str).fillna("")
    b = pd.read_csv(new_csv, dtype=str).fillna("")
    if a.shape != b.shape:
        print(f"[!] shape changed: {a.shape} → {b.shape}")
    mask = (a != b).any(axis=1)
    if not mask.any():
        print("No cell-level differences found.")
        return
    for idx in a[mask].index:
        for col in a.columns:
            if a.at[idx, col] != b.at[idx, col]:
                print(
                    f"row {idx:>4}  {col}: "
                    f"'{a.at[idx, col]}'  →  '{b.at[idx, col]}'"
                )
    print("Diff complete.")


# ──────────────────────────── constants ───────────────────────────────────
SLEEP = 0.7  # delay between HTTP requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
HEADERS_ALT = HEADERS | {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

MBG_COLS = {
    "Height (ft)",
    "Spread (ft)",
    "Sun",
    "Water",
    "Tolerates",
    "Maintenance",
    "Attracts",
    "Zone",
    "Culture",
    "Uses",
    "Problems",
}
WF_COLS = {
    "Height (ft)",
    "Spread (ft)",
    "Bloom Color",
    "Bloom Time",
    "Soil Description",
    "Condition Comments",
    "AGCP Regional Status",
    "Native Habitats",
    "Sun",
    "Water",
    "Attracts",
    "UseXYZ",
    "Propagation:Maintenance",
}
PR_COLS = {"Tolerates", "Attracts"}
NM_COLS = {"Sun", "Water", "Bloom Color", "Height (ft)", "Tolerates"}
PN_COLS = {
    "Bloom Color",
    "Bloom Time",
    "Height (ft)",
    "Spread (ft)",
    "Attracts",
    "Tolerates",
}

# Columns where data from multiple sources should be combined
ADDITIVE_COLS = {
    "Attracts",
    "Tolerates",
    "UseXYZ",
    "Propagation:Maintenance",
}


# ────────────────────── generic text helpers ──────────────────────────────
def missing(v: str | None) -> bool:
    return not str(v or "").strip()


def rng(s: str | None) -> str | None:
    """“1–3 ft” → “1 - 3” (or None)."""
    if not s:
        return None
    nums = re.findall(r"[\d.]+", s)
    nums = [str(int(float(n))) if float(n).is_integer() else n for n in nums]
    return " - ".join(nums) if nums else None


def csv_join(parts: list[str]) -> str | None:
    out: list[str] = []
    for p in parts:
        if p and p not in out:
            out.append(p)
    return ", ".join(out) if out else None


def merge_field(a: str | None, b: str | None) -> str | None:
    return csv_join(
        [*(re.split(r"[|,]", a) if a else []), *(re.split(r"[|,]", b) if b else [])]
    )


# ───────────────────── HTTP fetch helper ──────────────────────────────────
# ------------------------------------------------------------------------
#  Cached fetch()
# ------------------------------------------------------------------------
def fetch(url: str) -> str | None:
    """
    1. Look for <CACHE_DIR>/<slug>.html → return its contents if found.
    2. Otherwise hit the network, save a copy to the cache, and return it.
       If the request fails, return None (previous behaviour).
    """
    cache_file = _cache_name(url)

    # ---------- 1. serve from cache if we already have it ---------------
    if cache_file.exists():
        try:
            return cache_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass  # corrupted file? fall back to network

    # ---------- 2. otherwise, fetch & store -----------------------------
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 403:
            r = requests.get(url, headers=HEADERS_ALT, timeout=12)
        if r.ok:
            # save a copy for next time (ignore failures silently)
            try:
                cache_file.write_text(r.text, encoding="utf-8")
            except Exception:
                pass
            return r.text
    except requests.RequestException:
        pass

    return None


# ───────────────────────────── parsers ────────────────────────────────────
def _grab(text: str, label: str) -> str:
    m = re.search(
        rf"{re.escape(label)}\s*[:\-\u2013\u2014]?\s*([^\n]+)",
        text,
        flags=re.I,
    )
    return m.group(1).strip() if m else ""


def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text("\n", strip=True)
    return {
        "Height (ft)": rng(_grab(txt, "Height")),
        "Spread (ft)": rng(_grab(txt, "Spread")),
        "Sun": _grab(txt, "Sun"),
        "Water": _grab(txt, "Water"),
        "Tolerates": _grab(txt, "Tolerate"),
        "Maintenance": _grab(txt, "Maintenance"),
        "Attracts": _grab(txt, "Attracts"),
        "Culture": _grab(txt, "Culture") or _grab(txt, "Growing Tips"),
        "Uses": _grab(txt, "Uses"),
        "Problems": _grab(txt, "Problems"),
        "Zone": (
            f"USDA Hardiness Zone {_grab(txt, 'Zone')}"
            if _grab(txt, "Zone")
            else None
        ),
    }


# Wildflower helpers
def _section_text(soup: BeautifulSoup, hdr: str) -> str:
    h = soup.find(
        lambda t: t.name in ("h2", "h3", "h4")
        and hdr.lower() in t.get_text(strip=True).lower()
    )
    if not h:
        return ""
    out = []
    for sib in h.find_next_siblings():
        if sib.name in ("h2", "h3", "h4"):
            break
        out.append(sib.get_text("\n", strip=True))
    return "\n".join(out).strip()


def _wf_wetland(soup: BeautifulSoup, region: str = "AGCP") -> Optional[str]:
    h = soup.find("h4", string=lambda x: x and "wetland indicator" in x.lower())
    if not h:
        return None
    tbl = h.find_next("table")
    if not tbl:
        return None
    rows = tbl.find_all("tr")
    if len(rows) < 2:
        return None
    hdrs = [td.get_text(strip=True) for td in rows[0].find_all("td")]
    vals = [td.get_text(strip=True) for td in rows[1].find_all("td")]
    if hdrs and hdrs[0].lower().startswith("region"):
        hdrs = hdrs[1:]
    if vals and vals[0].lower().startswith("status"):
        vals = vals[1:]
    return {h: v for h, v in zip(hdrs, vals)}.get(region)

# --- text normalisation helpers ------------------------------------------
def clean(text: str | None) -> str | None:
    """Collapse multiple spaces, strip, and standard-ise punctuation."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)          # squeeze spaces/newlines
    text = text.replace(" ,", ",").strip(" ,")
    return text.strip()

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# normalisation map for common phrasing tweaks
NORMALISE = {
    "full sun to part shade": "Full Sun, Part Shade",
    "dry to medium": "dry, medium",
}

def month_list(raw: str | None) -> str | None:
    """
    Convert any 'Apr-May' · 'April to May' · 'Apr through Jun'
    → 'Apr, May' (plus extra months when range > 2).
    """
    if not raw:
        return None
    s = raw.title().replace("Through", "to").replace("–", "-")
    s = re.sub(r"\bto\b", "-", s)
    rng = re.split(r"[\s,/]+", s)
    if "-" in rng[0]:
        rng = [*rng[0].split("-")]
    if len(rng) == 2 and all(m[:3] in MONTHS for m in rng):
        a, b = MONTHS.index(rng[0][:3]), MONTHS.index(rng[1][:3])
        if a <= b:
            return ", ".join(MONTHS[a : b + 1])
    return ", ".join({m[:3] for m in rng if m[:3] in MONTHS})



def parse_wf(html: str, want_fallback_sun_water=False) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text("\n", strip=True)

    # Plant-characteristics table
    char: dict[str, str] = {}
    h = soup.find(
        lambda t: t.name in ("h2", "h3", "h4")
        and "plant characteristics" in t.get_text(strip=True).lower()
    )
    if h and (tbl := h.find_next("table")):
        for row in tbl.select("tr"):
            tds = [td.get_text(" ", strip=True) for td in row.select("td")]
            if len(tds) >= 2:
                char[tds[0].rstrip(":")] = tds[1]

    # Benefits → UseXYZ
    uses = []
    for li in soup.select("li"):
        strong = li.find(["strong", "b"])
        if not strong:
            continue
        head = strong.get_text(strip=True)
        if head.lower().startswith("use"):
            cat = head.replace("Use", "").replace(":", "").strip()
            body = li.get_text(" ", strip=True).replace(head, "").lstrip(":–—- ").strip()
            uses.append(f"{cat}: {body}")
    usexyz = csv_join(uses)

    # Propagation:Maintenance
    maint = None
    for li in soup.select("li"):
        strong = li.find(["strong", "b"])
        if strong and "maintenance" in strong.get_text(strip=True).lower():
            maint = li.get_text(" ", strip=True).split(":", 1)[-1].strip()
            break

    data = {
        "Height (ft)": rng(char.get("Height")),
        "Spread (ft)": rng(char.get("Spread")),
        "Bloom Color": clean(char.get("Bloom Color")),
        "Bloom Time": month_list(char.get("Bloom Time") or char.get("Bloom Period")),
        "Soil Description": clean(_section_text(soup, "Soil Description")),
        "Condition Comments": clean(_section_text(soup, "Comment")),  # works for Comment / Comments
        "Native Habitats": clean(char.get("Native Habitat") or char.get("Habitat")),
        "AGCP Regional Status": _wf_wetland(soup),
        "UseXYZ": usexyz and clean(usexyz),
        "Propagation:Maintenance": clean(maint),
        "Attracts": clean(char.get("Benefit")),
    }

    if want_fallback_sun_water:
        data["Sun"] = char.get("Light Requirement")
        data["Water"] = char.get("Soil Moisture")

    return {k: v for k, v in data.items() if v}

def parse_mbg(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")

    # helper: return concatenated <p> text that follows an <h3>/<h4> header
    def section(lbl: str) -> str:
        h = soup.find(lambda t: t.name in ("h3", "h4") and lbl.lower() in t.get_text(strip=True).lower())
        if not h:
            return ""
        out = []
        for sib in h.find_next_siblings():
            if sib.name in ("h3", "h4"):
                break
            if sib.name == "p":
                out.append(sib.get_text(" ", strip=True))
        return clean(" ".join(out))

    # key/value table at top of page
    plain = soup.get_text("\n", strip=True)
    def grab(label: str) -> str:  # first line only (for numeric stuff)
        m = re.search(rf"{re.escape(label)}\s*[:\-\u2013\u2014]?\s*(.+?)(?:\n|$)", plain, flags=re.I)
        return clean(m.group(1)) if m else ""

    return {
        "Height (ft)": rng(grab("Height")),
        "Spread (ft)": rng(grab("Spread")),
        "Sun": clean(grab("Sun")),
        "Water": clean(grab("Water")),
        "Tolerates": clean(grab("Tolerate")),
        "Maintenance": clean(grab("Maintenance")),
        "Attracts": clean(grab("Attracts")),
        "Culture": section("Culture") or section("Growing Tips"),
        "Uses": section("Uses"),
        "Problems": section("Problems"),
        "Zone": (
            f"USDA Hardiness Zone {grab('Zone')}" if grab("Zone") else None
        ),
    }


def parse_pr(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")

    def collect(title: str) -> Optional[str]:
        h = soup.find("h5", string=lambda x: x and title.lower() in x.lower())
        if not h:
            return None
        box = h.find_parent("div")
        if not box:
            return None
        vals = [a.get_text(strip=True) for a in box.select("a")]
        vals = [re.sub(r"^Attracts\s+", "", v) for v in vals]
        return csv_join(vals)

    return {"Attracts": collect("Attracts Wildlife"), "Tolerates": collect("Tolerance")}


def parse_nm(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text("\n", strip=True)
    flat = txt.replace("\n", " ")

    def lbl(l: str) -> Optional[str]:
        m = re.search(rf"{l}\s*:?\s*([^\n]+)", txt, flags=re.I)
        return m.group(1).strip() if m else None

    data = {
        "Sun": lbl("Exposure"),
        "Water": lbl("Soil Moisture Preference"),
        "Bloom Color": lbl("Bloom Colors"),
    }
    if m := re.search(r"Height\s*:\s*([\d\s\-]+)\s*ft", flat, flags=re.I):
        data["Height (ft)"] = rng(m.group(1))

    tol = []
    if s := lbl("Salt Tolerance"):
        tol.append(f"Salt Tolerance: {s}")
    if (j := lbl("Juglans nigra")) and j.lower().startswith("yes"):
        tol.append("Black Walnut Tolerant")
    if tol:
        data["Tolerates"] = csv_join(tol)

    return {k: v for k, v in data.items() if v}


def parse_pn(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    info = {
        i.find("span").get_text(strip=True): i.find("p").get_text(strip=True)
        for i in soup.select("div.item")
        if i.find("span") and i.find("p")
    }
    data = {
        "Bloom Color": info.get("Bloom Color"),
        "Bloom Time": info.get("Bloom Period"),
        "Height (ft)": rng(info.get("Max Mature Height") or info.get("Height")),
        "Spread (ft)": rng(info.get("Spread")),
    }
    if info.get("Pollinator Attributes"):
        data["Attracts"] = info["Pollinator Attributes"]
    if info.get("Deer Resistant", "").lower() == "yes":
        data["Tolerates"] = merge_field(data.get("Tolerates"), "Deer")
    return {k: v for k, v in data.items() if v}


# ──────────────────────────── main routine ────────────────────────────────
def fill_csv(in_csv: Path, out_csv: Path, master_csv: Path) -> None:
    df = pd.read_csv(in_csv, dtype=str).fillna("")

    # normalise link column names up front
    df.rename(
        columns={
            "Link: Missouri Botanical Garden": "MBG Link",
            "Link: Wildflower.org": "WF Link",
            "Link: Pleasantrunnursery.com": "PR Link",
            "Link: Newmoonnursery.com": "NM Link",
            "Link: Pinelandsnursery.com": "PN Link",
            "Distribution": "Distribution Zone",
            "Distribution Zone": "Distribution Zone",
        },
        inplace=True,
    )

    # guarantee every header we might write exists → prevents KeyError
    for col in MBG_COLS | WF_COLS | PR_COLS | NM_COLS | PN_COLS:
        if col not in df.columns:
            df[col] = ""

    # make sure Key column exists
    if "Key" not in df.columns:
        df["Key"] = ""

    # ---------- scrape loop ------------------------------------------------
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Fill"):
        # MBG --------------------------------------------------------------
        if any(missing(row[c]) for c in MBG_COLS):
            url = row.get("MBG Link", "").strip()
            if url.startswith("http") and (html := fetch(url)):
                for k, v in parse_mbg(html).items():
                    if k in ADDITIVE_COLS:
                        df.at[idx, k] = merge_field(df.at[idx, k], v)
                    elif missing(df.at[idx, k]):
                        df.at[idx, k] = v
                time.sleep(SLEEP)

        # Wildflower -------------------------------------------------------
        row = df.loc[idx]
        if any(missing(row[c]) for c in WF_COLS):
            url = row.get("WF Link", "").strip()
            if url.startswith("http") and (html := fetch(url)):
                wf_data = parse_wf(html, want_fallback_sun_water=missing(row["Sun"]))
                for k, v in wf_data.items():
                    if k in ADDITIVE_COLS:
                        df.at[idx, k] = merge_field(df.at[idx, k], v)
                    elif missing(df.at[idx, k]):
                        df.at[idx, k] = v
                time.sleep(SLEEP)

        # Pleasant Run -----------------------------------------------------
        row = df.loc[idx]
        if any(missing(row[c]) for c in PR_COLS):
            url = row.get("PR Link", "").strip()
            if url.startswith("http") and (html := fetch(url)):
                for k, v in parse_pr(html).items():
                    if k in ADDITIVE_COLS:
                        df.at[idx, k] = merge_field(df.at[idx, k], v)
                    elif missing(df.at[idx, k]):
                        df.at[idx, k] = v
                time.sleep(SLEEP)

        # New Moon ---------------------------------------------------------
        row = df.loc[idx]
        if any(missing(row[c]) for c in NM_COLS):
            url = row.get("NM Link", "").strip()
            if url.startswith("http") and (html := fetch(url)):
                for k, v in parse_nm(html).items():
                    if k in ADDITIVE_COLS:
                        df.at[idx, k] = merge_field(df.at[idx, k], v)
                    elif missing(df.at[idx, k]):
                        df.at[idx, k] = v
                time.sleep(SLEEP)

        # Pinelands --------------------------------------------------------
        row = df.loc[idx]
        if any(missing(row[c]) for c in PN_COLS):
            url = row.get("PN Link", "").strip()
            if url.startswith("http") and (html := fetch(url)):
                for k, v in parse_pn(html).items():
                    if k in ADDITIVE_COLS:
                        df.at[idx, k] = merge_field(df.at[idx, k], v)
                    elif missing(df.at[idx, k]):
                        df.at[idx, k] = v
                time.sleep(SLEEP)

                        # --- post-merge cleanup on additive fields -----------------------
        df.at[idx, "Sun"] = clean(df.at[idx, "Sun"])
        df.at[idx, "Water"] = clean(df.at[idx, "Water"]).lower() if df.at[idx, "Water"] else ""
        df.at[idx, "Tolerates"] = clean(df.at[idx, "Tolerates"])
        df.at[idx, "Soil Description"] = clean(df.at[idx, "Soil Description"])
        df.at[idx, "Bloom Time"] = month_list(df.at[idx, "Bloom Time"])


    # finalise Distribution Zone
    if "Zone" in df.columns:
        if "Distribution Zone" in df.columns:
            df["Distribution Zone"] = df["Distribution Zone"].where(
                df["Distribution Zone"].astype(bool), df["Zone"]
            )
        else:
            df.rename(columns={"Zone": "Distribution Zone"}, inplace=True)
        if "Zone" in df.columns:
            df.drop(columns=["Zone"], inplace=True)

    # restore original link column names
    df.rename(
        columns={
            "MBG Link": "Link: Missouri Botanical Garden",
            "WF Link": "Link: Wildflower.org",
            "PR Link": "Link: Pleasantrunnursery.com",
            "NM Link": "Link: Newmoonnursery.com",
            "PN Link": "Link: Pinelandsnursery.com",
        },
        inplace=True,
    )

    # reorder to master template
    template_cols = list(pd.read_csv(master_csv, nrows=0).columns)
    for col in template_cols:
        if col not in df.columns:
            df[col] = ""
    df = df.loc[:, [c for c in template_cols if c in df.columns]]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, quoting=csv.QUOTE_MINIMAL, na_rep="")
    print(f"[OK] saved → {out_csv.relative_to(REPO)}")


# ────────────────────────── entrypoint ────────────────────────────────────
if __name__ == "__main__":
    if ARGS.diff:
        csv_diff(repo_path(ARGS.diff[0]), repo_path(ARGS.diff[1]))
        sys.exit()

    fill_csv(
        repo_path(ARGS.in_csv),
        repo_path(ARGS.out_csv),
        repo_path(ARGS.master_csv),
    )
