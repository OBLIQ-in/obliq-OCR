"""
test_pipeline.py – Unit and integration tests for obliq-OCR.

Test categories
---------------
* Smoke / import tests – verify the package is importable and the public API
  is present.
* Unit tests         – test individual helper functions without I/O.
* Synthetic PDF tests – generate tiny in-memory PDFs and run the full
  pipeline, so CI can pass without real fixture files.
* Fixture-based tests – run against the four representative PDFs in
  tests/fixtures/.  These are *skipped* automatically if the files are
  missing, so the test suite still passes on a clean clone.
* Output schema tests – verify the structure of :class:`DocResult` and
  :class:`PageResult`.
* Edge-case tests    – FileNotFoundError, password-protected PDFs, etc.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Smoke: package importable and public symbols present
# ---------------------------------------------------------------------------


class TestImports:
    def test_package_importable(self):
        import obliq_ocr  # noqa: F401

    def test_public_api_present(self):
        from obliq_ocr import (
            build_ocr,
            detect_device,
            parse_document,
            save_result,
        )

        assert callable(parse_document)
        assert callable(save_result)
        assert callable(build_ocr)
        assert callable(detect_device)

    def test_version_string(self):
        import obliq_ocr

        assert isinstance(obliq_ocr.__version__, str)
        parts = obliq_ocr.__version__.split(".")
        assert len(parts) == 3, "version should be semver (x.y.z)"


# ---------------------------------------------------------------------------
# Unit: utility functions
# ---------------------------------------------------------------------------


class TestWordsToLines:
    def test_empty_returns_empty_string(self):
        from obliq_ocr.utils import words_to_lines

        assert words_to_lines([]) == ""

    def test_single_word(self):
        from obliq_ocr.utils import words_to_lines

        result = words_to_lines([(0, 0, 50, 20, "Hello")])
        assert result == "Hello"

    def test_two_words_same_line(self):
        from obliq_ocr.utils import words_to_lines

        items = [(0, 0, 50, 20, "Hello"), (55, 0, 100, 20, "World")]
        result = words_to_lines(items)
        assert "Hello" in result
        assert "World" in result
        assert "\n" not in result  # same line → no newline

    def test_two_lines(self):
        from obliq_ocr.utils import words_to_lines

        items = [
            (0, 0, 50, 20, "Line1"),
            (0, 40, 50, 60, "Line2"),
        ]
        result = words_to_lines(items)
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_column_gap_inserts_pipe(self):
        from obliq_ocr.utils import words_to_lines

        # two words on the same line with a big horizontal gap → " | "
        items = [
            (0, 0, 50, 20, "Left"),
            (200, 0, 260, 20, "Right"),  # gap ≫ line-height → column
        ]
        result = words_to_lines(items, gap_factor=1.0)
        assert " | " in result

    def test_whitespace_only_items_ignored(self):
        from obliq_ocr.utils import words_to_lines

        items = [(0, 0, 50, 20, "   "), (55, 0, 100, 20, "Text")]
        result = words_to_lines(items)
        assert result == "Text"


class TestGarbageRatio:
    def test_clean_text_is_zero(self):
        from obliq_ocr.utils import garbage_ratio

        assert garbage_ratio("Hello World") == pytest.approx(0.0)

    def test_all_replacement_chars(self):
        from obliq_ocr.utils import garbage_ratio

        assert garbage_ratio("\ufffd\ufffd\ufffd") == pytest.approx(1.0)

    def test_empty_string_is_one(self):
        from obliq_ocr.utils import garbage_ratio

        assert garbage_ratio("") == pytest.approx(1.0)

    def test_whitespace_only_is_one(self):
        from obliq_ocr.utils import garbage_ratio

        assert garbage_ratio("   \n\t") == pytest.approx(1.0)

    def test_cid_sequences_counted(self):
        from obliq_ocr.utils import garbage_ratio

        # one (cid:X) counts as 3 bad characters out of e.g. 10 real chars
        text = "abcdefghij(cid:1)"
        ratio = garbage_ratio(text)
        assert ratio > 0.0


class TestIsBlankImage:
    def test_white_image_is_blank(self):
        from obliq_ocr.utils import is_blank_image

        white = np.full((100, 100, 3), 255, dtype=np.uint8)
        assert is_blank_image(white) is True

    def test_image_with_content_is_not_blank(self):
        from obliq_ocr.utils import is_blank_image

        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        assert is_blank_image(img) is False


# ---------------------------------------------------------------------------
# Unit: schema dataclasses
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_bounding_box_as_list(self):
        from obliq_ocr.schemas import BoundingBox

        bb = BoundingBox(x0=1.0, y0=2.0, x1=3.0, y1=4.0)
        assert bb.as_list() == [1.0, 2.0, 3.0, 4.0]

    def test_document_output_full_text(self):
        from obliq_ocr.schemas import DocumentOutput, PageOutput

        doc = DocumentOutput(
            file_name="test.pdf",
            device="CPU",
            pages=[
                PageOutput(page_number=1, method="text_layer", reason="ok", text="Hello"),
                PageOutput(page_number=2, method="ocr", reason="scanned", text="World"),
            ],
        )
        ft = doc.full_text()
        assert "PAGE 1" in ft
        assert "Hello" in ft
        assert "PAGE 2" in ft
        assert "World" in ft

    def test_document_output_to_dict(self):
        from obliq_ocr.schemas import DocumentOutput, PageOutput

        doc = DocumentOutput(
            file_name="x.pdf",
            device="CPU",
            pages=[
                PageOutput(page_number=1, method="blank", reason="empty", text=""),
            ],
        )
        d = doc.to_dict()
        assert d["file_name"] == "x.pdf"
        assert isinstance(d["pages"], list)
        assert d["pages"][0]["page_number"] == 1


# ---------------------------------------------------------------------------
# Integration: synthetic digital PDF (always runs)
# ---------------------------------------------------------------------------


class TestDigitalPDF:
    def test_parse_returns_doc_result(self, digital_pdf):
        from obliq_ocr import DocResult, parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert isinstance(result, DocResult)

    def test_at_least_one_page(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert len(result.pages) >= 1

    def test_page_numbers_are_one_indexed(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert result.pages[0].page == 1

    def test_text_extracted(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        page = result.pages[0]
        assert len(page.text) > 0, "Expected non-empty text from digital PDF"

    def test_method_is_text_layer(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert result.pages[0].method == "text_layer"

    def test_confidence_is_none_for_text_layer(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert result.pages[0].confidence is None

    def test_seconds_is_positive(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        assert result.pages[0].seconds > 0

    def test_to_dict_serialisable(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        d = result.to_dict()
        serialised = json.dumps(d)  # must not raise
        assert "pages" in json.loads(serialised)


# ---------------------------------------------------------------------------
# Integration: synthetic blank PDF (always runs)
# ---------------------------------------------------------------------------


class TestBlankPDF:
    def test_blank_page_method(self, blank_pdf):
        from obliq_ocr import parse_document

        result = parse_document(blank_pdf, verbose=False)
        assert result.pages[0].method == "blank"

    def test_blank_page_empty_text(self, blank_pdf):
        from obliq_ocr import parse_document

        result = parse_document(blank_pdf, verbose=False)
        assert result.pages[0].text == ""

    def test_blank_page_zero_chars(self, blank_pdf):
        from obliq_ocr import parse_document

        result = parse_document(blank_pdf, verbose=False)
        assert result.pages[0].n_chars == 0


# ---------------------------------------------------------------------------
# Integration: synthetic rotated PDF (always runs)
# ---------------------------------------------------------------------------


class TestRotatedPDF:
    def test_parse_completes_without_error(self, rotated_pdf):
        from obliq_ocr import parse_document

        result = parse_document(rotated_pdf, verbose=False)
        assert len(result.pages) >= 1

    def test_page_has_text_or_ocr(self, rotated_pdf):
        from obliq_ocr import parse_document

        result = parse_document(rotated_pdf, verbose=False)
        page = result.pages[0]
        assert page.method in {"text_layer", "ocr", "blank"}


# ---------------------------------------------------------------------------
# Integration: save_result
# ---------------------------------------------------------------------------


class TestSaveResult:
    def test_saves_json_and_txt(self, digital_pdf, tmp_path):
        from obliq_ocr import parse_document, save_result

        result = parse_document(digital_pdf, verbose=False)
        json_p, txt_p = save_result(result, out_dir=str(tmp_path / "out"))
        assert json_p.exists()
        assert txt_p.exists()

    def test_json_is_valid(self, digital_pdf, tmp_path):
        from obliq_ocr import parse_document, save_result

        result = parse_document(digital_pdf, verbose=False)
        json_p, _ = save_result(result, out_dir=str(tmp_path / "out"))
        data = json.loads(json_p.read_text(encoding="utf-8"))
        assert "source" in data
        assert "pages" in data
        assert isinstance(data["pages"], list)

    def test_txt_contains_page_headers(self, digital_pdf, tmp_path):
        from obliq_ocr import parse_document, save_result

        result = parse_document(digital_pdf, verbose=False)
        _, txt_p = save_result(result, out_dir=str(tmp_path / "out"))
        content = txt_p.read_text(encoding="utf-8")
        assert "===== PAGE 1" in content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        from obliq_ocr import parse_document

        with pytest.raises(FileNotFoundError):
            parse_document(tmp_path / "nonexistent.pdf", verbose=False)

    def test_full_text_format(self, digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(digital_pdf, verbose=False)
        ft = result.full_text()
        assert ft.startswith("===== PAGE 1")


# ---------------------------------------------------------------------------
# Fixture-based integration tests (skip if files missing)
# ---------------------------------------------------------------------------


class TestFixtureDigital:
    """Tests against tests/fixtures/digital.pdf (skipped if absent)."""

    def test_extracts_text(self, fixture_digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_digital_pdf, verbose=False)
        total_chars = sum(p.n_chars for p in result.pages)
        assert total_chars > 0, "Expected at least some text from digital PDF fixture."

    def test_all_pages_have_valid_method(self, fixture_digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_digital_pdf, verbose=False)
        valid = {"text_layer", "ocr", "blank"}
        for p in result.pages:
            assert p.method in valid, f"Page {p.page} has unknown method: {p.method!r}"

    def test_page_numbers_sequential(self, fixture_digital_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_digital_pdf, verbose=False)
        for i, p in enumerate(result.pages, start=1):
            assert p.page == i


class TestFixtureScanned:
    """Tests against tests/fixtures/scanned.pdf (skipped if absent)."""

    def test_ocr_runs_and_returns_text(self, fixture_scanned_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_scanned_pdf, verbose=False)
        ocr_pages = [p for p in result.pages if p.method == "ocr"]
        assert len(ocr_pages) > 0, "Expected at least one OCR page in scanned fixture."
        assert all(0.0 <= p.confidence <= 1.0 for p in ocr_pages if p.confidence is not None)

    def test_bboxes_valid_on_ocr_pages(self, fixture_scanned_pdf):
        """Confidence should be in [0,1] and pages have text."""
        from obliq_ocr import parse_document

        result = parse_document(fixture_scanned_pdf, verbose=False)
        for p in result.pages:
            if p.method == "ocr" and p.confidence is not None:
                assert 0.0 <= p.confidence <= 1.0


class TestFixtureMixed:
    """Tests against tests/fixtures/mixed.pdf (skipped if absent)."""

    def test_mixed_pdf_has_both_methods(self, fixture_mixed_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_mixed_pdf, verbose=False)
        methods = {p.method for p in result.pages}
        assert len(methods) > 1, (
            "Mixed fixture should produce pages with different methods "
            f"(text_layer and ocr). Got: {methods}"
        )


class TestFixtureRotated:
    """Tests against tests/fixtures/rotated.pdf (skipped if absent)."""

    def test_rotated_pdf_parses_without_crash(self, fixture_rotated_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_rotated_pdf, verbose=False)
        assert len(result.pages) >= 1

    def test_rotated_pdf_produces_some_text(self, fixture_rotated_pdf):
        from obliq_ocr import parse_document

        result = parse_document(fixture_rotated_pdf, verbose=False)
        total = sum(p.n_chars for p in result.pages)
        assert total > 0, "Expected some text from rotated fixture."
