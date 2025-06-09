#!/usr/bin/env python3
# Launcher.py - CTk GUI for the plant-database tool-chain (2025-06-05, portable one-dir)

import sys, subprocess, threading, queue, customtkinter as ctk
from tkinter import filedialog
import webbrowser
from pathlib import Path
from datetime import datetime


# --- Locate the bundle root ----------------------------------------------
from pathlib import Path
import sys

def repo_dir() -> Path:
    """Return the app root whether running from source or PyInstaller (onedir)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent  # [OK] works in one-dir
    return Path(__file__).resolve().parent



REPO   = repo_dir()                 # <-- new single source of truth
HELPERS = REPO / "helpers"          
STATIC = REPO / "Static"            # scripts & themes stay here

# --- Appearance ----------------------------------------------------------
ctk.set_appearance_mode("dark")
THEME = STATIC / "themes" / "rutgers.json"
ctk.set_default_color_theme(str(THEME))

# --- Paths used throughout the GUI ---------------------------------------
SCRIPTS = STATIC / "Python"         # original .py sources (used when *not* frozen)
TEMPL   = REPO / "Templates"        # <-- moved out of Static
OUTDEF  = REPO / "Outputs"          # <-- moved out of Static
OUTDEF.mkdir(exist_ok=True)         # create on first launch

today   = datetime.now().strftime("%Y%m%d")

# --- Tool Config ---------------------------------------------------------
TOOLS = [
    # script           in-flag      out-flag     default-IN                         stem                     ext
    ("PDFScraper.py",  "--in_pdf",  "--out_csv", "Templates/Plant Guide 2025 Update.pdf", "Plants_NeedLinks",      ".csv"),
    ("GetLinks.py",    "--in_csv",  "--out_csv", "Outputs/Plants_NeedLinks.csv",        "Plants_Linked",          ".csv"),
    ("FillMissingData.py","--in_csv","--out_csv","Outputs/Plants_Linked.csv",           "Plants_Linked_Filled",   ".csv"),
    ("GeneratePDF.py", "--in_csv",  "--out_pdf", "Outputs/Plants_Linked_Filled.csv",    "Plant_Guide_EXPORT",     ".pdf"),
    ("Excelify2.py",   "--in_csv",  "--out_xlsx","Outputs/Plants_Linked_Filled.csv",    "Plants_Linked_Filled_Review",".xlsx"),
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


# --- Utility -------------------------------------------------------------
def pretty(flag: str) -> str:
    return f"{'Input' if flag.startswith('--in_') else 'Output'} {flag.split('_',1)[1].upper()}"


def ftypes(flag: str):
    return (
        [("PDF", "*.pdf")] if "pdf" in flag else [("CSV", "*.csv"), ("Excel", "*.xlsx")]
    )


# --- GUI ROOT ------------------------------------------------------------
app = ctk.CTk()
app.title(" Rutgers Plant Launcher")
app.geometry("860x760")

# --- Global Vars ---------------------------------------------------------
out_dir_var = ctk.StringVar(value=str(OUTDEF))
pre_var = ctk.StringVar(value=f"{today}_")
suf_var = ctk.StringVar(value="")
img_dir_var = ctk.StringVar(value=str(OUTDEF / "pdf_images"))
guide_pdf_var = ctk.StringVar(value=str(TEMPL / "Plant Guide 2025 Update.pdf"))
master_csv_var = ctk.StringVar(value=str(TEMPL / "Plants_Linked_Filled_Master.csv"))
_img_user_set = False

log_q: queue.Queue[str] = queue.Queue(maxsize=500)
in_vars: dict[tuple[str, str], ctk.StringVar] = {}
status_lbl: dict[str, ctk.CTkLabel] = {}
out_widgets: list[tuple] = []

# --- Top Controls --------------------------------------------------------
hdr = ctk.CTkFrame(app)
hdr.pack(fill="x", padx=15, pady=10)


def refresh_out_labels():
    """Update output labels to reflect current folder, prefix and suffix."""

    for _, lbl, stem, ext in out_widgets:
        lbl.configure(
            text=str(
                Path(out_dir_var.get()) / f"{pre_var.get()}{stem}{suf_var.get()}{ext}"
            )
        )


def browse_output():
    """Prompt for an output directory and refresh file previews."""

    folder = filedialog.askdirectory(initialdir=out_dir_var.get())
    if folder:
        out_dir_var.set(folder)
        global _img_user_set
        if not _img_user_set:
            img_dir_var.set(str(Path(folder) / "pdf_images"))
        refresh_out_labels()


def browse_img():
    """Prompt for a directory to store scraped images."""

    folder = filedialog.askdirectory(initialdir=img_dir_var.get())
    if folder:
        img_dir_var.set(folder)
        global _img_user_set
        _img_user_set = True


def browse_pdf():
    """Prompt for the guide PDF file."""

    f = filedialog.askopenfilename(
        initialdir=Path(guide_pdf_var.get()).parent, filetypes=[("PDF", "*.pdf")]
    )
    if f:
        guide_pdf_var.set(f)


def browse_master():
    """Prompt for the master CSV file."""

    f = filedialog.askopenfilename(
        initialdir=Path(master_csv_var.get()).parent, filetypes=[("CSV", "*.csv")]
    )
    if f:
        master_csv_var.set(f)


def open_chrome_portable():
    webbrowser.open(
        "https://portableapps.com/apps/internet/google_chrome_portable",
        new=1,
    )


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

# Guide PDF
ctk.CTkLabel(hdr, text="Guide PDF:").grid(row=3, column=0, sticky="e", padx=4, pady=4)
ctk.CTkEntry(hdr, textvariable=guide_pdf_var, width=430).grid(row=3, column=1, padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_pdf).grid(row=3, column=2)

# Master CSV
ctk.CTkLabel(hdr, text="Master CSV:").grid(row=4, column=0, sticky="e", padx=4, pady=4)
ctk.CTkEntry(hdr, textvariable=master_csv_var, width=430).grid(row=4, column=1, padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_master).grid(row=4, column=2)

# Chrome Portable link
ctk.CTkButton(
    hdr,
    text="Get Chrome Portable",
    width=160,
    command=open_chrome_portable,
).grid(row=5, column=1, padx=4, pady=4, sticky="w")

# --- Tabs & Tool Rows ---------------------------------------------------
tabs = ctk.CTkTabview(app)
tabs.pack(fill="both", padx=15, pady=6, expand=True)
export_tab = tabs.add("Export")
builder_tab = tabs.add("Builder")


b_body = ctk.CTkScrollableFrame(builder_tab, height=420)
b_body.pack(fill="both", expand=True)
e_body = ctk.CTkScrollableFrame(export_tab, height=420)
e_body.pack(fill="both", expand=True)


def choose_input(var: ctk.StringVar, flag: str):
    """Ask for an input file and update the provided variable."""

    f = filedialog.askopenfilename(initialdir=TEMPL, filetypes=ftypes(flag))
    if f:
        var.set(f)


def run_tool(script, in_flag, out_flag, stem, ext):
    """Execute one of the pipeline scripts in a background thread."""

    # -- 1. Resolve input path --------------------------------------------
    if script == "PDFScraper.py":
        inp = guide_pdf_var.get().strip()
    else:
        inp = in_vars[(script, in_flag)].get().strip()

    if not inp or not Path(inp).exists():
        status_lbl[script].configure(text="[ERROR] input missing", text_color="red")
        return

    # -- 2. Build output path ---------------------------------------------
    out_path = (
        Path(out_dir_var.get()) /
        f"{pre_var.get()}{stem}{suf_var.get()}{ext}"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # -- 3. Choose interpreter / helper EXE -------------------------------
    if getattr(sys, "frozen", False):
        helper_exe = HELPERS / f"{script[:-3]}.exe"  # helpers\PDFScraper.exe ...
        print(f"[debug] Expecting helper at: {helper_exe}")
        log_q.put(f"[debug] Expecting helper at: {helper_exe}\n")

        if not helper_exe.exists():
            status_lbl[script].configure(text="[ERROR] helper missing", text_color="red")
            return
        cmd = [
            str(helper_exe),
            in_flag, inp,
            out_flag, str(out_path),
        ]
    else:  # running from source -> use python
        cmd = [
            sys.executable,
            str(SCRIPTS / script),
            in_flag, inp,
            out_flag, str(out_path),
        ]

    # -- 4. Add script-specific extra flags -------------------------------
    if script in {"GetLinks.py", "FillMissingData.py"}:
        cmd += ["--master_csv", master_csv_var.get()]

    if script in {"GeneratePDF.py", "PDFScraper.py"}:
        cmd += ["--img_dir", img_dir_var.get()]
        if script == "PDFScraper.py":
            cmd += [
                "--map_csv",
                str(Path(img_dir_var.get()).parent / "image_map.csv"),
            ]

    # -- 5. Spawn in a background thread & stream output -----------------
    def worker():
        lbl = status_lbl[script]
        lbl.configure(text="running... running...", text_color="yellow")
        log_q.put(f"\n\nRun {' '.join(cmd)}\n")
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
                text="[OK] finished" if p.returncode == 0 else "[ERROR] error",
                text_color="green" if p.returncode == 0 else "red",
            )
        except Exception as e:
            lbl.configure(text="[ERROR] exception", text_color="red")
            log_q.put(f"[launcher] {e}\n")

    threading.Thread(target=worker, daemon=True).start()


for script, in_flag, out_flag, def_in, stem, ext in TOOLS:
    parent = b_body if TAB_MAP[script] == "builder" else e_body
    fr = ctk.CTkFrame(parent)
    fr.pack(fill="x", pady=6, padx=8)

    # Header row with script name and Run Run
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
        text="Run Run",
        width=70,
        command=lambda s=script, i=in_flag, o=out_flag, st=stem, e=ext: run_tool(
            s, i, o, st, e
        ),
    ).pack(side="right", padx=4)

    # Input row
    in_row = ctk.CTkFrame(fr)
    in_row.pack(fill="x", padx=12, pady=2)
    ctk.CTkLabel(in_row, text=pretty(in_flag), width=120).pack(side="left")
    if script == "PDFScraper.py":
        var = guide_pdf_var
    else:
        var = ctk.StringVar(value=str(REPO / def_in))
    in_vars[(script, in_flag)] = var
    ctk.CTkEntry(in_row, textvariable=var, width=380).pack(side="left", padx=4)
    ctk.CTkButton(
        in_row, text="Browse...", command=lambda v=var, f=in_flag: choose_input(v, f)
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

# --- Console Output ------------------------------------------------------
console = ctk.CTkTextbox(app, height=180, wrap="none")
console.pack(fill="both", padx=15, pady=8)
scr = ctk.CTkScrollbar(app, command=console.yview)
scr.place(relx=0.97, rely=0.74, relheight=0.24)
console.configure(yscrollcommand=scr.set)


def feed_console():
    """Continuously pull lines from the queue into the console widget."""

    while True:
        line = log_q.get()
        if "CropBox missing from /Page" in line:
            continue  # Suppress PyMuPDF warning
        console.insert("end", line)
        console.see("end")


threading.Thread(target=feed_console, daemon=True).start()

# --- Initial Load --------------------------------------------------------
refresh_out_labels()
app.mainloop()
