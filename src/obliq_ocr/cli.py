"""
cli.py – Command-line interface for obliq-OCR.

Usage
-----
::

    python -m obliq_ocr path/to/document.pdf
    python -m obliq_ocr path/to/scan.jpg --device cpu --output-dir results/
    python -m obliq_ocr path/to/doc.pdf --quiet

This is also exposed as the ``obliq-ocr`` console script (see pyproject.toml).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obliq-ocr",
        description="Page-aware OCR and document parsing pipeline (PyMuPDF + RapidOCR).",
    )
    p.add_argument(
        "input",
        metavar="FILE",
        help="PDF or image file to process.",
    )
    p.add_argument(
        "--output-dir",
        default="outputs",
        metavar="DIR",
        help="Directory to write JSON and TXT output files. Default: outputs/",
    )
    p.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Compute device for OCR inference. Default: auto",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-page progress output.",
    )
    return p


def main(argv=None):
    args = _build_parser().parse_args(argv)

    from obliq_ocr.core import extract_document, save_result  # lazy import

    input_path = Path(args.input)
    force_device = None if args.device == "auto" else args.device

    t0 = time.perf_counter()
    try:
        result = extract_document(
            input_path,
            force_device=force_device,
            verbose=not args.quiet,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    total = time.perf_counter() - t0

    n_ocr = sum(p.method == "ocr" for p in result.pages)
    n_text = sum(p.method == "text_layer" for p in result.pages)
    n_blank = sum(p.method == "blank" for p in result.pages)

    print(
        f"\n{len(result.pages)} pages | {n_ocr} OCR | {n_text} text layer "
        f"| {n_blank} blank | {total:.2f}s total on {result.device}"
    )

    json_path, txt_path = save_result(result, out_dir=args.output_dir)
    print(f"saved: {json_path}  {txt_path}")


if __name__ == "__main__":
    main()
