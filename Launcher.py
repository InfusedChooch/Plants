#!/usr/bin/env python3
# Launcher.py – simple CTk GUI for the plant-database tool-chain (2025-05-30)

import sys, subprocess, threading, queue, customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

# ─── Appearance ──────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

BASE    = Path(__file__).resolve().parent
SCRIPTS = BASE / "Static/Python"
OUTDEF  = BASE / "Static/Outputs"
TEMPL   = BASE / "Static/Templates"
today   = datetime.now().strftime("%Y%m%d")

# [script, in-flag, out-flag, default-input, out-stem, ext]
TOOLS = [
    ("PDFScraper.py",    "--in_pdf",  "--out_csv",
     "Static/Templates/Plant Guide 2025 Update.pdf",
     "Plants_NeedLinks", ".csv"),
    ("GetLinks.py",      "--in_csv",  "--out_csv",
     "Static/Outputs/Plants_NeedLinks.csv",
     "Plants_Linked", ".csv"),
    ("FillMissingData.py","--in_csv","--out_csv",
     "Static/Outputs/Plants_Linked.csv",
     "Plants_Linked_Filled", ".csv"),
   # ("Excelify2.py",     "--in_csv",  "--out_xlsx",
    # "Static/Templates/Plants_Linked_Filled_Master.csv",
     #"Plants_Linked_Filled_Review", ".xlsx"),
    ("GeneratePDF.py",   "--in_csv",  "--out_pdf",
     "Static/Templates/Plants_Linked_Filled_Master.csv",
     "Plant_Guide_EXPORT", ".pdf"),
]

def pretty(flag: str) -> str:
    return f"{'Input' if flag.startswith('--in_') else 'Output'} {flag.split('_',1)[1].upper()}"

def ftypes(flag: str):
    return [("PDF", "*.pdf")] if "pdf" in flag else [("CSV", "*.csv"), ("Excel", "*.xlsx")]

# ─── GUI ROOT ────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title("🌿 Plant Tool-chain Launcher")
app.geometry("840x740")

# ─── GLOBAL VARS ─────────────────────────────────────────────────────────
out_dir_var   = ctk.StringVar(value=str(OUTDEF))
suf_var       = ctk.StringVar(value=f"_{today}")
img_dir_var   = ctk.StringVar(value=str(OUTDEF / "pdf_images"))
_img_user_set = False          # flipped to True after manual browse

log_q: queue.Queue[str] = queue.Queue(maxsize=500)   # console feed

# per-tool input vars   {(script,in_flag): StringVar}
in_vars = {}

# ─── Top-of-window controls ──────────────────────────────────────────────
def refresh_out_labels():
    for _, lbl, stem, ext in out_widgets:
        lbl.configure(text=str(Path(out_dir_var.get()) / f"{stem}{suf_var.get()}{ext}"))

def browse_output():
    folder = filedialog.askdirectory(initialdir=out_dir_var.get())
    if not folder: return
    out_dir_var.set(folder)
    global _img_user_set
    if not _img_user_set:
        default_img = Path(folder) / "pdf_images"
        img_dir_var.set(str(default_img))
    refresh_out_labels()

def browse_img():
    folder = filedialog.askdirectory(initialdir=img_dir_var.get())
    if folder:
        img_dir_var.set(folder)
        global _img_user_set
        _img_user_set = True

hdr = ctk.CTkFrame(app); hdr.pack(fill="x", padx=15, pady=10)
ctk.CTkLabel(hdr, text="Output folder:").grid(row=0,column=0,sticky="e",padx=4,pady=4)
ctk.CTkEntry(hdr, textvariable=out_dir_var, width=420).grid(row=0,column=1,padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_output).grid(row=0,column=2)

ctk.CTkLabel(hdr, text="File-name suffix:").grid(row=1,column=0,sticky="e",padx=4,pady=4)
ctk.CTkEntry(hdr, textvariable=suf_var, width=120).grid(row=1,column=1,sticky="w",padx=4)
suf_var.trace_add("write", lambda *a: refresh_out_labels())

ctk.CTkLabel(hdr, text="Image folder:").grid(row=2,column=0,sticky="e",padx=4,pady=4)
ctk.CTkEntry(hdr, textvariable=img_dir_var, width=420).grid(row=2,column=1,padx=4)
ctk.CTkButton(hdr, text="Browse", command=browse_img).grid(row=2,column=2)

