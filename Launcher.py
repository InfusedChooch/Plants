# ctk_launcher.py
# GUI launcher for plant database toolchain with override tab + validation

import customtkinter as ctk
from tkinter import filedialog
import subprocess
from pathlib import Path

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

BASE = Path(__file__).resolve().parent

TOOLS = [
    ("PDFScraper.py", "--in_pdf", "--out_csv"),
    ("GetLinks.py", "--in_csv", "--out_csv"),
    ("FillMissingData.py", "--in_csv", "--out_csv"),
    ("TestLinks.py", "--in_csv", "--out_csv"),
    ("Excelify2.py", "--in_csv", "--out_xlsx"),
    ("GeneratePDF.py", "--in_csv", "--out_pdf"),
]

app = ctk.CTk()
app.geometry("620x580")
app.title("🌿 Plant Toolchain Launcher")

tabs = ctk.CTkTabview(app)
tabs.pack(expand=True, fill="both", padx=20, pady=20)

tab_run = tabs.add("Run Tools")
tab_override = tabs.add("Override Paths")

check_vars = []
override_vars = {}

# ─── Run Tab Layout ─────────────────────────────────────
ctk.CTkLabel(tab_run, text="Select tools to run:", font=("Arial", 18)).pack(pady=10)
run_frame = ctk.CTkFrame(tab_run)
run_frame.pack(fill="x", padx=10, pady=5)

for name, _, _ in TOOLS:
    var = ctk.BooleanVar(value=False)
    chk = ctk.CTkCheckBox(run_frame, text=name, variable=var)
    chk.pack(anchor="w", padx=20, pady=3)
    check_vars.append(var)

def run_selected():
    for (tool, arg1, arg2), checked in zip(TOOLS, check_vars):
        if checked.get():
            args = ["python", str(BASE / tool)]
            val1 = override_vars.get((tool, arg1), "").get().strip()
            val2 = override_vars.get((tool, arg2), "").get().strip()
            if val1: args += [arg1, val1]
            if val2: args += [arg2, val2]
            if arg1.startswith("--in") and val1 and not Path(val1).exists():
                status.configure(text=f"❌ {tool}: Missing {val1}", text_color="red")
                return
            subprocess.run(args)
    status.configure(text="✅ All selected tools finished.", text_color="green")

ctk.CTkButton(tab_run, text="▶ Run Selected", command=run_selected).pack(pady=15)
status = ctk.CTkLabel(tab_run, text="", font=("Arial", 14))
status.pack(pady=5)

# ─── Override Tab Layout ────────────────────────────────
ctk.CTkLabel(tab_override, text="Override file paths (optional):", font=("Arial", 16)).pack(pady=10)

for tool, arg1, arg2 in TOOLS:
    sec = ctk.CTkFrame(tab_override)
    sec.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(sec, text=tool, font=("Arial", 14)).pack(anchor="w", padx=5)
    for arg in (arg1, arg2):
        if not arg: continue
        row = ctk.CTkFrame(sec)
        row.pack(fill="x", pady=2, padx=10)
        ctk.CTkLabel(row, text=arg).pack(side="left")
        var = ctk.StringVar()
        entry = ctk.CTkEntry(row, textvariable=var, width=400)
        entry.pack(side="left", padx=5)
        override_vars[(tool, arg)] = var

app.mainloop()
