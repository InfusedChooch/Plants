## Start
```
I need my toolchains csv outpput catagories to match the csv column formatting through out. I went and hand tuned the desire coulmn entires in Templates\DatasetFormating_Template_Sample.csv .. The way each column holds the data is important. the current methods results in data that looks like Outputs\NewMaster\0612_Masterlist_Merged.csv. Certain columns are a mix of "" strings and not. My Templates\DatasetFormating_Template_Sample.csv has uniform data in each column. I want this uniformity to be standrad across the whole toolchain. notable export csv tools are Static\Python_full\FillMissingData.py, Static\Python_full\Excelify2_Testing.py, and Static\Tools\CleanMerge.py .

I need my code base commented out for basic functions, and it should be updated to expect comments for the Better COmments VS Code Extension "better-comments.

Make sure to update the comments at the top when they are finished, You can use the "# // tag" and change the comment on the line, or Needs Testing

```

**CSV → Source chain (left‑to‑right = first place we look, fallbacks follow, + means append to previous entry)**
```
CSV header               : data source path                : expected format
Plant Type               : Masterlist                      : "Plant Type"
Key                      : FillMissingData                 : 2-3 letter unique code
Botanical Name           : Masterlist                      : "Genus species 'Variety'" (italics)
Common Name              : Masterlist                      : "COMMON NAME"

Height (ft)              : MBG → WF → PL                   : X - Y
Spread (ft)              : MBG → WF → PL                   : X - Y
Bloom Color              : WF + MBG + PL/NM                : "Color1, Color2, …"
Bloom Time               : WF + MBG + PL/NM                : "Jan, Feb, …"
Sun                      : MBG → WF “Light Requirement”    : "Full Sun, Part Sun, …"
Water                    : MBG → WF “Soil Moisture”        : "Wet, Medium, Dry"
AGCP Regional Status     : WF (Wetland Indicator)          : FACU | OBL | …
USDA Hardiness Zone      : MBG “Zone”                      : "Zone X – Y"

Attracts                 : PR + WF + MBG + Pinelands        : "Bees, Butterflies, …"
Tolerates                : MBG + PR + NM + Pinelands        : "Deer, Salt, …"
Soil Description         : WF “Soil Description”            : "paragraph"
Condition Comments       : WF “Condition Comments”          : "paragraph"
MaintenanceLevel         : MBG “Maintenance”                : "Low | Medium | High"
Native Habitats          : WF “Native Habitat”              : "Prairie, Woodland, …"
Culture                  : MBG “Culture” / “Growing Tips”   : "paragraph"
Uses                     : MBG “Uses”                       : "paragraph"
UseXYZ                   : WF Benefit list                  : "Use Ornamental: …; Use Wildlife: …"
WFMaintenance            : WF "Maintenance:"                : "Maintenence: ..."
Problems                 : MBG “Problems”                   : "paragraph"

Link: MBG                : GetLinks                         : URL
Link: Wildflower.org     : GetLinks                         : URL
Link: Pleasant Run       : GetLinks                         : URL
Link: New Moon           : GetLinks                         : URL
Link: Pinelands          : GetLinks                         : URL
Link: Other              : [Tag,"URL","Label"]              : Entry list "[Tag,""URL"",""Label""]" : [T1,""https://Test.com"",""Test 1""];
Rev                      : User Input (YYYYMMDD_FL)         : "YYYYMMDD_FirstinitalLastinital" 
```

```
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Link: Others,Rev

```

```
Comment Style Guide Meaning -- This repo uses better-comments (VS Code) -- key functions
* : Important information
! : Deprecated method
? : Something to think about
TODO : Next steps here
// : Note for the Layman - useful for the intended User
```

```
!Urgent
@@  # inside the loop that writes mirror formulas into Plant Data
-        base_tag   = get_column_letter(3 * (idx - 1) + 3)   # C,F,I,...
-        base_label = get_column_letter(3 * (idx - 1) + 4)   # D,G,J,...
-        base_url   = get_column_letter(3 * (idx - 1) + 5)   # E,H,K,...
+        base_label = get_column_letter(3 * (idx - 1) + 3)   # C,F,I,...
+        base_url   = get_column_letter(3 * (idx - 1) + 4)   # D,G,J,...
+        base_tag   = get_column_letter(3 * (idx - 1) + 5)   # E,H,K,...
@@
-        ws.cell(row=row_pd, column=tag_pd).value = \
-            f"=CHOOSE($AE{row_pd}," + \
-            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 3)}{row_ol}"
-                     for j in range(1, MAX_LINKS + 1)) + ")"
-
-        # Label n
-        ws.cell(row=row_pd, column=label_pd).value = \
-            f"=CHOOSE($AE{row_pd}," + \
-            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 4)}{row_ol}"
-                     for j in range(1, MAX_LINKS + 1)) + ")"
-
-        # URL n
-        ws.cell(row=row_pd, column=url_pd).value = \
-            f"=CHOOSE($AE{row_pd}," + \
-            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 5)}{row_ol}"
-                     for j in range(1, MAX_LINKS + 1)) + ")"
+        # Tag n  (now pulls column  E,H,K,…)
+        ws.cell(row=row_pd, column=tag_pd).value = \
+            f"=CHOOSE($AE{row_pd}," + \
+            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 5)}{row_ol}"
+                     for j in range(1, MAX_LINKS + 1)) + ")"
+
+        # Label n  (C,F,I,…)
+        ws.cell(row=row_pd, column=label_pd).value = \
+            f"=CHOOSE($AE{row_pd}," + \
+            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 3)}{row_ol}"
+                     for j in range(1, MAX_LINKS + 1)) + ")"
+
+        # URL n   (D,G,J,…)
+        ws.cell(row=row_pd, column=url_pd).value = \
+            f"=CHOOSE($AE{row_pd}," + \
+            ",".join(f"'Other Links'!{get_column_letter(3 * (j - 1) + 4)}{row_ol}"
+                     for j in range(1, MAX_LINKS + 1)) + ")"
```


and

```
@@  # fix Link: Others reference – remove stray apostrophe
-    ws.cell(row=row_pd, column=link_others_col).value = \
-        f"='Other Links'!{get_column_letter(PLANT_DATA_HEADERS.index('CSV RAW OUTPUT')+1)}{row_ol}"
+    ws.cell(row=row_pd, column=link_others_col).value = \
+        f"='Other Links'!{get_column_letter(PLANT_DATA_HEADERS.index('CSV RAW OUTPUT')+1)}{row_ol}".replace(\"'Other Links'!\", \"Other Links!\")
```


```
Link String TEst

=TEXTJOIN(
  ";", TRUE,

  IF(OR($E3="",$D3="",$C3=""), "",
     CONCAT("[",$E3,",",CHAR(34),$D3,CHAR(34),",",CHAR(34),$C3,CHAR(34),"]")),

  IF(OR($H3="",$G3="",$F3=""), "",
     CONCAT("[",$H3,",",CHAR(34),$G3,CHAR(34),",",CHAR(34),$F3,CHAR(34),"]")),

  IF(OR($K3="",$J3="",$I3=""), "",
     CONCAT("[",$K3,",",CHAR(34),$J3,CHAR(34),",",CHAR(34),$I3,CHAR(34),"]")),

  IF(OR($N3="",$M3="",$L3=""), "",
     CONCAT("[",$N3,",",CHAR(34),$M3,CHAR(34),",",CHAR(34),$L3,CHAR(34),"]"))
)