# ─── SCROLL AREA WITH TOOL ROWS ──────────────────────────────────────────
body = ctk.CTkScrollableFrame(app, height=420); body.pack(fill="both", padx=15, pady=6)
status_lbl = {}
out_widgets = []

def choose_input(var: ctk.StringVar, flag: str):
    f = filedialog.askopenfilename(initialdir=TEMPL, filetypes=ftypes(flag))
    if f: var.set(f)

def run_tool(script, in_flag, out_flag, stem, ext):
    inp = in_vars[(script,in_flag)].get().strip()
    if not inp or not Path(inp).exists():
        status_lbl[script].configure(text="❌ input missing", text_color="red")
        return
    out_path = Path(out_dir_var.get()) / f"{stem}{suf_var.get()}{ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SCRIPTS/script),
           in_flag, inp,
           out_flag, str(out_path)]
    if script in {"GeneratePDF.py", "PDFScraper.py"}:
        cmd += ["--img_dir", img_dir_var.get()]
        if script == "PDFScraper.py":
            cmd += ["--map_csv", str(Path(img_dir_var.get()).parent / "image_map.csv")]

    def worker():
        lbl = status_lbl[script]
        lbl.configure(text="⏳ running…", text_color="yellow")
        log_q.put(f"\n\n▶ {' '.join(cmd)}\n")
        try:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, bufsize=1) as p:
                for line in p.stdout: log_q.put(line)
            lbl.configure(text="✅ finished" if p.returncode==0 else "❌ error",
                          text_color="green" if p.returncode==0 else "red")
        except Exception as e:
            lbl.configure(text="❌ exception", text_color="red")
            log_q.put(f"[launcher] {e}\n")

    threading.Thread(target=worker, daemon=True).start()

for script,in_flag,out_flag,def_in,stem,ext in TOOLS:
    fr = ctk.CTkFrame(body); fr.pack(fill="x", pady=6, padx=8)
    ctk.CTkLabel(fr, text=script, font=("Arial",14,"bold")).pack(anchor="w")

    # input row
    in_row = ctk.CTkFrame(fr); in_row.pack(fill="x", padx=12, pady=2)
    ctk.CTkLabel(in_row, text=pretty(in_flag), width=110).pack(side="left")
    var = in_vars.setdefault((script,in_flag), ctk.StringVar(value=str(BASE/def_in)))
    ctk.CTkEntry(in_row, textvariable=var, width=380).pack(side="left", padx=4)
    ctk.CTkButton(in_row, text="Browse…",
                  command=lambda v=var,f=in_flag: choose_input(v,f)).pack(side="left")

    # output preview
    out_row = ctk.CTkFrame(fr); out_row.pack(fill="x", padx=12, pady=1)
    ctk.CTkLabel(out_row, text=pretty(out_flag), width=110).pack(side="left")
    out_lbl = ctk.CTkLabel(out_row, text="", text_color="#a6f4a6", anchor="w")
    out_lbl.pack(side="left", padx=4)
    out_widgets.append((script,out_lbl,stem,ext))

    # status + ▶
    act = ctk.CTkFrame(fr); act.pack(fill="x", padx=12, pady=2)
    st = ctk.CTkLabel(act, text=""); st.pack(side="left", padx=4)
    status_lbl[script]=st
    ctk.CTkButton(act, text="▶ Run", width=70,
                  command=lambda s=script,inf=in_flag,outf=out_flag,
                                 st=stem,e=ext: run_tool(s,inf,outf,st,e)
                 ).pack(side="right")

# ─── CONSOLE ─────────────────────────────────────────────────────────────
console = ctk.CTkTextbox(app, height=170, wrap="none"); console.pack(fill="both", padx=15, pady=8)
scr = ctk.CTkScrollbar(app, command=console.yview); scr.place(relx=0.97, rely=0.73, relheight=0.23)
console.configure(yscrollcommand=scr.set)

def feed_console():
    while True:
        line = log_q.get()
        console.insert("end", line)
        console.see("end")

threading.Thread(target=feed_console, daemon=True).start()

# initial label refresh
refresh_out_labels()
app.mainloop()
