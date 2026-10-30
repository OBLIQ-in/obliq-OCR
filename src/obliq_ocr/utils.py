"""
utils.py – Low-level helper utilities for the obliq-OCR pipeline.

Contains:
- ``words_to_lines``  : groups word-level boxes into visual reading-order lines.
- ``garbage_ratio``   : measures how much junk is in a PDF text layer.
- ``image_cover``     : fraction of a PDF page covered by embedded images.
- ``fit_image``       : downscale an ndarray so its longest side ≤ MAX_SIDE_PX.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

# ── knobs ────────────────────────────────────────────────────────────────────
COL_GAP_FACTOR: float = 1.0  # gap (in line-heights) that becomes " | "
MAX_SIDE_PX: int = 3200  # cap rendered page size
# ─────────────────────────────────────────────────────────────────────────────

# Type alias: (x0, y0, x1, y1, text)
WordBox = Tuple[float, float, float, float, str]


def words_to_lines(
    items: List[WordBox],
    gap_factor: float = COL_GAP_FACTOR,
) -> str:
    """Regroup word-level boxes into visual reading-order lines.

    Wide horizontal gaps between words on the same line become `` | `` so
    table columns are preserved when the text is fed to a downstream LLM.

    Parameters
    ----------
    items:
        List of ``(x0, y0, x1, y1, text)`` tuples in any order.
    gap_factor:
        Number of line-heights that constitutes a "column gap".  Default 1.0.

    Returns
    -------
    str
        Multi-line string, one visual row per line.
    """
    items = [it for it in items if it[4].strip()]
    if not items:
        return ""

    # Sort top-to-bottom, then left-to-right within a row
    items.sort(key=lambda t: ((t[1] + t[3]) / 2, t[0]))

    lines: List[List[WordBox]] = []
    cur: List[WordBox] = []
    cur_y: float = 0.0
    cur_h: float = 0.0

    for it in items:
        yc = (it[1] + it[3]) / 2
        h = max(it[3] - it[1], 1.0)
        if cur and abs(yc - cur_y) <= 0.6 * cur_h:
            cur.append(it)
            n = len(cur)
            cur_y = cur_y + (yc - cur_y) / n  # running mean
            cur_h = max(cur_h, h) if n < 3 else cur_h
        else:
            if cur:
                lines.append(cur)
            cur, cur_y, cur_h = [it], yc, h

    if cur:
        lines.append(cur)

    out: List[str] = []
    for ln in lines:
        ln.sort(key=lambda t: t[0])
        h = float(np.median([max(t[3] - t[1], 1.0) for t in ln]))
        s = ln[0][4]
        for prev, nxt in zip(ln, ln[1:]):
            gap = nxt[0] - prev[2]
            s += (" | " if gap > gap_factor * h else " ") + nxt[4]
        out.append(s.strip())

    return "\n".join(out)


def garbage_ratio(text: str) -> float:
    """Return the fraction of non-whitespace characters that are junk.

    "Junk" means:
    * Unicode replacement character ``\\ufffd``
    * Control characters (``ord < 32``)
    * Private-use Unicode range ``U+E000–U+F8FF``
    * ``(cid:…)`` sequences emitted by some PDF renderers (counted × 3)

    Parameters
    ----------
    text:
        Raw text extracted by PyMuPDF.

    Returns
    -------
    float
        Value in ``[0.0, 1.0]``; higher means more garbage.
    """
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 1.0
    bad = sum(1 for c in chars if c == "\ufffd" or (ord(c) < 32) or 0xE000 <= ord(c) <= 0xF8FF)
    bad += 3 * text.count("(cid:")
    return min(bad / len(chars), 1.0)


def image_cover(page) -> float:  # page: pymupdf.Page
    """Return the fraction of *page* area covered by embedded raster images.

    Parameters
    ----------
    page:
        A :class:`pymupdf.Page` object.

    Returns
    -------
    float
        Value in ``[0.0, 1.0]``.
    """
    import pymupdf  # local import keeps utils importable without pymupdf

    area = page.rect.width * page.rect.height
    if area <= 0:
        return 0.0
    try:
        covered = sum(
            pymupdf.Rect(i["bbox"]).intersect(page.rect).get_area() for i in page.get_image_info()
        )
    except Exception:
        return 0.0
    return min(covered / area, 1.0)


def fit_image(img: np.ndarray, max_side: int = MAX_SIDE_PX) -> np.ndarray:
    """Downscale *img* so its longest side is at most *max_side* pixels.

    Uses LANCZOS resampling.  Returns *img* unchanged if it already fits.

    Parameters
    ----------
    img:
        ``uint8`` NumPy array of shape ``(H, W, C)``.
    max_side:
        Maximum pixel dimension (height or width).

    Returns
    -------
    np.ndarray
        Possibly resized array, same dtype.
    """
    from PIL import Image  # local import

    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_side:
        return img
    s = max_side / m
    return np.array(Image.fromarray(img).resize((int(w * s), int(h * s)), Image.LANCZOS))


def is_blank_image(img: np.ndarray, std_threshold: float = 3.0) -> bool:
    """Return ``True`` if *img* looks like a blank (white/black) page.

    Parameters
    ----------
    img:
        RGB ``uint8`` NumPy array.
    std_threshold:
        Pages whose grayscale standard deviation is below this value are
        considered blank.  Default 3.0.
    """
    g = img.mean(axis=2)
    return bool(g.std() < std_threshold)
