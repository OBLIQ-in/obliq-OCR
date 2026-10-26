"""
obliq_ocr – Page-aware OCR and document parsing pipeline.

Combines PyMuPDF (digital text layer) with RapidOCR (PP-OCR / ONNX Runtime)
to extract structured text from PDFs and images on a per-page basis.

Quick start
-----------
>>> from obliq_ocr import parse_document
>>> result = parse_document("invoice.pdf")
>>> print(result.full_text())
"""

from obliq_ocr.core import DocResult, PageResult, save_result
from obliq_ocr.core import extract_document as parse_document  # primary public API
from obliq_ocr.engine import build_ocr, detect_device
from obliq_ocr.schemas import BoundingBox, DocumentOutput, PageOutput

__all__ = [
    # Primary entrypoint
    "parse_document",
    # Result objects
    "DocResult",
    "PageResult",
    "save_result",
    # Engine helpers
    "build_ocr",
    "detect_device",
    # Schema / output types
    "DocumentOutput",
    "PageOutput",
    "BoundingBox",
]

__version__ = "0.1.0"
