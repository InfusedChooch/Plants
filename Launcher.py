#!/usr/bin/env python3
# Launcher.py – CTk GUI for the plant-database tool-chain
# 2025-06-09  Fix console spacing + auto-update input paths when output folder changes

import sys, subprocess, threading, queue, customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime
import webbrowser

# ─── Locate bundle root ──────────────────────────────────────────────────
def repo_dir() -> Path:
    """Return application root whether running from source or PyInstaller."""
    if getattr(sys, "frozen", False):                       # one-dir build
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent                  # source checkout


REPO     = repo_dir()
HELPERS  = REPO / "helpers"
STATIC   = REPO / "Static"          # themes & Python helpers
SCRIPTS  = STATIC / "Python"
TEMPL    = REPO / "Templates"
OUTDEF   = REPO / "Outputs"
OUTDEF.mkdir(exist_ok=True)

# ─── Appearance ──────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(str(STATIC / "themes" / "rutgers.json"))

# ─── Tool definitions (script, in-flag, out-flag, default-IN, stem, ext) ─
TOOLS = [
    ("PDFScraper.py",     "--in_pdf",  "--out_csv", "Templates/Plant Guide 2025 Update.pdf", "Plants_NeedLinks",                ".csv"),
    ("GetLinks.py",       "--in_csv",  "--out_csv", "Outputs/Plants_NeedLinks.csv",            "Plants_Linked",                  ".csv"),
    ("FillMissingData.py","--in_csv",  "--out_csv", "Outputs/Plants_Linked.csv",               "Plants_Linked_Filled",           ".csv"),
    ("GeneratePDF.py",    "--in_csv",  "--out_pdf", "Outputs/Plants_Linked_Filled.csv",        "Plant_Guide_EXPORT",             ".pdf"),
    ("Excelify2.py",      "--in_csv",  "--out_xlsx","Outputs/Plants_Linked_Filled.csv",        "Plants_Linked_Filled_Review",    ".xlsx"),
]

TAB_MAP = {
    "PDFScraper.py": "builder",
    "GetLinks.py": "builder",
    "FillMissingData.py": "builder",
    "GeneratePDF.py": "export",
    "Excelify2.py": "export",
}
LABEL_OVERRIDES = {
    "PDFScraper.py": "Extract from PDF",
    "GetLinks.py": "Get Plant Links",
    "FillMissingData.py": "Fill Missing Data",
    "GeneratePDF.py": "Generate PDF",
    "Excelify2.py": "Export to Excel",
}

# ─── Utility helpers ─────────────────────────────────────────────────────
def pretty(flag: str) -> str:
    return f"{'Input' if flag.startswith('--in_') else 'Output'} {flag.split('_',1)[1].upper()}"

def ftypes(flag: str):
    return [("PDF", "*.pdf")] if "pdf" in flag else [("CSV", "*.csv"), ("Excel", "*.xlsx")]

# ─── GUI ROOT ────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title(" Rutgers Plant Launcher")
app.geometry("860x760")

# ─── Global state vars ───────────────────────────────────────────────────
today          = datetime.now().strftime("%Y%m%d")
out_dir_var    = ctk.StringVar(value=str(OUTDEF))
pre_var        = ctk.StringVar(value=f"{today}_")
suf_var        = ctk.StringVar(value="")
img_dir_var    = ctk.StringVar(value=str(OUTDEF / "pdf_images"))
guide_pdf_var  = ctk.StringVar(value=str(TEMPL / "Plant Guide 2025 Update.pdf"))
master_csv_var = ctk.StringVar(value=str(TEMPL / "Plants_Linked_Filled_Master.csv"))
_img_user_set  = False
_prev_out_dir  = out_dir_var.get()   # track last output dir for path-rewrite

log_q          : queue.Queue[str]            = queue.Queue(maxsize=800)
in_vars        : dict[tuple[str,str],ctk.StringVar] = {}
status_lbl     : dict[str,ctk.CTkLabel]      = {}
out_widgets    : list[tuple]                 = []

# ─── Top controls (folder / prefix / master paths) ───────────────────────
hdr = ctk.CTkFrame(app)
hdr.pack(fill="x", padx=15, pady=10)

def refresh_out_labels() -> None:
    """Update all *output* path previews."""
    for _, lbl, stem, ext in out_widgets:
        lbl.configure(
            text=str(Path(out_dir_var.get()) / f"{pre_var.get()}{stem}{suf_var.get()}{ext}")
        )

def _rewrite_inputs_for_new_folder(new_folder: str) -> None:
    """Whenever the output folder changes, rewrite any INPUT path that
    still lives in the old folder so it follows along automatically."""
    global _prev_out_dir
    for (script, flag), var in in_vars.items():
        cur = Path(var.get())
        if cur.is_absolute() and str(cur).startswith(_prev_out_dir):
            # Keep the filename part (incl. prefix/suffix) but move under new_folder
            var.set(str(Path(new_folder) / cur.name))
    _prev_out_dir = new_folder

