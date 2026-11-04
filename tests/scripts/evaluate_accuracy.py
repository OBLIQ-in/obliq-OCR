"""
Model-accuracy regression test for obliq-OCR.
Runs the OCR/parsing engine on golden fixture files and asserts that
Character Error Rate (CER) and Word Error Rate (WER) remain below threshold.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jiwer import cer, wer  # noqa: E402

from obliq_ocr import parse_document  # noqa: E402
from tests.scripts.generate_fixtures import FIXTURES_DIR  # noqa: E402

GOLDEN_EXPECTATIONS = {
    "digital.pdf": (
        "Hello obliq-OCR digital test page.\n"
        "This is a native text layer document.\n"
        "It contains multiple lines of standard searchable text."
    ),
    "scanned.pdf": "Scanned OCR text content",
}

MAX_CER_THRESHOLD = 0.05
MAX_WER_THRESHOLD = 0.10


def run_accuracy_evaluation() -> None:
    """Evaluate extracted text against golden references and enforce thresholds."""
    print("=== Running Model-Accuracy Regression Gate ===")

    failures = 0
    total_evaluated = 0

    for filename, expected_text in GOLDEN_EXPECTATIONS.items():
        file_path = FIXTURES_DIR / filename
        if not file_path.exists():
            print(f"[SKIP] Golden fixture not found: {file_path}")
            continue

        total_evaluated += 1

        result = parse_document(file_path, verbose=False)
        extracted_text = "\n".join(p.text.strip() for p in result.pages).strip()

        computed_cer = cer(expected_text, extracted_text)
        computed_wer = wer(expected_text, extracted_text)

        print(f"\nTarget: {filename}")
        print(f"  - Expected : {expected_text!r}")
        print(f"  - Extracted: {extracted_text!r}")
        print(f"  - CER      : {computed_cer:.4f} (Threshold: <= {MAX_CER_THRESHOLD})")
        print(f"  - WER      : {computed_wer:.4f} (Threshold: <= {MAX_WER_THRESHOLD})")

        if computed_cer > MAX_CER_THRESHOLD or computed_wer > MAX_WER_THRESHOLD:
            print(f"[FAIL] Accuracy regression detected for {filename}!")
            failures += 1
        else:
            print(f"[PASS] {filename} met accuracy thresholds.")

    if total_evaluated == 0:
        print("[WARN] No golden fixtures found to evaluate.")
        sys.exit(0)

    if failures > 0:
        print(
            f"\n[ERROR] Model-Accuracy Regression Gate FAILED "
            f"({failures}/{total_evaluated} files failed thresholds)."
        )
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All {total_evaluated} golden fixtures passed accuracy checks!")
        sys.exit(0)


if __name__ == "__main__":
    run_accuracy_evaluation()
