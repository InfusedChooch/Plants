import pandas as pd
import argparse
import re

parser = argparse.ArgumentParser(description="Rebase master CSV to new column layout")
parser.add_argument("input", help="Path to existing master CSV")
parser.add_argument("output", help="Path to write converted CSV")
args = parser.parse_args()

old = pd.read_csv(args.input, dtype=str).fillna("")

new_cols = [
    "Plant Type", "Key", "Botanical Name", "Common Name",
    "Height (ft)", "Spread (ft)", "Bloom Color", "Bloom Time",
    "Sun", "Water", "Tolerates", "Maintenance",
    "Native Habitats", "Wildlife Benefits", "Distribution Zone",
    "AGCP Regional Status", "Link: Missouri Botanical Garden",
    "Link: Wildflower.org", "Link: Pleasant Run",
    "Link: New Moon", "Link: Pinelands",
]

new = pd.DataFrame(columns=new_cols)

new["Plant Type"] = old.get("Plant Type", "")
new["Key"] = old.get("Key", "")
new["Botanical Name"] = old.get("Botanical Name", "")
new["Common Name"] = old.get("Common Name", "")
new["Height (ft)"] = old.get("Height (ft)", "")
new["Spread (ft)"] = old.get("Spread (ft)", "")
new["Bloom Color"] = old.get("Bloom Color", "")
new["Bloom Time"] = old.get("Bloom Time", "")
new["Sun"] = old.get("Sun", "")
new["Water"] = old.get("Water", "")

tols = []
maint = []
for val in old.get("Characteristics", []):
    t, m = "", ""
    if isinstance(val, str):
        m1 = re.search(r"Tolerate:\s*([^|]+)", val)
        if m1:
            t = m1.group(1).strip()
        m2 = re.search(r"Maintenance:\s*([^|]+)", val)
        if m2:
            m = m2.group(1).strip()
    tols.append(t)
    maint.append(m)
new["Tolerates"] = tols
new["Maintenance"] = maint

new["Native Habitats"] = old.get("Habitats", "")
new["Wildlife Benefits"] = old.get("Wildlife Benefits", "")
new["Distribution Zone"] = old.get("Distribution", old.get("Zone", ""))
new["AGCP Regional Status"] = old.get("AGCP Regional Status", "")
new["Link: Missouri Botanical Garden"] = old.get("Link: Missouri Botanical Garden", old.get("MBG Link", ""))
new["Link: Wildflower.org"] = old.get("Link: Wildflower.org", old.get("WF Link", ""))
new["Link: Pleasant Run"] = old.get("Link: Pleasant Run", "")
new["Link: New Moon"] = old.get("Link: New Moon", "")
new["Link: Pinelands"] = old.get("Link: Pinelands", "")

new.to_csv(args.output, index=False)