def browse_output() -> None:
    folder = filedialog.askdirectory(initialdir=out_dir_var.get())
    if folder:
        out_dir_var.set(folder)
        _rewrite_inputs_for_new_folder(folder)
        global _img_user_set
        if not _img_user_set:
            img_dir_var.set(str(Path(folder) / "pdf_images"))
        refresh_out_labels()

def browse_img() -> None:
    folder = filedialog.askdirectory(initialdir=img_dir_var.get())
    if folder:
        img_dir_var.set(folder)
        global _img_user_set
        _img_user_set = True

def browse_pdf() -> None:
    f = filedialog.askopenfilename(initialdir=Path(guide_pdf_var.get()).parent, filetypes=[("PDF","*.pdf")])
    if f: guide_pdf_var.set(f)

def browse_master() -> None:
    f = filedialog.askopenfilename(initialdir=Path(master_csv_var.get()).parent, filetypes=[("CSV","*.csv")])
    if f: master_csv_var.set(f)

def open_chrome_portable() -> None:
    webbrowser.open("https://portableapps.com/apps/internet/google_chrome_portable", new=1)

# Output folder row
ctk.CTkLabel(hdr, text="Output folder:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
ctk.CTkEntry(hdr, textvariable=out_dir_var, width=430).grid(row=0, column=1, padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_output).grid(row=0, column=2)

# Prefix / suffix
name_box = ctk.CTkFrame(hdr)
name_box.grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4)
ctk.CTkLabel(name_box, text="File-name prefix:").pack(side="left", padx=(0,4))
ctk.CTkEntry(name_box, textvariable=pre_var, width=120).pack(side="left", padx=(0,12))
ctk.CTkLabel(name_box, text="File-name suffix:").pack(side="left", padx=(0,4))
ctk.CTkEntry(name_box, textvariable=suf_var, width=120).pack(side="left")
for v in (pre_var, suf_var):
    v.trace_add("write", lambda *_: refresh_out_labels())

# Image dir / guide PDF / master CSV rows
for r, (label, var, cmd) in enumerate(
    [("Image folder:", img_dir_var, browse_img),
     ("Guide PDF:",    guide_pdf_var, browse_pdf),
     ("Master CSV:",   master_csv_var, browse_master)],
    start=2
):
    ctk.CTkLabel(hdr, text=label).grid(row=r, column=0, sticky="e", padx=4, pady=4)
    ctk.CTkEntry(hdr, textvariable=var, width=430).grid(row=r, column=1, padx=4)
    ctk.CTkButton(hdr, text="Browse", command=cmd).grid(row=r, column=2)

# Chrome portable helper
ctk.CTkButton(hdr, text="Get Chrome Portable", width=160, command=open_chrome_portable).grid(
    row=5, column=1, sticky="w", padx=4, pady=4
)

# ─── Tabs & tool rows ────────────────────────────────────────────────────
tabs        = ctk.CTkTabview(app)
export_tab  = tabs.add("Export")
builder_tab = tabs.add("Builder")

tabs.pack(fill="both", padx=15, pady=(0,6), expand=True)

b_body = ctk.CTkScrollableFrame(builder_tab, height=420) ; b_body.pack(fill="both", expand=True)
e_body = ctk.CTkScrollableFrame(export_tab,  height=420) ; e_body.pack(fill="both", expand=True)

def choose_input(var: ctk.StringVar, flag: str):
    f = filedialog.askopenfilename(initialdir=TEMPL, filetypes=ftypes(flag))
    if f: var.set(f)

