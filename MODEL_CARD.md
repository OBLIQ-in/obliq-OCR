# Model card: obliq-ocr

What obliq-ocr runs, what it was tested on, how well it did, and where it
fails. Last revised **5 November 2026**, against `main` at `111a83b`.

## What it is for

obliq-ocr pulls text out of the documents CA firms receive from clients: tax
invoices, bills, challans, e-way bills and compiled PDFs, either digital or
scanned. Its output is meant to be **checked by a person** before it reaches a
working paper or a filing.

It is not meant for handwriting, for documents in Hindi or other Indian
scripts, or for any decision made without human review.

## What runs inside

obliq-ocr has no model of its own. It decides page by page between two
existing engines (`docs/architecture.md`, added in #70, explains how it
decides):

| Component | Required | Version tested | Role | Licence |
|---|---|---|---|---|
| [PyMuPDF](https://pymupdf.readthedocs.io) | `>=1.24.0` | 1.28.2 | Reads the PDF text layer and renders pages for OCR | AGPL-3.0, or a commercial licence from Artifex |
| [rapidocr_onnxruntime](https://github.com/RapidAI/RapidOCR) | `>=1.3.18` | 1.4.4 | OCR pipeline, ships the models below | Apache-2.0 |
| [ONNX Runtime](https://onnxruntime.ai) | `>=1.17.0,<2.0.0` | 1.23.2 | Runs the models (CPU, or CUDA with `onnxruntime-gpu`) | MIT |

The models are PaddleOCR's PP-OCR models converted to ONNX and bundled inside
`rapidocr_onnxruntime` 1.4.4:

| Step | File | Size | SHA-256 |
|---|---|---|---|
| Find text lines | `ch_PP-OCRv4_det_infer.onnx` | 4.7 MB | `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9` |
| Detect upside-down lines | `ch_ppocr_mobile_v2.0_cls_infer.onnx` | 0.6 MB | `e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c` |
| Read each line | `ch_PP-OCRv4_rec_infer.onnx` | 10.9 MB | `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b` |

`pyproject.toml` only sets a minimum version for `rapidocr_onnxruntime`, so a
newer release could ship different model files. Compare the hashes above to
know whether this card still applies.

### What the reader model can output

The `ch_` models are PaddleOCR's Chinese and English models. The reader's
alphabet has 6,623 characters: Chinese characters, the Latin alphabet, digits
and common symbols. It does **not** include:

- `₹`: a printed rupee sign can't be read as `₹`.
- Any Devanagari or other Indian script: Hindi text can't be read.

Text-layer pages don't go through the model, so digital PDFs keep their `₹`
and Hindi text.

## Evaluation data

No real client documents were used for this card.

| Set | Size | Reference text | Used for |
|---|---|---|---|
| Synthetic invoice probe (`tests/scripts/model_card_probe.py`) | 1 made-up A4 tax invoice: 14 lines, 10 key values, scanned under 10 conditions | Yes, exact | OCR accuracy, effect of DPI and rotation |
| Benchmark set ([Kaggle](https://www.kaggle.com/datasets/rahulkate173/obliq-ocr-benchmarking-dataset), see [BENCHMARK.md](BENCHMARK.md)) | 4 PDFs, 10 pages: 2 scanned PDFs (5 pages), 2 digital PDFs (5 pages) | Only for the digital PDFs (their own text layer) | Speed, memory, comparison with other engines |
| CI fixtures (`tests/scripts/generate_fixtures.py`) | 4 tiny synthetic PDFs: digital, scanned, mixed, rotated | Yes | Regression gate on every PR |

The probe draws the invoice with PyMuPDF's built-in Helvetica, saves it as a
grey-scale image at the scan resolution (rotated where stated), and wraps it
in an image-only PDF so obliq-ocr has to OCR it. This is a clean, best-case
scan: real phone photos and photocopies will do worse.

## Results

### OCR accuracy (synthetic invoice probe)

Hardware: AMD Ryzen 7 7735HS (8 cores, 16 threads), 16 GB RAM, Windows 11,
Python 3.10.11, CPU only. Run with `python tests/scripts/model_card_probe.py`.
The accuracy columns are the same on every run; the times vary from run to
run by up to about half a second.

| Scan | CER | CER, spaces ignored | WER | Key values exact | Lines wrong | Confidence | Seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| 300 DPI | 18.7% | 15.4% | 50.8% | 10/10 | 1/14 | 0.98 | 3.05 |
| 200 DPI | 1.9% | 0.0% | 23.0% | 10/10 | 0/14 | 0.98 | 2.77 |
| 150 DPI | 17.4% | 14.9% | 52.5% | 10/10 | 1/14 | 0.94 | 2.11 |
| 100 DPI | 8.9% | 0.0% | 77.0% | 10/10 | 0/14 | 0.98 | 3.43 |
| 72 DPI | 18.0% | 15.9% | 44.3% | 9/10 | 3/14 | 0.98 | 3.50 |
| 200 DPI, 2° skew | 17.0% | 15.4% | 36.1% | 10/10 | 1/14 | 0.96 | 3.87 |
| 200 DPI, 5° skew | 17.2% | 16.1% | 36.1% | 10/10 | 4/14 | 0.98 | 3.90 |
| 200 DPI, 10° skew | 1.0% | 0.0% | 16.4% | 10/10 | 0/14 | 0.98 | 3.90 |
| 200 DPI, upside down | 72.2% | 74.3% | 86.9% | 9/10 | 2/14 | 0.98 | 3.11 |
| 200 DPI, rotated 90° | 2.9% | 0.0% | 41.0% | 10/10 | 0/14 | 0.99 | 2.92 |

Cold start (first call in a process, which loads the models): 4.6 s.

Key values are the two GSTINs, the invoice number, the date and six amounts.
A line is wrong if it isn't read exactly once spaces are ignored.

How to read this:

- **Characters are usually right; spaces often aren't.** The model drops
  spaces (`InvoiceDate:14/10/2026`, and at 100 DPI
  `HSN8471LaptopcomputersQty2…`). That alone explains the high WER at 100 DPI,
  where every character was correct.
- **The jumps around 15–18% CER are one missing line.** The longest line
  ("Amount in words: …", 75 characters) disappears completely at 300 DPI,
  150 DPI, 72 DPI and with 2° and 5° skew. It is not a confidence cut-off:
  lowering `OCR_MIN_SCORE` to 0 doesn't bring it back.
- **Low resolution changes amounts.** At 72 DPI, `1,03,750.00` came out as
  `1.03,750.00` and `9,337.50` as `9.337.50`, with confidence 0.98.
- **Skew mixes up letters and rows.** At 5° the model read `Sampie` and
  `lnvoice`, and two invoice rows were merged into one line.
- **Upside-down pages come out in reverse line order.** Each line is turned
  the right way up, but the page is read bottom to top, and one invoice row
  (`HSN 8443 … 12,750.00`) was lost. A 90° turn was read correctly in this
  test.

### Confidence is not an accuracy score

In every case above the page confidence stayed between 0.94 and 0.99,
including the cases with wrong amounts and missing lines. A high `confidence`
does not mean the text is right. Callers should still check key values, for
example the GSTIN checksum, and that line items add up to the total.

### Speed and memory (benchmark set)

From [BENCHMARK.md](BENCHMARK.md), CPU only. The CPU model, Python version and
DPI were not recorded for that run.

| Path | Seconds per page | Pages per second | Peak memory growth |
|---|---:|---:|---:|
| OCR (scanned PDFs) | 3.19 | 0.31 | 196 MB |
| Text layer (digital PDFs) | 0.024 | 42.4 | ~0 MB |

Cold start in that run was 1.10 s. There's no CER or WER for the scanned PDFs
there, because they had no reference text. For the digital PDFs, obliq-ocr
matched 100% of the words and numbers in the text layer. Its CER of 67.66%
against that same text layer is most likely word order, not wrong
characters, since every word matched.

An earlier run on an 8-page scanned invoice PDF on a Kaggle CPU notebook
(2 vCPU) took 29 seconds in total, with mean confidence 0.83.

The times on this card were measured with the duplicate page render that
exists on `main` today: every OCR page is rendered twice. Fixing that will
make OCR pages a little faster.

### CI regression gate

Every PR runs `tests/scripts/evaluate_accuracy.py` on the synthetic CI
fixtures and fails if CER goes above 5% or WER above 10%, and
`tests/scripts/benchmark_performance.py` warns if a fixture takes longer than
its time budget (1.5 s digital, 3.5 s scanned, 3.0 s mixed). These fixtures
are a few lines of large clean text, so passing them shows nothing broke, not
that real accuracy is high.

## Known limitations

| Limitation | Evidence |
|---|---|
| **No `₹` and no Indian scripts** in OCR | Not in the reader's alphabet (see above) |
| **Handwriting** is not supported | The PP-OCR models are trained on printed text. Not tested here. |
| **Low resolution** below about 100 DPI can change digits and separators | Probe at 72 DPI |
| **Skew** of a few degrees causes wrong letters and merged rows | Probe at 2° and 5° |
| **Upside-down pages** come out in reverse line order, and rows can be lost | Probe at 180° |
| **Long lines** can be dropped completely, with no warning | Probe, several cases |
| **Spaces** are often dropped inside a line | Probe, all cases |
| **Confidence** stays high when the text is wrong | Probe, all cases |
| **Text layers are trusted as-is.** A digital PDF with a wrong or hidden text layer is not checked by OCR | Design, see the architecture doc |
| **No coordinates** in the output yet | #71 |
| **Python 3.10–3.12 only.** `rapidocr_onnxruntime` doesn't install on 3.13 | Install attempt on 3.13 |

All accuracy numbers here come from one synthetic page and a 10-page
benchmark. Treat them as a rough guide, not a guarantee.

## Licences

The code in this repository is MIT. PyMuPDF is AGPL-3.0 unless a commercial
licence is bought from Artifex, which matters for a closed-source or hosted
product. #56 is auditing dependency and model licences.

## When this card is revised

Update this card, its date and the commit it was checked against when any of
these happen:

- A different version of `rapidocr_onnxruntime` is tested or required, or the
  model hashes change.
- `OCR_DPI`, `OCR_MIN_SCORE`, the triage thresholds or the line rebuilding
  change.
- A new benchmark is run, especially one with reference text for scanned pages.
- Before every release.

The PR that makes one of these changes should update the card in the same PR.
