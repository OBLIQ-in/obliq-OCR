"""
schemas.py – Structured output types for the obliq-OCR pipeline.

These dataclasses define the public output schema returned by
:func:`obliq_ocr.parse_document`.  All fields are serialisable via
:func:`dataclasses.asdict`.

Output schema
-------------
.. code-block:: json

    {
        "file_name": "invoice.pdf",
        "device": "CPU",
        "pages": [
            {
                "page_number": 1,
                "method": "ocr",
                "reason": "only 3 text chars",
                "confidence": 0.87,
                "processing_seconds": 2.65,
                "elements": [
                    {
                        "text": "Invoice Number: 12345",
                        "bbox": [50.0, 80.0, 300.0, 110.0],
                        "confidence": 0.98
                    }
                ],
                "text": "Invoice Number: 12345"
            }
        ]
    }

Coordinate system
-----------------
All bounding boxes use ``[x0, y0, x1, y1]`` in *points* (1/72 inch) for
digital pages, and in *pixels* at the configured render DPI for scanned
pages.  ``x0/y0`` is the top-left corner; ``x1/y1`` is the bottom-right.
Page numbering is **1-indexed** (first page = 1).

Confidence scores
-----------------
``confidence`` is the mean score across all RapidOCR boxes on the page
(range 0.0–1.0). It is ``null`` (``None``) for digital pages that were
extracted directly from the PDF text layer, because PyMuPDF does not
produce a confidence value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class BoundingBox:
    """Axis-aligned bounding box ``[x0, y0, x1, y1]``."""

    x0: float
    y0: float
    x1: float
    y1: float

    def as_list(self) -> List[float]:
        """Return ``[x0, y0, x1, y1]`` for JSON serialisation."""
        return [self.x0, self.y0, self.x1, self.y1]


@dataclass
class TextElement:
    """A single text region (word group / OCR box) on a page.

    Parameters
    ----------
    text:
        Extracted text string.
    bbox:
        ``[x0, y0, x1, y1]`` bounding box (see module docstring for units).
    confidence:
        Model confidence in range ``[0, 1]``, or ``None`` for text-layer
        elements where PyMuPDF does not supply a score.
    """

    text: str
    bbox: List[float]  # [x0, y0, x1, y1]
    confidence: Optional[float] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class PageOutput:
    """Structured result for a single page.

    Parameters
    ----------
    page_number:
        1-indexed page number.
    method:
        How text was extracted: ``"text_layer"``, ``"ocr"``, or ``"blank"``.
    reason:
        Human-readable explanation of why that method was chosen, e.g.
        ``"only 3 text chars"`` or ``"garbled text layer (20% junk)"``.
    text:
        Full page text, re-assembled into reading order. Column gaps are
        represented as `` | `` so table rows remain readable.
    elements:
        Individual text regions with bounding boxes and per-element
        confidence scores.  Empty list for blank pages.
    confidence:
        Mean OCR confidence for the page (``None`` for text-layer pages).
    processing_seconds:
        Wall-clock time to process this page.
    """

    page_number: int
    method: str  # "text_layer" | "ocr" | "blank"
    reason: str
    text: str
    elements: List[TextElement] = field(default_factory=list)
    confidence: Optional[float] = None
    processing_seconds: float = 0.0

    def to_dict(self):
        d = asdict(self)
        return d


@dataclass
class DocumentOutput:
    """Top-level structured output for a parsed document.

    Parameters
    ----------
    file_name:
        Base name of the source file (no directory path).
    device:
        Compute device used for OCR: ``"CPU"`` or ``"CUDA"``.
    pages:
        Ordered list of :class:`PageOutput` objects, one per page.
    """

    file_name: str
    device: str
    pages: List[PageOutput] = field(default_factory=list)

    def full_text(self) -> str:
        """Concatenate all pages into a single string with page headers."""
        parts = [f"===== PAGE {p.page_number} [{p.method}] =====\n{p.text}" for p in self.pages]
        return "\n\n".join(parts)

    def to_dict(self):
        return asdict(self)
