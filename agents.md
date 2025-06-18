## Start
- Update `readme.md` with tool chain steps, launcher usage, and expected input/output files.
- Clean up comments and basic formatting in the Python scripts.
- Ensure `GeneratePDF.py` creates `Outputs/Meow_Plant_Guide_EXPORT.pdf` using `Outputs/20991212_Masterlist_Template.csv`.
- Replace `Static/Tools/Tool Test/WhatIhave.PNG` with `WhatIwant.png`.
- Fix the footer on the last page and skip blank or `NA` fields.

## Details
- CSV column reference is in [Docs/csv_reference.md](Docs/csv_reference.md).
- Comment tags are described in [Docs/comment_style.md](Docs/comment_style.md).
- Excel link formula in [Docs/excel_formula.md](Docs/excel_formula.md).

## Testing
- Run `pytest -q` before committing.
