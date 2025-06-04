#!/usr/bin/env python3
# Launcher.py – CTk GUI for the plant-database tool-chain (2025-05-31, layout + prefix patch)

import sys, subprocess, threading, queue, customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime

# ─── Appearance ──────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

BASE = Path(__file__).resolve().parent
SCRIPTS = BASE / "Static/Python"
OUTDEF = BASE / "Static/Outputs"
TEMPL = BASE / "Static/Templates"
today = datetime.now().strftime("%Y%m%d")

# ─── Tool Config ─────────────────────────────────────────────────────────
TOOLS = [
    (
        "PDFScraper.py",
        "--in_pdf",
        "--out_csv",
        "Static/Templates/Plant Guide 2025 Update.pdf",
        "Plants_NeedLinks",
        ".csv",
    ),
    (
        "GetLinks.py",
        "--in_csv",
        "--out_csv",
        "Static/Outputs/Plants_NeedLinks.csv",
        "Plants_Linked",
        ".csv",
    ),
    (
        "FillMissingData.py",
        "--in_csv",
        "--out_csv",
        "Static/Outputs/Plants_Linked.csv",
        "Plants_Linked_Filled",
        ".csv",
    ),
    (
        "GeneratePDF.py",
        "--in_csv",
        "--out_pdf",
        "Static/Templates/Plants_Linked_Filled_Master.csv",
        "Plant_Guide_EXPORT",
        ".pdf",
    ),
    (
        "Excelify2.py",
        "--in_csv",
        "--out_xlsx",
        "Static/Templates/Plants_Linked_Filled_Master.csv",
        "Plants_Linked_Filled_Review",
        ".xlsx",
    ),
]

LABEL_OVERRIDES = {
    "PDFScraper.py": "Extract from PDF",
    "GetLinks.py": "Get Plant Links",
    "FillMissingData.py": "Fill Missing Data",
    "GeneratePDF.py": "Generate PDF",
    "Excelify2.py": "Export to Excel",
}


# ─── Utility ─────────────────────────────────────────────────────────────
def pretty(flag: str) -> str:
    return f"{'Input' if flag.startswith('--in_') else 'Output'} {flag.split('_',1)[1].upper()}"


def ftypes(flag: str):
    return (
        [("PDF", "*.pdf")] if "pdf" in flag else [("CSV", "*.csv"), ("Excel", "*.xlsx")]
    )


# ─── GUI ROOT ────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title("🌿 Plant Tool-chain Launcher")
app.geometry("860x760")

# ─── Global Vars ─────────────────────────────────────────────────────────
out_dir_var = ctk.StringVar(value=str(OUTDEF))
pre_var = ctk.StringVar(value=f"{today}_")
suf_var = ctk.StringVar(value="")
img_dir_var = ctk.StringVar(value=str(OUTDEF / "pdf_images"))
_img_user_set = False

log_q: queue.Queue[str] = queue.Queue(maxsize=500)
in_vars: dict[tuple[str, str], ctk.StringVar] = {}
status_lbl: dict[str, ctk.CTkLabel] = {}
out_widgets: list[tuple] = []

# ─── Top Controls ────────────────────────────────────────────────────────
hdr = ctk.CTkFrame(app)
hdr.pack(fill="x", padx=15, pady=10)


def refresh_out_labels():
    for _, lbl, stem, ext in out_widgets:
        lbl.configure(
            text=str(
                Path(out_dir_var.get()) / f"{pre_var.get()}{stem}{suf_var.get()}{ext}"
            )
        )


def browse_output():
    folder = filedialog.askdirectory(initialdir=out_dir_var.get())
    if folder:
        out_dir_var.set(folder)
        global _img_user_set
        if not _img_user_set:
            img_dir_var.set(str(Path(folder) / "pdf_images"))
        refresh_out_labels()


def browse_img():
    folder = filedialog.askdirectory(initialdir=img_dir_var.get())
    if folder:
        img_dir_var.set(folder)
        global _img_user_set
        _img_user_set = True


# Output folder
ctk.CTkLabel(hdr, text="Output folder:").grid(
    row=0, column=0, sticky="e", padx=4, pady=4
)
ctk.CTkEntry(hdr, textvariable=out_dir_var, width=430).grid(row=0, column=1, padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_output).grid(row=0, column=2)

# Prefix/Suffix row
name_box = ctk.CTkFrame(hdr)
name_box.grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4)
ctk.CTkLabel(name_box, text="File-name prefix:").pack(side="left", padx=(0, 4))
ctk.CTkEntry(name_box, textvariable=pre_var, width=120).pack(side="left", padx=(0, 12))
ctk.CTkLabel(name_box, text="File-name suffix:").pack(side="left", padx=(0, 4))
ctk.CTkEntry(name_box, textvariable=suf_var, width=120).pack(side="left")
pre_var.trace_add("write", lambda *a: refresh_out_labels())
suf_var.trace_add("write", lambda *a: refresh_out_labels())

