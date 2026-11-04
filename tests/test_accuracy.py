"""Pytest wrapper for model-accuracy regression gate."""

from __future__ import annotations

import pytest
from jiwer import cer, wer

from obliq_ocr import parse_document
from tests.scripts.generate_fixtures import FIXTURES_DIR

GOLDEN_EXPECTATIONS = {
    "digital.pdf": (
        "Hello obliq-OCR digital test page.\n"
        "This is a native text layer document.\n"
        "It contains multiple lines of standard searchable text."
    ),
    "scanned.pdf": "Scanned OCR text content",
}

MAX_CER = 0.05
MAX_WER = 0.10


@pytest.mark.parametrize("filename,expected", GOLDEN_EXPECTATIONS.items())
def test_golden_file_accuracy(filename: str, expected: str):
    file_path = FIXTURES_DIR / filename
    if not file_path.exists():
        pytest.skip(f"Golden fixture {filename} missing.")

    result = parse_document(file_path, verbose=False)
    # Extract actual page text without header banners
    extracted = "\n".join(p.text.strip() for p in result.pages).strip()

    computed_cer = cer(expected, extracted)
    computed_wer = wer(expected, extracted)

    assert computed_cer <= MAX_CER, (
        f"CER {computed_cer:.4f} exceeded threshold {MAX_CER} for {filename}"
    )
    assert computed_wer <= MAX_WER, (
        f"WER {computed_wer:.4f} exceeded threshold {MAX_WER} for {filename}"
    )
