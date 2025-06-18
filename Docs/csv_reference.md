# CSV Column Reference

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
Sun                      : MBG → WF "Light Requirement"    : "Full Sun, Part Sun, …"
Water                    : MBG → WF "Soil Moisture"        : "Wet, Medium, Dry"
AGCP Regional Status     : WF (Wetland Indicator)          : FACU | OBL | …
USDA Hardiness Zone      : MBG "Zone"                      : "Zone X – Y"

Attracts                 : PR + WF + MBG + Pinelands        : "Bees, Butterflies, …"
Tolerates                : MBG + PR + NM + Pinelands        : "Deer, Salt, …"
Soil Description         : WF "Soil Description"            : "paragraph"
Condition Comments       : WF "Condition Comments"          : "paragraph"
MaintenanceLevel         : MBG "Maintenance"                : "Low | Medium | High"
Native Habitats          : WF "Native Habitat"              : "Prairie, Woodland, …"
Culture                  : MBG "Culture" / "Growing Tips"   : "paragraph"
Uses                     : MBG "Uses"                       : "paragraph"
UseXYZ                   : WF Benefit list                  : "Use Ornamental: …; Use Wildlife: …"
WFMaintenance            : WF "Maintenance:"                : "Maintenence: ..."
Problems                 : MBG "Problems"                   : "paragraph"

Link: MBG                : GetLinks                         : URL
Link: Wildflower.org     : GetLinks                         : URL
Link: Pleasant Run       : GetLinks                         : URL
Link: New Moon           : GetLinks                         : URL
Link: Pinelands          : GetLinks                         : URL
Link: Other              : [Tag,"URL","Label"]              : Entry list "[Tag,"URL","Label"]" : [T1,"https://Test.com","Test 1"]; 
Rev                      : User Input (YYYYMMDD_FL)         : "YYYYMMDD_FirstinitialLastinital"
```

```csv
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Link: Others,Rev
```
