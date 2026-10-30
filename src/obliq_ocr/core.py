"""
core.py – Main pipeline orchestration for the obliq-OCR package.

Public API
----------
:func:`extract_document` (aliased as ``parse_document`` in ``__init__.py``)
    Parse a PDF or image file and return a :class:`DocResult`.

:class:`DocResult` / :class:`PageResult`
    Lightweight result dataclasses retained for backwards-compatibility
    with the original notebook output format.  The richer typed schema is
    in :mod:`obliq_ocr.schemas`.

:func:`save_result`
    Write JSON and plain-text representations to disk.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from obliq_ocr.engine import detect_device, get_ocr_engine
from obliq_ocr.parser import (
    iter_pages,
    ocr_extract,
    render_page,
    text_layer_extract,
    triage_page,
)
from obliq_ocr.utils import is_blank_image

# ---------------------------------------------------------------------------
# Result dataclasses  (notebook-compatible)
# ---------------------------------------------------------------------------


@dataclass
class PageResult:
    """Per-page extraction result.

    Parameters
    ----------
    page:
        1-indexed page number.
    method:
        ``"text_layer"``, ``"ocr"``, or ``"blank"``.
    reason:
        Human-readable triage reason.
    text:
        Extracted text (reading-order, columns separated by `` | ``).
    n_chars:
        Character count of *text*.
    confidence:
        Mean OCR confidence in ``[0, 1]``, or ``None`` for text-layer pages.
    seconds:
        Wall-clock processing time for this page.
    """

    page: int
    method: str
    reason: str
    text: str
    n_chars: int
    confidence: Optional[float]
    seconds: float


@dataclass
class DocResult:
    """Top-level result for a parsed document.

    Parameters
    ----------
    source:
        Base filename of the input document.
    device:
        ``"CPU"`` or ``"CUDA"``.
    pages:
        Ordered list of :class:`PageResult` objects.
    """

    source: str
    device: str
    pages: List[PageResult] = field(default_factory=list)

    def full_text(self) -> str:
        """Return all pages concatenated with page-number headers."""
        parts = [f"===== PAGE {p.page} [{p.method}] =====\n{p.text}" for p in self.pages]
        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "device": self.device,
            "pages": [asdict(p) for p in self.pages],
        }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def extract_document(
    path,
    *,
    force_device: Optional[str] = None,
    verbose: bool = True,
) -> DocResult:
    """Parse a PDF or image file and return a :class:`DocResult`.

    This is the primary public entrypoint, aliased as ``parse_document``
    in :mod:`obliq_ocr.__init__`.

    Parameters
    ----------
    path:
        ``str`` or :class:`pathlib.Path` pointing to the document to parse.
        Supported formats: PDF, JPEG, PNG, TIFF, BMP, WebP.
    force_device:
        ``"cpu"``, ``"cuda"``, or ``None`` (auto-detect).  Overrides the
        ``OBLIQ_OCR_DEVICE`` environment variable.
    verbose:
        Print per-page progress to stdout.  Default ``True``.

    Returns
    -------
    DocResult
        Structured result with one :class:`PageResult` per page.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file is password-protected.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    use_cuda = detect_device(force=force_device)
    ocr_engine = get_ocr_engine(use_cuda=use_cuda)
    device_label = "CUDA" if use_cuda else "CPU"

    res = DocResult(source=path.name, device=device_label)

    for page_no, pdf_page, img in iter_pages(path):
        t0 = time.perf_counter()

        if pdf_page is not None:
            # ── digital PDF page ──────────────────────────────────────────
            use_text, reason = triage_page(pdf_page)
            if use_text:
                text, _ = text_layer_extract(pdf_page)
                pr = PageResult(
                    page=page_no,
                    method="text_layer",
                    reason=reason,
                    text=text,
                    n_chars=len(text),
                    confidence=None,
                    seconds=time.perf_counter() - t0,
                )
                res.pages.append(pr)
                if verbose:
                    print(f"page {page_no:>3}: text_layer  {pr.seconds * 1000:7.1f} ms  ({reason})")
                continue
            # Fall through: render and OCR
            img = render_page(pdf_page)
        else:
            # ── standalone image input ────────────────────────────────────
            reason = "image file"

        if is_blank_image(img):
            pr = PageResult(
                page=page_no,
                method="blank",
                reason=reason + ", blank page",
                text="",
                n_chars=0,
                confidence=None,
                seconds=time.perf_counter() - t0,
            )
        else:
            text, _elements, conf = ocr_extract(img, ocr_engine)
            pr = PageResult(
                page=page_no,
                method="ocr",
                reason=reason,
                text=text,
                n_chars=len(text),
                confidence=conf,
                seconds=time.perf_counter() - t0,
            )

        res.pages.append(pr)
        if verbose:
            conf_str = f"conf {pr.confidence:.2f}" if pr.confidence is not None else ""
            print(
                f"page {page_no:>3}: {pr.method:<11} {pr.seconds * 1000:7.1f} ms"
                f"  ({reason}) {conf_str}"
            )

    return res


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def save_result(res: DocResult, out_dir: str = "outputs") -> tuple[Path, Path]:
    """Write JSON and plain-text files for *res* to *out_dir*.

    Parameters
    ----------
    res:
        A :class:`DocResult` returned by :func:`extract_document`.
    out_dir:
        Directory path (created automatically if it does not exist).

    Returns
    -------
    (json_path, txt_path)
        Paths to the saved files.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(res.source).stem
    json_path = out / f"{stem}.json"
    txt_path = out / f"{stem}.txt"
    json_path.write_text(json.dumps(res.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text(res.full_text(), encoding="utf-8")
    return json_path, txt_path
