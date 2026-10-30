"""
parser.py – Page-level triage and text extraction logic.

This module contains the per-page decision logic:

* :func:`triage_page`        – decides *text layer* vs *OCR* vs *blank*.
* :func:`text_layer_extract` – extracts words from PyMuPDF's text layer
                               and re-assembles them into reading-order lines.
* :func:`render_page`        – rasterises a PDF page to an RGB NumPy array.
* :func:`ocr_extract`        – runs RapidOCR and returns structured elements.
* :func:`iter_pages`         – yields ``(page_no, pdf_page, image_array)``
                               tuples for both PDF and standalone-image inputs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np

from obliq_ocr.schemas import TextElement
from obliq_ocr.utils import (
    WordBox,
    fit_image,
    garbage_ratio,
    image_cover,
    words_to_lines,
)

# ── knobs ────────────────────────────────────────────────────────────────────
OCR_DPI: int = 200  # 150 = faster, 300 = tiny print / poor scans
MIN_TEXT_CHARS: int = 40  # fewer non-space chars than this → treat page as scanned
GARBAGE_MAX: float = 0.15  # share of junk characters allowed before OCR fallback
IMG_COVER_MAX: float = 0.60  # page mostly covered by an image …
IMG_MIN_CHARS: int = 200  # … and not much real text → treat as scanned
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
# ─────────────────────────────────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# Page triage
# ---------------------------------------------------------------------------


def triage_page(page) -> Tuple[bool, str]:
    """Decide whether to use the PDF text layer or fall back to OCR.

    Parameters
    ----------
    page:
        A :class:`pymupdf.Page` object.

    Returns
    -------
    (use_text_layer, reason)
        ``use_text_layer=True`` means the digital text layer is usable;
        ``False`` means the page should be rasterised and OCR'd.
    """
    text = page.get_text("text")
    n = len(re.sub(r"\s", "", text))

    if n < MIN_TEXT_CHARS:
        return False, f"only {n} text chars"

    g = garbage_ratio(text)
    if g > GARBAGE_MAX:
        return False, f"garbled text layer ({g:.0%} junk)"

    cover = image_cover(page)
    if cover > IMG_COVER_MAX and n < IMG_MIN_CHARS:
        return False, f"full-page image + thin text ({n} chars)"

    return True, f"{n} chars, image cover {cover:.0%}"


# ---------------------------------------------------------------------------
# Digital text-layer extraction
# ---------------------------------------------------------------------------


def text_layer_extract(page) -> Tuple[str, List[TextElement]]:
    """Extract text from the PDF text layer and return (text, elements).

    Words are re-grouped into reading-order lines by :func:`words_to_lines`.
    Each word becomes a :class:`TextElement` with its bounding box; confidence
    is ``None`` because PyMuPDF does not supply a score.

    Parameters
    ----------
    page:
        A :class:`pymupdf.Page` object.

    Returns
    -------
    (text, elements)
        *text* is the full page text; *elements* contains per-word boxes.
    """
    raw_words = page.get_text("words")  # list of (x0, y0, x1, y1, word, …)
    word_boxes: List[WordBox] = [(w[0], w[1], w[2], w[3], w[4]) for w in raw_words]

    elements: List[TextElement] = [
        TextElement(
            text=wb[4],
            bbox=[wb[0], wb[1], wb[2], wb[3]],
            confidence=None,
        )
        for wb in word_boxes
    ]
    text = words_to_lines(word_boxes)
    return text, elements


# ---------------------------------------------------------------------------
# Rasterisation
# ---------------------------------------------------------------------------


def render_page(page) -> np.ndarray:
    """Rasterise *page* to an RGB NumPy array at :data:`OCR_DPI`.

    The result is downscaled if its longest side exceeds
    :data:`obliq_ocr.utils.MAX_SIDE_PX`.

    Parameters
    ----------
    page:
        A :class:`pymupdf.Page` object.

    Returns
    -------
    np.ndarray
        ``uint8`` array of shape ``(H, W, 3)``.
    """
    import pymupdf  # local import so the module is importable without pymupdf

    pix = page.get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    return fit_image(img)


# ---------------------------------------------------------------------------
# OCR extraction
# ---------------------------------------------------------------------------


def ocr_extract(
    img: np.ndarray,
    ocr_engine,
) -> Tuple[str, List[TextElement], Optional[float]]:
    """Run RapidOCR on *img* and return ``(text, elements, mean_confidence)``.

    Bounding boxes are converted from the quad format returned by PP-OCR
    (four ``[x, y]`` corner points) to axis-aligned ``[x0, y0, x1, y1]``.

    Parameters
    ----------
    img:
        ``uint8`` RGB NumPy array.
    ocr_engine:
        A :class:`rapidocr_onnxruntime.RapidOCR` instance.

    Returns
    -------
    (text, elements, mean_confidence)
        *text* is the full page text; *elements* contains per-box results;
        *mean_confidence* is the mean score across all boxes, or ``None``
        if no boxes were detected.
    """
    result, _ = ocr_engine(img)
    if not result:
        return "", [], None

    items: List[WordBox] = []
    elements: List[TextElement] = []
    scores: List[float] = []

    for box, txt, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        items.append((x0, y0, x1, y1, txt))
        elements.append(
            TextElement(
                text=txt,
                bbox=[x0, y0, x1, y1],
                confidence=float(score),
            )
        )
        scores.append(float(score))

    text = words_to_lines(items)
    mean_conf = float(np.mean(scores)) if scores else None
    return text, elements, mean_conf


# ---------------------------------------------------------------------------
# Multi-format page iterator
# ---------------------------------------------------------------------------


def iter_pages(
    path: Path,
) -> Iterator[Tuple[int, object, Optional[np.ndarray]]]:
    """Yield ``(page_no, pdf_page_or_None, image_array_or_None)`` for every page.

    Handles:
    * Multi-page PDFs (via PyMuPDF)
    * Single or multi-frame image files (JPEG, PNG, TIFF, …)
    * Password-protected PDFs → raises :class:`ValueError`

    Parameters
    ----------
    path:
        Path to the input file.

    Yields
    ------
    (page_no, page, img)
        *page_no* is 1-indexed.  Exactly one of *page* or *img* is not ``None``.
    """
    from PIL import Image, ImageOps, ImageSequence  # local import

    if path.suffix.lower() in IMG_EXTENSIONS:
        im = Image.open(path)
        for i, frame in enumerate(ImageSequence.Iterator(im), start=1):
            frame = ImageOps.exif_transpose(frame.convert("RGB"))
            yield i, None, fit_image(np.array(frame))
    else:
        import pymupdf  # local import

        doc = pymupdf.open(str(path))
        if doc.needs_pass:
            raise ValueError(f"{path.name!r} is password-protected.")
        for i, page in enumerate(doc, start=1):
            yield i, page, None
