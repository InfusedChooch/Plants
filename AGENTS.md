# Repository Guidelines

This project contains a set of scripts to automatically extract and enrich plant data from PDF files and various websites. All main scripts are located under `Static/Python/` and can be run individually or through the `Launcher.py` GUI.

## Workflow overview
1. **PDFScraper.py** – extract text, hyperlinks and images from the source PDF. Produces `Static/Outputs/Plants_NeedLinks.csv` and image files.
2. **GetLinks.py** – search for plant pages on Missouri Botanical Garden, Wildflower.org and several nursery sites to populate missing links.
3. **FillMissingData.py** – scrape details from those links and fill empty fields in the CSV.
4. **GeneratePDF.py** – output a printable PDF plant guide from the final dataset.
5. **Excelify2.py** – create a formatted Excel workbook for review.

`Launcher.py` provides a CustomTkinter interface to run these steps with GUI controls and live logging.

## Development notes
- Install dependencies with `pip install -r requirements.txt`.
- Format any modified or new Python files using [Black](https://black.readthedocs.io/) before committing. Check formatting with:
  ```bash
  black --check .
  ```
- There are no automated tests. Verify changes by running the scripts on the sample data in `Static/Templates/` and confirming the outputs in `Static/Outputs/`.

## Pull request expectations
- Summarize the purpose of the change and mention affected files.
- Include relevant console output demonstrating that scripts still run after modifications whenever possible.
