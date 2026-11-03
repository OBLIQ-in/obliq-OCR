# Generate synthetic PDF test fixtures for the obliq-OCR test suite.

from pathlib import Path

import pymupdf

# Resolve tests/fixtures path dynamically relative to this script's directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def create_image_pixmap(text: str):
    """Render text into a standalone raster image pixmap with no underlying PDF text layer."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=150)
    page.insert_text((30, 75), text, fontsize=24)
    pix = page.get_pixmap(dpi=150)
    doc.close()
    return pix


def generate_all_fixtures():
    """Build all 4 required synthetic test PDF files."""
    # 1. Create digital.pdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        (
            "Hello obliq-OCR digital test page.\n"
            "This is a native text layer document.\n"
            "It contains multiple lines of standard searchable text."
        ),
        fontsize=14,
    )
    doc.save(FIXTURES_DIR / "digital.pdf")
    doc.close()

    # 3. Create mixed.pdf
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 50),
        (
            "Mixed document digital page.\n"
            "This page contains native text layer elements.\n"
            "It should be extracted via text layer."
        ),
        fontsize=14,
    )
    p2 = doc.new_page(width=400, height=150)
    p2.insert_image(
        p2.rect,
        pixmap=create_image_pixmap("Mixed document scanned page."),
    )
    doc.save(FIXTURES_DIR / "mixed.pdf")
    doc.close()

    # 2. Create scanned.pdf
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=150)
    page.insert_image(page.rect, pixmap=create_image_pixmap("Scanned OCR text content"))
    doc.save(FIXTURES_DIR / "scanned.pdf")
    doc.close()

    # 3. Create mixed.pdf (Page 1 = rich digital text, Page 2 = pure image)
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 50),
        (
            "Mixed document digital page.\n"
            "This page contains native text layer elements.\n"
            "It should be extracted via text layer."
        ),
        fontsize=14,
    )

    p2 = doc.new_page(width=400, height=150)
    p2.insert_image(
        p2.rect, pixmap=create_image_pixmap("Mixed document scanned page.")
    )  # Fixed: p2.rect instead of page.rect
    doc.save(FIXTURES_DIR / "mixed.pdf")
    doc.close()

    # 4. Create rotated.pdf
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=150)
    page.insert_image(page.rect, pixmap=create_image_pixmap("Rotated text content"))
    doc[0].set_rotation(90)
    doc.save(FIXTURES_DIR / "rotated.pdf")
    doc.close()

    print(f"Successfully generated all 4 PDF fixtures in: {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
