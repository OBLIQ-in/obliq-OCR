# obliq-OCR

> **High-performance, page-aware OCR and document-parsing pipeline** combining
> [PyMuPDF](https://pymupdf.readthedocs.io) and
> [RapidOCR](https://rapidai.github.io/RapidOCRDocs/) (PP-OCR / ONNX Runtime),
> built for automated tax-compliance document processing at OBLIQ.

---

## Table of Contents

1. [How it works](#how-it-works)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Quick start](#quick-start)
5. [CLI usage](#cli-usage)
6. [Output schema](#output-schema)
7. [Model details](#model-details)
8. [Testing](#testing)
9. [Known limitations](#known-limitations)
10. [Project structure](#project-structure)

---

## How it works

The pipeline processes documents **page by page**:

| Step | Action |
|------|--------|
| **Triage** | Is there a usable text layer? Is it garbled? Is the page a full-page image? Is it blank? |
| **Digital page** | Extract text directly from the PDF text layer via PyMuPDF (~milliseconds). |
| **Scanned page** | Rasterise the page at 200 DPI and run PP-OCR models via RapidOCR on ONNX Runtime. |
| **Layout rebuild** | Word-level boxes are regrouped into visual reading-order lines; wide gaps become ` \| ` so table rows remain intact. |
| **Output** | Per-page text + method + confidence + timing, returned as a `DocResult` and optionally saved as JSON + TXT. |

Mixed files (some pages digital, some scanned) are handled naturally because the decision is made on a per-page basis.

---

## Requirements

| Dependency | Minimum version | Notes |
|---|---|---|
| Python | 3.10 | Tested on 3.10 – 3.13 |
| PyMuPDF | 1.24.0 | PDF rendering and text extraction |
| rapidocr-onnxruntime | 1.3.18 | OCR engine with bundled PP-OCR ONNX models |
| onnxruntime | 1.17.0 | CPU inference runtime |
| Pillow | 10.0.0 | Image preprocessing |
| NumPy | 1.24.0 | Array operations |

For GPU (CUDA) inference, install the `[gpu]` extra (see below).

---

## Installation

### From source (development)

```bash
# 1. Clone the repository and switch to the feature branch
git clone https://github.com/rahulkate173/obliq-OCR.git
cd obliq-OCR
git switch feat/initial-ocr-pipeline

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install the package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### GPU (CUDA) support

If you have an NVIDIA GPU with CUDA:

```bash
# Uninstall the CPU onnxruntime first (the two builds conflict)
pip uninstall onnxruntime -y
pip install "obliq-ocr[gpu]"
```

Set `OBLIQ_OCR_DEVICE=cuda` or pass `force_device="cuda"` to use it.

---

## Quick start

```python
from obliq_ocr import parse_document

# Works with PDFs (digital, scanned, or mixed) and images (JPEG, PNG, TIFF, …)
result = parse_document("invoice.pdf")

# Print all pages
print(result.full_text())

# Access structured per-page data
for page in result.pages:
    print(f"Page {page.page}: method={page.method}, chars={page.n_chars}, conf={page.confidence}")

# Save JSON + TXT to disk
from obliq_ocr import save_result
save_result(result, out_dir="outputs/")
```

### Force device

```python
result = parse_document("scan.pdf", force_device="cpu")   # always CPU
result = parse_document("scan.pdf", force_device="cuda")  # require GPU
# or via environment variable:
# OBLIQ_OCR_DEVICE=cuda python my_script.py
```

---

## CLI usage

```bash
# Basic usage
obliq-ocr invoice.pdf

# Specify output directory and device
obliq-ocr scan.pdf --output-dir results/ --device cpu

# Suppress per-page progress
obliq-ocr document.pdf --quiet

# Or invoke as a module
python -m obliq_ocr invoice.pdf
```

---

## Output schema

`parse_document()` returns a `DocResult`. Calling `.to_dict()` gives:

```json
{
  "source": "invoice.pdf",
  "device": "CPU",
  "pages": [
    {
      "page": 1,
      "method": "ocr",
      "reason": "only 3 text chars",
      "text": "Invoice Number: 12345 | Amount: ₹50,000",
      "n_chars": 38,
      "confidence": 0.87,
      "seconds": 2.65
    },
    {
      "page": 2,
      "method": "text_layer",
      "reason": "412 chars, image cover 0%",
      "text": "Terms and conditions ...",
      "n_chars": 412,
      "confidence": null,
      "seconds": 0.003
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `page` | int | 1-indexed page number |
| `method` | str | `"text_layer"`, `"ocr"`, or `"blank"` |
| `reason` | str | Why that method was chosen |
| `text` | str | Extracted text; column gaps → ` \| ` |
| `n_chars` | int | Character count of `text` |
| `confidence` | float \| null | Mean PP-OCR score [0, 1]; `null` for text-layer pages |
| `seconds` | float | Wall-clock processing time for this page |

**Coordinate system (elements):** Bounding boxes are `[x0, y0, x1, y1]`.
For digital pages, units are PDF *points* (1/72 inch), origin at the top-left corner.
For scanned pages, units are *pixels* at the configured render DPI (default 200).
Page numbering is **1-indexed**.

---

## Model details

| Sub-model | File | Size | Source | License |
|---|---|---|---|---|
| PP-OCRv4 Detection | `ch_PP-OCRv4_det_infer.onnx` | ~4 MB | [RapidOCR releases](https://github.com/RapidAI/RapidOCR/releases) | Apache 2.0 |
| PP-OCRv4 Classification | `ch_ppocr_mobile_v2.0_cls_infer.onnx` | ~1 MB | [RapidOCR releases](https://github.com/RapidAI/RapidOCR/releases) | Apache 2.0 |
| PP-OCRv4 Recognition | `ch_PP-OCRv4_rec_infer.onnx` | ~12 MB | [RapidOCR releases](https://github.com/RapidAI/RapidOCR/releases) | Apache 2.0 |

**All three models are bundled inside the `rapidocr_onnxruntime` package**
and are downloaded automatically by `pip install rapidocr_onnxruntime`.
No manual model download is required. Total additional disk size: ~17 MB.
No model files > 50 MB are committed to this repository.

---

## Testing

```bash
# Run all tests (some fixture-based tests are skipped on a clean clone)
pytest

# Run with coverage report
pytest --cov=obliq_ocr --cov-report=term-missing

# Run only the fast smoke + unit tests
pytest tests/test_pipeline.py -k "Imports or Unit or Blank or Digital"
```

### Adding real fixture PDFs

Place anonymised or synthetic PDF files in `tests/fixtures/`:

| File | What it tests |
|---|---|
| `digital.pdf` | Text extraction from native PDF text layer |
| `scanned.pdf` | OCR on rasterised page images |
| `mixed.pdf` | Handling of pages with both methods |
| `rotated.pdf` | Text extraction on rotated pages |

See `tests/fixtures/README.md` for rules. **No real client documents or PII.**

### Test results (Kaggle CPU, Oct 2026)

Tested on an 8-page scanned invoice PDF (Mix of LR No., E-Way Bill, Tax Invoice, Delivery Challan):

| Metric | Value |
|---|---|
| Pages | 8 |
| OCR pages | 8 |
| Total time | 29 s (CPU) |
| Mean confidence | 0.83 |
| Hardware | Kaggle CPU notebook (2 vCPU, no GPU) |

No formal CER/WER benchmark has been run yet. Visual inspection of output showed high accuracy on printed documents; handwriting and low-DPI scans are not supported.

---

## Known limitations

- **Handwriting** is not supported. PP-OCR is trained on printed text.
- **Low-DPI scans** (< 100 DPI) may produce poor results. Increase `OCR_DPI` in `parser.py` if needed.
- **Rotated pages** – PyMuPDF handles page rotation metadata automatically, but extreme skew (not multiples of 90°) will reduce OCR accuracy.
- **Complex layouts** (multi-column magazines, tables with merged cells) are approximated by the ` | ` column separator.
- **Right-to-left scripts** (Arabic, Hebrew) are not explicitly handled.
- **Password-protected PDFs** raise a `ValueError`.
- **GPU support** requires manually swapping `onnxruntime` for `onnxruntime-gpu`.

---

## Project structure

```
obliq-OCR/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/
│   └── obliq_ocr/
│       ├── __init__.py      # Public API + version
│       ├── __main__.py      # python -m obliq_ocr
│       ├── cli.py           # obliq-ocr console script
│       ├── core.py          # Main pipeline (DocResult, extract_document, save_result)
│       ├── engine.py        # OCR engine init & device detection
│       ├── parser.py        # Per-page triage, text extraction, OCR
│       ├── schemas.py       # Typed output schema (DocumentOutput, PageOutput, …)
│       └── utils.py         # words_to_lines, garbage_ratio, image helpers
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (synthetic + file-based)
│   ├── test_pipeline.py     # All tests
│   └── fixtures/            # Anonymised / synthetic PDFs (not committed)
│       ├── README.md
│       ├── digital.pdf      # ← add before full test run
│       ├── scanned.pdf      # ← add before full test run
│       ├── mixed.pdf        # ← add before full test run
│       └── rotated.pdf      # ← add before full test run
└── docs/                    # (planned) benchmarks and additional docs
```

---

## License

MIT © 2026 Rahul Kate / OBLIQ