# Image folder
ctk.CTkLabel(hdr, text="Image folder:").grid(
    row=2, column=0, sticky="e", padx=4, pady=4
)
ctk.CTkEntry(hdr, textvariable=img_dir_var, width=430).grid(row=2, column=1, padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_img).grid(row=2, column=2)

# ─── Tool Rows ───────────────────────────────────────────────────────────
body = ctk.CTkScrollableFrame(app, height=420)
body.pack(fill="both", padx=15, pady=6)


def choose_input(var: ctk.StringVar, flag: str):
    f = filedialog.askopenfilename(initialdir=TEMPL, filetypes=ftypes(flag))
    if f:
        var.set(f)


def run_tool(script, in_flag, out_flag, stem, ext):
    inp = in_vars[(script, in_flag)].get().strip()
    if not inp or not Path(inp).exists():
        status_lbl[script].configure(text="❌ input missing", text_color="red")
        return
    out_path = Path(out_dir_var.get()) / f"{pre_var.get()}{stem}{suf_var.get()}{ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(SCRIPTS / script), in_flag, inp, out_flag, str(out_path)]

    if script in {"GeneratePDF.py", "PDFScraper.py"}:
        cmd += ["--img_dir", img_dir_var.get()]
        if script == "PDFScraper.py":
            cmd += ["--map_csv", str(Path(img_dir_var.get()).parent / "image_map.csv")]

    def worker():
        lbl = status_lbl[script]
        lbl.configure(text="⏳ running…", text_color="yellow")
        log_q.put(f"\n\n▶ {' '.join(cmd)}\n")
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as p:
                for line in p.stdout:
                    log_q.put(line)
            lbl.configure(
                text="✅ finished" if p.returncode == 0 else "❌ error",
                text_color="green" if p.returncode == 0 else "red",
            )
        except Exception as e:
            lbl.configure(text="❌ exception", text_color="red")
            log_q.put(f"[launcher] {e}\n")

    threading.Thread(target=worker, daemon=True).start()


for script, in_flag, out_flag, def_in, stem, ext in TOOLS:
    fr = ctk.CTkFrame(body)
    fr.pack(fill="x", pady=6, padx=8)

    # Header row with script name and ▶ Run
    title_row = ctk.CTkFrame(fr)
    title_row.pack(fill="x", padx=12, pady=(4, 2))
    nice_name = LABEL_OVERRIDES.get(
        script, script.replace(".py", "").replace("_", " ").title()
    )
    ctk.CTkLabel(title_row, text=nice_name, font=("Arial", 14, "bold")).pack(
        side="left"
    )
    ctk.CTkButton(
        title_row,
        text="▶ Run",
        width=70,
        command=lambda s=script, i=in_flag, o=out_flag, st=stem, e=ext: run_tool(
            s, i, o, st, e
        ),
    ).pack(side="right", padx=4)

    # Input row
    in_row = ctk.CTkFrame(fr)
    in_row.pack(fill="x", padx=12, pady=2)
    ctk.CTkLabel(in_row, text=pretty(in_flag), width=120).pack(side="left")
    var = in_vars.setdefault((script, in_flag), ctk.StringVar(value=str(BASE / def_in)))
    ctk.CTkEntry(in_row, textvariable=var, width=380).pack(side="left", padx=4)
    ctk.CTkButton(
        in_row, text="Browse…", command=lambda v=var, f=in_flag: choose_input(v, f)
    ).pack(side="left")

    # Output row
    out_row = ctk.CTkFrame(fr)
    out_row.pack(fill="x", padx=12, pady=1)
    ctk.CTkLabel(out_row, text=pretty(out_flag), width=120).pack(side="left")
    out_lbl = ctk.CTkLabel(out_row, text="", text_color="#a6f4a6", anchor="w")
    out_lbl.pack(side="left", padx=4)
    out_widgets.append((script, out_lbl, stem, ext))

    status_lbl[script] = ctk.CTkLabel(out_row, text="")
    status_lbl[script].pack(side="right", padx=4)

# ─── Console Output ──────────────────────────────────────────────────────
console = ctk.CTkTextbox(app, height=180, wrap="none")
console.pack(fill="both", padx=15, pady=8)
scr = ctk.CTkScrollbar(app, command=console.yview)
scr.place(relx=0.97, rely=0.74, relheight=0.24)
console.configure(yscrollcommand=scr.set)


def feed_console():
    while True:
        line = log_q.get()
        if "CropBox missing from /Page" in line:
            continue  # Suppress PyMuPDF warning
        console.insert("end", line)
        console.see("end")


threading.Thread(target=feed_console, daemon=True).start()

# ─── Initial Load ────────────────────────────────────────────────────────
refresh_out_labels()
app.mainloop()
