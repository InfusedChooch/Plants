Templates\0611_Masterlist_New_Beta_Nodata.csv is the new data structure for CSVs


**CSV → Source chain (left‑to‑right = first place we look, fallbacks follow, + means append to previous entry)**
```
CSV header               : data source path                              : expected format
Plant Type               : Masterlist                                    : Perennial | Shrub | …
Key                      : FillMissingData                               : 2-3 letter unique code
Botanical Name           : Masterlist                                    : Genus species 'Variety' (italics)
Common Name              : Masterlist                                    : ALL CAPS

Height (ft)              : MBG → Wildflower.org → Pinelands              : X - Y
Spread (ft)              : MBG → Wildflower.org → Pinelands              : X - Y
Bloom Color              : Wildflower.org + MBG + Pinelands/New Moon     : Color1, Color2, …
Bloom Time               : Wildflower.org + MBG + Pinelands/New Moon     : Jan, Feb, …
Sun                      : MBG → WF “Light Requirement”                  : Full Sun, Part Sun, …
Water                    : MBG → WF “Soil Moisture”                      : Low | Medium | High
AGCP Regional Status     : WF (Wetland Indicator)                        : FACU | OBL | …
USDA Hardiness Zone      : MBG “Zone”                                    : Zone X – Y

Attracts                 : PR + WF + MBG + Pinelands                     : Bees, Butterflies, …
Tolerates                : MBG + PR + NM + Pinelands                     : Deer, Salt, …
Soil Description         : WF “Soil Description”                         : paragraph
Condition Comments       : WF “Condition Comments”                       : paragraph
MaintenanceLevel         : MBG “Maintenance”                             : Low | Medium | High
Native Habitats          : WF “Native Habitat”                           : Prairie, Woodland, …
Culture                  : MBG “Culture” / “Growing Tips”                : paragraph
Uses                     : MBG “Uses”                                    : paragraph
UseXYZ                   : WF Benefit list                               : Use Ornamental: …; Use Wildlife: …
WFMaintenance            : WF "Maintenance:"                             : free-text
Problems                 : MBG “Problems”                                : paragraph

Link: MBG                : GetLinks (MBG ID)                             : URL
Link: Wildflower.org     : GetLinks (USDA ID)                            : URL
Link: Pleasant Run       : GetLinks (name match)                         : URL
Link: New Moon           : GetLinks (name match)                         : URL
Link: Pinelands          : GetLinks (name match)                         : URL
Rev                      : User Input (YYYYMMDD_FL)                      : "YYYYMMDD_FirstinitalLastinital" 

```

```
Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,AGCP Regional Status,USDA Hardiness Zone,Attracts,Tolerates,Soil Description,Condition Comments,MaintenanceLevel,Native Habitats,Culture,Uses,UseXYZ,WFMaintenance,Problems,Link: Missouri,Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com,Rev
```
