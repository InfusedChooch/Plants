## Start

I need the readme.md updated to discribe the intended tool chain use, and what fiiles to input output, Also it need to explain how to use the launcher first. Then gove explicit python instructions. Go through all python code and clea up the comments, also look for basic formatting fixes. 

```
Static\Python_full\GeneratePDF.py makes Outputs\Meow_Plant_Guide_EXPORT.pdf with Outputs\20991212_Masterlist_Template.csv
Static\Tools\Tool Test\WhatIhave.PNG needs to be Static\Tools\Tool Test\WhatIwant.png visually. 
The Footer still isn't populating on the last page -- Ygenus yspecies 'Variety5'
If a feild is blank, missing, or NA do not populate it. 
```

```

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

```CSV
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Link: Others,Rev

```

```md
Comment Style Guide Meaning -- This repo uses better-comments (VS Code) -- key functions
* : Important information
! : Deprecated method
? : Something to think about
TODO : Next steps here
// : Note for the Layman - useful for the intended User
```



```excel
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
```
