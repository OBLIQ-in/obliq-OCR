# PDF Fixture Files

Place the following anonymised or synthetic PDF files in this directory before
running the full test suite:

| Filename       | Purpose                                               |
|----------------|-------------------------------------------------------|
| `digital.pdf`  | A PDF with a native text layer (no OCR needed)       |
| `scanned.pdf`  | A fully scanned PDF (all pages are images, need OCR) |
| `mixed.pdf`    | A PDF with both digital-text and scanned pages        |
| `rotated.pdf`  | A PDF with one or more pages rotated (90°/180°/270°) |

## Rules

- **No real client documents, tax files, or PII** — use synthetic or
  anonymised files only.
- **Keep files small** — aim for < 5 MB each, ideally ≤ 1 MB.
- Files in this directory are excluded from Git via `.gitignore`.

## Generating synthetic fixtures

You can use `pymupdf` to create minimal synthetic PDFs for testing:

```python
import pymupdf, io

# Digital PDF
doc = pymupdf.open()
page = doc.new_page()
page.insert_text((72, 100), "Sample text for digital PDF fixture.", fontsize=14)
doc.save("tests/fixtures/digital.pdf")

# Scanned PDF – insert a raster image on a blank page
doc2 = pymupdf.open()
page2 = doc2.new_page()
# page2.insert_image(page2.rect, filename="some_scan.png")
doc2.save("tests/fixtures/scanned.pdf")
```

Alternatively, generate a PNG with Pillow, embed it into a PDF with PyMuPDF,
and save it as `scanned.pdf`.
