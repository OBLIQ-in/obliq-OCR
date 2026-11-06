# obliq-ocr

[![CI](https://github.com/OBLIQ-in/obliq-OCR/actions/workflows/ci.yml/badge.svg)](https://github.com/OBLIQ-in/obliq-OCR/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/obliq-ocr)](https://pypi.org/project/obliq-ocr/)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://github.com/OBLIQ-in/obliq-OCR/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/OBLIQ-in/obliq-OCR/blob/main/pyproject.toml)

Pulls the text out of PDFs and scans, one page at a time. Pages that already
have digital text are read straight from the PDF in milliseconds; scanned
pages go through OCR ([RapidOCR](https://github.com/RapidAI/RapidOCR), PP-OCRv4
on ONNX Runtime). A file that mixes both is handled without any settings.

It was built at [OBLIQ](https://github.com/OBLIQ-in) for the documents CA
firms get from their clients: tax invoices, bills, challans, e-way bills and
compiled PDFs. It's for Python developers who need that text as plain strings
or JSON, and its output is meant to be checked by a person before it's used.

## Install

```bash
pip install obliq-ocr
```

- **Python 3.10, 3.11 or 3.12.** The OCR engine doesn't install on 3.13 yet.
- **Linux and Windows** are tested. macOS should work but isn't tested.
- Runs on CPU. For an NVIDIA GPU, see [GPU](#gpu).

If you want to directly use it from GitHub:

```bash
pip install "git+https://github.com/OBLIQ-in/obliq-OCR.git"
```

## Quickstart

<!-- quickstart: tests/test_readme.py runs this block exactly as written -->
```python
from obliq_ocr import parse_document, save_result

result = parse_document("invoice.pdf")  # a PDF or an image

for page in result.pages:
    print(page.page, page.method, page.confidence)

print(result.full_text())
save_result(result, out_dir="outputs")  # outputs/invoice.json and outputs/invoice.txt
```

`parse_document` prints one progress line per page; pass `verbose=False` to
turn that off.

## Supported files

| Type | Extensions | Notes |
|---|---|---|
| PDF | `.pdf` | Digital, scanned or mixed. Password-protected PDFs raise `ValueError`. |
| Images | `.jpg` `.jpeg` `.png` `.bmp` `.tif` `.tiff` `.webp` | Each frame of a multi-page TIFF is a page. Phone photos are turned upright using their EXIF data. |

## Sample output

`save_result` writes this JSON (the same as `result.to_dict()`). This is the
real output for a two-page test PDF where page 1 is digital and page 2 is a
scan:

```json
{
  "source": "invoice.pdf",
  "device": "CPU",
  "pages": [
    {
      "page": 1,
      "method": "text_layer",
      "reason": "97 chars, image cover 0%",
      "text": "Mixed document digital page.\nThis page contains native text layer elements.\nIt should be extracted via text layer.",
      "n_chars": 114,
      "confidence": null,
      "seconds": 0.018
    },
    {
      "page": 2,
      "method": "ocr",
      "reason": "only 0 text chars",
      "text": "Mixed document scanned page.",
      "n_chars": 28,
      "confidence": 1.0,
      "seconds": 0.516
    }
  ]
}
```

`method` is `text_layer`, `ocr` or `blank`. `confidence` is the average OCR
score from 0 to 1, and `null` for pages that weren't OCR'd. Every field and
error is explained in the
[architecture doc](https://github.com/OBLIQ-in/obliq-OCR/blob/main/docs/architecture.md).

## Command line

```bash
obliq-ocr invoice.pdf                                   # writes outputs/invoice.json and .txt
obliq-ocr scan.pdf --output-dir results --device cpu    # choose folder and device
obliq-ocr scan.pdf --quiet                              # no per-page progress
python -m obliq_ocr invoice.pdf                         # same thing, as a module
```

## GPU

```bash
pip uninstall -y onnxruntime
pip install "obliq-ocr[gpu]"
```

The CPU and GPU builds of ONNX Runtime can't be installed together, which is
why the first command is needed. obliq-ocr uses CUDA when it's available; set
`OBLIQ_OCR_DEVICE=cpu` or `cuda`, or pass `force_device="cpu"` or `"cuda"`, to
choose.

## Limitations

The [model card](https://github.com/OBLIQ-in/obliq-OCR/blob/main/MODEL_CARD.md)
has the measurements. In short:

- Scanned pages can't produce `₹` or Hindi and other Indian scripts. Digital
  PDFs keep them.
- Handwriting isn't supported.
- Low-resolution or skewed scans can change digits and drop whole lines.
- A high `confidence` doesn't mean the text is right: check key values.
- The output has no coordinates yet ([#71](https://github.com/OBLIQ-in/obliq-OCR/issues/71)).

## Documentation

- [Architecture and output schema](https://github.com/OBLIQ-in/obliq-OCR/blob/main/docs/architecture.md): how pages are routed, every output field, errors
- [Model card](https://github.com/OBLIQ-in/obliq-OCR/blob/main/MODEL_CARD.md): models, versions, measured accuracy, limitations
- [Benchmark](BENCHMARK.md): speed and memory against other OCR engines
- [Changelog](https://github.com/OBLIQ-in/obliq-OCR/blob/main/CHANGELOG.md)
- [Release guide](https://github.com/OBLIQ-in/obliq-OCR/blob/main/docs/RELEASE_GUIDE.md), for maintainers
- [Security policy](https://github.com/OBLIQ-in/obliq-OCR/blob/main/SECURITY.md): how to report a vulnerability privately

## Contributing

```bash
git clone https://github.com/OBLIQ-in/obliq-OCR.git
cd obliq-OCR
python -m venv .venv            # Python 3.10 to 3.12
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev,test]"
pre-commit install
python tests/scripts/generate_fixtures.py   # synthetic test PDFs
pytest
```

- Branch off `main` and open a PR. PR titles follow
  [Conventional Commits](https://www.conventionalcommits.org) (`docs: …`,
  `fix: …`, `feat: …`). If the PR has a single commit, its message must follow
  the same format.
- CI runs ruff, mypy, the tests on Python 3.10 to 3.12, an accuracy gate and a
  link check.
- Never commit real client documents or anything with personal data. Test
  files must be synthetic or fully anonymised.

Questions and bugs go to [GitHub issues](https://github.com/OBLIQ-in/obliq-OCR/issues).

## License

obliq-OCR is MIT-licensed. PyMuPDF, used for PDF extraction and rendering, is
separately dual-licensed under AGPL-3.0 or an Artifex commercial license. We
keep PyMuPDF and use it under the AGPL-3.0 option for our open-source
distribution. We will meet the AGPL-3.0 obligations that apply to distribution
and service use, including offering corresponding source to users interacting
with a modified program over a network where required by section 13. Closed-
source use that cannot meet those terms requires an Artifex commercial license.

See [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES) for the recorded decision,
dependency license inventory, and OCR model notices.
