"""
engine.py – OCR engine initialisation and device detection.

Loads RapidOCR once and exposes a singleton-style accessor so that
the expensive model-loading step is only performed on first use.

ONNX Runtime execution provider selection
------------------------------------------
* If ``onnxruntime-gpu`` is installed **and** ``CUDAExecutionProvider``
  is present, CUDA is used automatically.
* Set the ``OBLIQ_OCR_DEVICE`` environment variable to ``"cpu"`` or
  ``"cuda"`` to override auto-detection.
* ``FORCE_DEVICE`` parameter in :func:`build_ocr` accepts the same values.
"""

from __future__ import annotations

import os
from typing import Optional

import onnxruntime as ort

# ── configuration knobs (can be overridden before the first import) ──────────
OCR_MIN_SCORE: float = 0.5  # drop OCR boxes below this confidence
# ────────────────────────────────────────────────────────────────────────────


def detect_device(force: Optional[str] = None) -> bool:
    """Return ``True`` if CUDA should be used for OCR inference.

    Parameters
    ----------
    force:
        ``"cpu"`` to always use CPU, ``"cuda"`` to require GPU, or
        ``None`` (default) for automatic detection.

    Raises
    ------
    RuntimeError
        If ``force="cuda"`` is requested but CUDA is unavailable.
    """
    env_override = os.environ.get("OBLIQ_OCR_DEVICE", "").strip().lower()
    effective = (force or env_override or "auto").lower()

    providers = ort.get_available_providers()
    cuda_available = "CUDAExecutionProvider" in providers

    if effective == "cuda":
        if not cuda_available:
            raise RuntimeError(
                "CUDA requested (OBLIQ_OCR_DEVICE=cuda / force='cuda') "
                "but CUDAExecutionProvider is not available. "
                "Install onnxruntime-gpu and ensure CUDA drivers are present."
            )
        return True
    if effective == "cpu":
        return False
    # auto
    return cuda_available


def build_ocr(use_cuda: bool = False):
    """Instantiate and return a :class:`rapidocr_onnxruntime.RapidOCR` engine.

    Falls back silently to CPU if GPU initialisation fails.

    Parameters
    ----------
    use_cuda:
        Whether to request CUDA execution providers for all three sub-models
        (detection, classification, recognition).

    Returns
    -------
    rapidocr_onnxruntime.RapidOCR
        A configured OCR engine ready for inference.
    """
    from rapidocr_onnxruntime import (
        RapidOCR,  # imported here to keep the module importable without rapidocr installed
    )

    kw = dict(
        det_use_cuda=use_cuda,
        cls_use_cuda=use_cuda,
        rec_use_cuda=use_cuda,
        det_limit_side_len=1280,
        det_limit_type="max",
        # Passing None tells RapidOCR to use its own bundled model paths.
        det_model_path=None,
        cls_model_path=None,
        rec_model_path=None,
        text_score=OCR_MIN_SCORE,
    )
    try:
        return RapidOCR(**kw)
    except Exception as exc:  # any GPU-init problem → safe CPU fallback
        print(f"[obliq_ocr] OCR GPU init failed ({exc!r:.120}); falling back to CPU.")
        kw.update(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False)
        return RapidOCR(**kw)


# ---------------------------------------------------------------------------
# Module-level lazy singleton – avoids re-loading models on every call.
# ---------------------------------------------------------------------------
_ocr_engine = None
_ocr_engine_cuda: Optional[bool] = None


def get_ocr_engine(use_cuda: bool = False):
    """Return the module-level OCR engine, initialising it on first call.

    Parameters
    ----------
    use_cuda:
        Passed to :func:`build_ocr` on first initialisation.  Ignored on
        subsequent calls (the engine is reused as-is).
    """
    global _ocr_engine, _ocr_engine_cuda
    if _ocr_engine is None or _ocr_engine_cuda != use_cuda:
        _ocr_engine = build_ocr(use_cuda)
        _ocr_engine_cuda = use_cuda
    return _ocr_engine
