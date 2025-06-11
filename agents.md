Templates\0610_Masterlist_New_Beta_Nodata.csv is the new data structure for CSVs

Plant Type	Key	Botanical Name	Common Name	Height (ft)	Spread (ft)	Bloom Color	Bloom Time	Sun	Water	AGCP Regional Status	Distribution Zone	Attracts	Tolerates	Soil Description	Condition Comments	Maintenance	Native Habitats	Culture	Uses	UseXYZ	Propagation:Maintenance	Problems	Link: Missouri Botanical Garden	Link: Wildflower.org	Link: Pleasantrunnursery.com	Link: Newmoonnursery.com	Link: Pinelandsnursery.com		


This is a representation of where to get the data and how it is stored
| **Column**                      | **Data Hierarchy**                        | **Formatting / Notes**                                     |
| ------------------------------- | ----------------------------------------- | ---------------------------------------------------------- |
| Plant Type                      | Given                                     |                                                            |
| Key                             | generated from Botanical Name             |                                                            |
| Botanical Name                  | Given                                     | Italics                                                    |
| Common Name                     | Given                                     | stored in ALL CAPS                                         |
| Height (ft)                     | MBG → Wildflower                          | `X - Y`                                                    |
| Spread (ft)                     | MBG → Wildflower                          | `X - Y`                                                    |
| Bloom Color                     | Wildflower → MBG → Pinelands/New Moon     | `Color1, Color2, ...`                                      |
| Bloom Time                      | Wildflower → MBG → Pinelands/New Moon     | `Month1, Month2, ...`                                      |
| Sun                             | MBG → Wildflower                          | `Full sun, Part sun, Part Shade, Full Shade`               |
| Water                           | MBG → Wildflower                          | `Low, Medium, High`                                        |
| AGCP Regional Status            | Wildflower                                | from "National Wetland Indicator Status"                   |
| Distribution Zone               | MBG                                       |                                                            |
| Attracts                        | Pleasant Run + WF + MBG + Pinelands       |                                                            |
| Tolerates                       | MBG + Pleasant Run + New Moon + Pinelands | comma-separated list                                       |
| Soil Description                | Wildflower                                |                                                            |
| Condition Comments              | Wildflower                                |                                                            |
| Maintenance                     | MBG                                       | `Low, Medium, High`                                        |
| Native Habitats                 | Wildflower                                | comma-separated list                                       |
| Culture                         | MBG                                       |                                                            |
| Uses                            | MBG                                       |                                                            |
| UseXYZ                          | Wildflower                                | **Under Benefits List:"Use "X": X, Use"Y":Y..."**         |
| Propagation:Maintenance        | Wildflower                                | optional: Might not exist, Under Proptional fieldopagation |
| Problems                        | MBG                                       |                                                            |
| Link: Missouri Botanical Garden | from GetLinks                             |                                                            |
| Link: Wildflower.org            | from GetLinks                             |                                                            |
| Link: Pleasantrunnursery.com    | from GetLinks                             |                                                            |
| Link: Newmoonnursery.com        | from GetLinks                             |                                                            |
| Link: Pinelandsnursery.com      | from GetLinks                             |                                                            |