def run_tool(script, in_flag, out_flag, stem, ext):
    """Spawn a helper exe (or python script) in a background thread."""
    # 1. resolve input
    if script == "PDFScraper.py":
        inp = guide_pdf_var.get().strip()
    else:
        inp = in_vars[(script, in_flag)].get().strip()

    # attempt to auto-guess missing input under current output dir
    if (not inp or not Path(inp).exists()) and in_flag.startswith("--in_"):
        guess = Path(out_dir_var.get()) / f"{pre_var.get()}{Path(inp).name}"
        if guess.exists():
            inp, in_vars[(script, in_flag)].set(str(guess))

    if not inp or not Path(inp).exists():
        status_lbl[script].configure(text="[ERROR] input missing", text_color="red")
        return

    # 2. build output
    out_path = Path(out_dir_var.get()) / f"{pre_var.get()}{stem}{suf_var.get()}{ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. interpreter / helper selection
    if getattr(sys, "frozen", False):
        exe = HELPERS / f"{script[:-3]}.exe"
        if not exe.exists():
            status_lbl[script].configure(text="[ERROR] helper missing", text_color="red")
            return
        cmd = [str(exe), in_flag, inp, out_flag, str(out_path)]
    else:
        cmd = [sys.executable, str(SCRIPTS / script), in_flag, inp, out_flag, str(out_path)]

    # 4. extra flags
    if script in {"GetLinks.py", "FillMissingData.py"}:
        cmd += ["--master_csv", master_csv_var.get()]
    if script in {"GeneratePDF.py", "PDFScraper.py"}:
        cmd += ["--img_dir", img_dir_var.get()]
        if script == "PDFScraper.py":
            cmd += ["--map_csv", str(Path(img_dir_var.get()).parent / "image_map.csv")]

    # 5. thread worker
    def worker():
        lbl = status_lbl[script]
        lbl.configure(text="running…", text_color="yellow")
        log_q.put(f"\n> {' '.join(cmd)}\n")
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, bufsize=1) as p:
                for line in p.stdout:
                    log_q.put(line)
            ok = p.returncode == 0
            lbl.configure(text="[OK]" if ok else "[ERROR]", text_color="green" if ok else "red")

            # if success, push this file path into the *next* tool's input box
            if ok:
                produced = str(out_path)
                for j, (scr, i_flag, *_rest) in enumerate(TOOLS[:-1]):
                    if scr == script:
                        nxt_scr, nxt_flag, *_ = TOOLS[j+1]
                        in_vars[(nxt_scr, nxt_flag)].set(produced)
                        break
        except Exception as e:
            lbl.configure(text="[EXCEPTION]", text_color="red")
            log_q.put(f"[launcher] {e}\n")

    threading.Thread(target=worker, daemon=True).start()

# build tool rows
for script, in_flag, out_flag, def_in, stem, ext in TOOLS:
    parent = b_body if TAB_MAP[script] == "builder" else e_body
    fr = ctk.CTkFrame(parent)
    fr.pack(fill="x", pady=4, padx=8)

    # header
    title = LABEL_OVERRIDES.get(script, script.replace(".py","").replace("_"," ").title())
    head = ctk.CTkFrame(fr) ; head.pack(fill="x", padx=10, pady=(2,1))
    ctk.CTkLabel(head, text=title, font=("Arial",14,"bold")).pack(side="left")
    ctk.CTkButton(head, text="Run", width=70,
                  command=lambda s=script,i=in_flag,o=out_flag,st=stem,e=ext: run_tool(s,i,o,st,e)).pack(side="right", padx=4)

    # input row
    in_row = ctk.CTkFrame(fr) ; in_row.pack(fill="x", padx=10, pady=1)
    ctk.CTkLabel(in_row, text=pretty(in_flag), width=118).pack(side="left")
    if script == "PDFScraper.py":
        var = guide_pdf_var
    else:
        var = ctk.StringVar(value=str(REPO / def_in))
    in_vars[(script,in_flag)] = var
    ctk.CTkEntry(in_row, textvariable=var, width=380).pack(side="left", padx=4)
    ctk.CTkButton(in_row, text="Browse…", command=lambda v=var,f=in_flag: choose_input(v,f)).pack(side="left")

    # output row
    out_row = ctk.CTkFrame(fr) ; out_row.pack(fill="x", padx=10, pady=(0,2))
    ctk.CTkLabel(out_row, text=pretty(out_flag), width=118).pack(side="left")
    lbl = ctk.CTkLabel(out_row, text="", text_color="#a6f4a6", anchor="w")
    lbl.pack(side="left", padx=4)
    out_widgets.append((script, lbl, stem, ext))
    status_lbl[script] = ctk.CTkLabel(out_row, text="") ; status_lbl[script].pack(side="right", padx=4)

# ─── Console widget (tighter spacing) ────────────────────────────────────
console = ctk.CTkTextbox(app, height=160, wrap="none")
console.pack(fill="both", padx=15, pady=(0,8), expand=False)

scr = ctk.CTkScrollbar(app, command=console.yview)
scr.place(relx=0.97, rely=0.80, relheight=0.18)
console.configure(yscrollcommand=scr.set)

def feed_console() -> None:
    while True:
        raw = log_q.get()
        if "CropBox missing from /Page" in raw:            # mute PyMuPDF spam
            continue
        clean = raw.replace("\r","")
        if not clean.strip():                              # skip blank lines
            continue
        console.insert("end", clean.rstrip("\n") + "\n")   # single-spaced
        console.see("end")

threading.Thread(target=feed_console, daemon=True).start()

# ─── Initial paint ───────────────────────────────────────────────────────
refresh_out_labels()
app.mainloop()
