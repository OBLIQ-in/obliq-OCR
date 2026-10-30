"""
conftest.py – pytest fixtures shared across all tests.

PDF fixtures are expected in tests/fixtures/.  They are NOT committed to Git
(see .gitignore); you must add real or synthetic PDF files before running the
full test suite.  The ``conftest.py`` provides helpers to create minimal
synthetic PDFs on-the-fly for CI/smoke tests.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Minimal synthetic PDF builders (no external files required for smoke tests)
# ---------------------------------------------------------------------------


def _make_digital_pdf(text: str = "Hello obliq-OCR. This is a digital text-layer page for testing purposes.") -> bytes:
    """Return bytes of a minimal single-page digital PDF with embedded text."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), text, fontsize=14)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_blank_pdf() -> bytes:
    """Return bytes of a single-page PDF with no content."""
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_rotated_pdf(text: str = "Rotated page text for testing.") -> bytes:
    """Return bytes of a PDF whose single page is rotated 90 degrees."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.set_rotation(90)
    page.insert_text((72, 100), text, fontsize=14)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def digital_pdf(tmp_path) -> Path:
    """A temporary single-page digital PDF with readable text layer."""
    p = tmp_path / "digital.pdf"
    p.write_bytes(_make_digital_pdf())
    return p


@pytest.fixture()
def blank_pdf(tmp_path) -> Path:
    """A temporary single-page blank PDF (no text, no images)."""
    p = tmp_path / "blank.pdf"
    p.write_bytes(_make_blank_pdf())
    return p


@pytest.fixture()
def rotated_pdf(tmp_path) -> Path:
    """A temporary single-page PDF with a 90-degree page rotation."""
    p = tmp_path / "rotated.pdf"
    p.write_bytes(_make_rotated_pdf())
    return p


@pytest.fixture()
def fixture_digital_pdf() -> Path:
    """Path to the user-supplied digital.pdf fixture (skips if missing)."""
    p = FIXTURES_DIR / "digital.pdf"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}. Add a digital PDF to tests/fixtures/.")
    return p


@pytest.fixture()
def fixture_scanned_pdf() -> Path:
    """Path to the user-supplied scanned.pdf fixture (skips if missing)."""
    p = FIXTURES_DIR / "scanned.pdf"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}. Add a scanned PDF to tests/fixtures/.")
    return p


@pytest.fixture()
def fixture_mixed_pdf() -> Path:
    """Path to the user-supplied mixed.pdf fixture (skips if missing)."""
    p = FIXTURES_DIR / "mixed.pdf"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}. Add a mixed PDF to tests/fixtures/.")
    return p


@pytest.fixture()
def fixture_rotated_pdf() -> Path:
    """Path to the user-supplied rotated.pdf fixture (skips if missing)."""
    p = FIXTURES_DIR / "rotated.pdf"
    if not p.exists():
        pytest.skip(f"Fixture not found: {p}. Add a rotated PDF to tests/fixtures/.")
    return p
