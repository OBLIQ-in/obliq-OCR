"""Synthetic accuracy probe for MODEL_CARD.md.

Draws a made-up tax invoice with PyMuPDF's built-in Helvetica font, turns it
into an image-only "scan" at several resolutions and angles, runs obliq-ocr on
each one, and compares the result with the known text.

No real documents are used: every name, GSTIN and amount below is invented.

Run from the repo root (needs the ``test`` extra for jiwer):

    python tests/scripts/model_card_probe.py
"""

from __future__ import annotations

import io
import os
import platform
import re
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("OBLIQ_OCR_DEVICE", "cpu")

import pymupdf  # noqa: E402
from jiwer import cer, wer  # noqa: E402
from PIL import Image  # noqa: E402

from obliq_ocr import parse_document  # noqa: E402

# Single column, so the reading order is unambiguous.
LINES = [
    "TAX INVOICE",
    "Sample Traders Pvt Ltd",
    "GSTIN: 27AAACS1234F1Z5",
    "Invoice No: INV-2026-0457",
    "Invoice Date: 14/10/2026",
    "Bill To: Example Retail LLP",
    "Buyer GSTIN: 29AABCE5678K1Z2",
    "HSN 8471 Laptop computers Qty 2 Rate 45,500.00 Amount 91,000.00",
    "HSN 8443 Laser printer Qty 1 Rate 12,750.00 Amount 12,750.00",
    "Taxable Value: Rs. 1,03,750.00",
    "CGST @ 9%: Rs. 9,337.50",
    "SGST @ 9%: Rs. 9,337.50",
    "Total Invoice Value: Rs. 1,22,425.00",
    "Amount in words: One Lakh Twenty Two Thousand Four Hundred Twenty Five Only",
]
REFERENCE = "\n".join(LINES)

# Values a reviewer would copy into a working paper. Each must be read exactly.
KEY_FIELDS = [
    "27AAACS1234F1Z5",
    "29AABCE5678K1Z2",
    "INV-2026-0457",
    "14/10/2026",
    "45,500.00",
    "91,000.00",
    "12,750.00",
    "1,03,750.00",
    "9,337.50",
    "1,22,425.00",
]

# (label, scan DPI, rotation in degrees counter-clockwise)
CASES = [
    ("300 DPI", 300, 0),
    ("200 DPI", 200, 0),
    ("150 DPI", 150, 0),
    ("100 DPI", 100, 0),
    ("72 DPI", 72, 0),
    ("200 DPI, 2 deg skew", 200, 2),
    ("200 DPI, 5 deg skew", 200, 5),
    ("200 DPI, 10 deg skew", 200, 10),
    ("200 DPI, upside down", 200, 180),
    ("200 DPI, rotated 90", 200, 90),
]


def digital_page() -> pymupdf.Document:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 in points
    y = 72.0
    for i, line in enumerate(LINES):
        page.insert_text((60, y), line, fontname="helv", fontsize=16 if i == 0 else 11)
        y += 26
    return doc


def scanned_pdf(src: pymupdf.Document, dpi: int, angle: int) -> bytes:
    pix = src[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
    img = Image.frombytes("L", (pix.w, pix.h), pix.samples)
    if angle:
        img = img.rotate(angle, expand=True, fillcolor=255)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Keep the page the same physical size as the image at its scan DPI.
    width, height = img.width * 72 / dpi, img.height * 72 / dpi
    out = pymupdf.open()
    out.new_page(width=width, height=height).insert_image(
        pymupdf.Rect(0, 0, width, height), stream=buf.getvalue()
    )
    return out.tobytes()


def normalise(text: str) -> str:
    text = text.replace(" | ", " ")
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def squash(text: str) -> str:
    return re.sub(r"\s", "", text)


def key_fields_found(hypothesis: str) -> int:
    # Spaces are ignored: the OCR model often drops them ("Rs.9,337.50").
    return sum(value in squash(hypothesis) for value in KEY_FIELDS)


def lines_wrong(hypothesis: str) -> int:
    return sum(squash(line) not in squash(hypothesis) for line in LINES)


def main() -> None:
    print("CPU:", platform.processor() or platform.machine(), f"| {os.cpu_count()} logical CPUs")
    print("Python", platform.python_version(), "|", platform.system(), platform.release())
    for pkg in ("obliq-ocr", "pymupdf", "rapidocr_onnxruntime", "onnxruntime"):
        print(f"  {pkg} {version(pkg)}")
    print()

    src = digital_page()
    with tempfile.TemporaryDirectory() as tmp:
        warm = Path(tmp) / "warmup.pdf"
        warm.write_bytes(scanned_pdf(src, 150, 0))
        t0 = time.perf_counter()
        parse_document(warm, verbose=False)
        print(f"Cold start (first call, loads the models): {time.perf_counter() - t0:.2f} s\n")

        print(
            f"{'Case':<24}{'CER':>7}{'CER*':>7}{'WER':>7}"
            f"{'Key fields':>12}{'Lines wrong':>13}{'Conf':>6}{'s/page':>8}"
        )
        for label, dpi, angle in CASES:
            path = Path(tmp) / "case.pdf"
            path.write_bytes(scanned_pdf(src, dpi, angle))
            page = parse_document(path, verbose=False).pages[0]
            hyp = normalise(page.text)
            conf = f"{page.confidence:.2f}" if page.confidence is not None else "n/a"
            keys = f"{key_fields_found(hyp)}/{len(KEY_FIELDS)}"
            wrong = f"{lines_wrong(hyp)}/{len(LINES)}"
            print(
                f"{label:<24}{cer(REFERENCE, hyp):>7.1%}"
                f"{cer(squash(REFERENCE), squash(hyp)):>7.1%}{wer(REFERENCE, hyp):>7.1%}"
                f"{keys:>12}{wrong:>13}{conf:>6}{page.seconds:>8.2f}"
            )
    print(
        "\nCER* ignores spaces. Key fields and lines are matched with spaces ignored;"
        " a line is wrong if it isn't read exactly."
    )


if __name__ == "__main__":
    main()
