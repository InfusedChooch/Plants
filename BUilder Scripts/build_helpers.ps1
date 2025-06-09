# ---- build_helpers.ps1 (run from repo root) ------------------------------
$helpers = "PDFScraper.py","GetLinks.py","FillMissingData.py","GeneratePDF.py","Excelify2.py"
$dest    = "dist\Launcher\_internal\helpers"          # <- final location

foreach ($h in $helpers) {
    pyinstaller "Python\$h" --onefile --noconfirm --windowed `
        --add-data "Static;Static" `                   # lets helpers see themes, etc.
        --distpath  $dest
}
