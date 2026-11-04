"""Pytest suite for performance benchmark regression tracking."""

from __future__ import annotations

import time

import pytest

from obliq_ocr import parse_document
from tests.scripts.generate_fixtures import FIXTURES_DIR


@pytest.mark.parametrize(
    "filename,max_allowed_seconds",
    [
        ("digital.pdf", 2.0),
        ("scanned.pdf", 5.0),
        ("mixed.pdf", 4.0),
    ],
)
def test_parsing_performance_baseline(filename: str, max_allowed_seconds: float):
    """Assert document parsing completes within baseline execution windows."""
    file_path = FIXTURES_DIR / filename
    if not file_path.exists():
        pytest.skip(f"Benchmark fixture {filename} missing.")

    # Warm-up run
    _ = parse_document(file_path, verbose=False)

    # Timed run
    start = time.perf_counter()
    result = parse_document(file_path, verbose=False)
    duration = time.perf_counter() - start

    assert duration <= max_allowed_seconds, (
        f"Performance regression on {filename}: took {duration:.2f}s "
        f"(max threshold: {max_allowed_seconds:.2f}s)"
    )
    assert len(result.pages) >= 1
