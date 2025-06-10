RU Plant Guide/
├── Launcher.exe                     # <- main GUI
├── _internal/
│   ├── Static/
│   │   └── themes/
│   │   │    └── leaf.ico
│   │   └── Python_full/
│   ├── helpers/
│   │   ├── PDFScraper.exe
│   │   ├── GeneratePDF.exe
│   │   └── Excelify2.exe
├── Templates/
│   ├── Plants_Linked_Filled_Master.csv
│   ├── Plant Guide 2025 Update.pdf
│   └── MASTER_MASTER_20250605.csv
├── Outputs/
│   ├── pdf_images/
│   ├── Plants_Linked_Filled.csv
│   ├── Plant_Guide_EXPORT.pdf
│   └── Plants_Linked_Filled_Review.xlsx


We need to add another header to the CSV Master. This header is "Conditions Comments" and it is found on Wildflower.org links It should be the Text following the "Conditions Comments:" section. I need to update my toolchain to accept my new CSV formate 

Plant Type,Key,Botanical Name,Common Name,Height (ft),Spread (ft),Bloom Color,Bloom Time,Sun,Water,Tolerates,Maintenance,Native Habitats,Attracts,Soil Description,Condition Comments,Distribution Zone,AGCP Regional Status,Link: Missouri Botanical Garden,Link: Wildflower.org,Link: Pleasantrunnursery.com,Link: Newmoonnursery.com,Link: Pinelandsnursery.com

