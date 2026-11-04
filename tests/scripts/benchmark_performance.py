"""
Performance benchmark and speed regression detector for obliq-OCR.
Measures parsing throughput (pages/second) across document types and asserts
that execution time remains within accepted performance baselines.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from obliq_ocr import parse_document  # noqa: E402
from tests.scripts.generate_fixtures import FIXTURES_DIR  # noqa: E402

# Baseline expectations (minimum pages/second or max seconds per document)
# Note: CI runners can be constrained; baseline values account for standard runner load.
PERFORMANCE_BASELINES = {
    "digital.pdf": {"max_seconds": 1.5, "min_pages_per_sec": 0.5},
    "scanned.pdf": {"max_seconds": 3.5, "min_pages_per_sec": 0.25},
    "mixed.pdf": {"max_seconds": 3.0, "min_pages_per_sec": 0.33},
}

WARN_REGRESSION_THRESHOLD = 1.25  # Warn if execution is 25% slower than max_seconds


def run_performance_benchmarks() -> None:
    """Run performance benchmarks on fixture PDFs and detect speed regressions."""
    print("=== Running obliq-OCR Performance Benchmark Suite ===")

    warnings = 0
    failures = 0
    total_benchmarked = 0

    for filename, baseline in PERFORMANCE_BASELINES.items():
        file_path = FIXTURES_DIR / filename
        if not file_path.exists():
            print(f"[SKIP] Fixture for benchmark missing: {file_path}")
            continue

        total_benchmarked += 1

        # Warm-up run to exclude cold-start engine initialization overhead
        _ = parse_document(file_path, verbose=False)

        # Benchmark execution run
        start_time = time.perf_counter()
        result = parse_document(file_path, verbose=False)
        elapsed_seconds = time.perf_counter() - start_time

        page_count = len(result.pages)
        pages_per_sec = page_count / elapsed_seconds if elapsed_seconds > 0 else 0

        max_allowed_time = baseline["max_seconds"]
        warn_time = max_allowed_time * WARN_REGRESSION_THRESHOLD

        print(f"\nBenchmark Target: {filename}")
        print(f"  - Pages Processed : {page_count}")
        print(f"  - Execution Time  : {elapsed_seconds:.4f} seconds")
        print(f"  - Throughput      : {pages_per_sec:.2f} pages/sec")
        print(f"  - Baseline Max    : {max_allowed_time:.2f} seconds")

        if elapsed_seconds > warn_time:
            print(f"[FAIL] Hard performance regression! Exceeded limit of {warn_time:.2f}s.")
            failures += 1
        elif elapsed_seconds > max_allowed_time:
            print(
                "[WARN] Performance warning: Processed slower than "
                f"ideal baseline ({max_allowed_time:.2f}s)."
            )
            warnings += 1
        else:
            print(f"[PASS] {filename} benchmark passed within baseline bounds.")

    print("\n=== Benchmark Summary ===")
    print(f"Total Evaluated : {total_benchmarked}")
    print(f"Warnings        : {warnings}")
    print(f"Failures        : {failures}")

    if failures > 0:
        print("\n[ERROR] Performance benchmark check FAILED due to critical speed regression.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Performance benchmark completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    run_performance_benchmarks()
