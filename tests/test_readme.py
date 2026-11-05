"""Runs the README quickstart exactly as written, so it can't go stale (#47)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from tests.scripts.generate_fixtures import FIXTURES_DIR

README = Path(__file__).resolve().parents[1] / "README.md"


def quickstart_code() -> str:
    text = README.read_text(encoding="utf-8")
    match = re.search(r"<!-- quickstart:.*?-->\s*```python\n(.*?)```", text, re.S)
    assert match, "README quickstart block not found"
    return match.group(1)


def test_quickstart_is_at_most_ten_lines():
    assert len(quickstart_code().strip().splitlines()) <= 10


def test_quickstart_runs_verbatim(tmp_path, monkeypatch):
    fixture = FIXTURES_DIR / "mixed.pdf"
    if not fixture.exists():
        pytest.skip("mixed.pdf fixture missing; run tests/scripts/generate_fixtures.py")

    # The quickstart reads invoice.pdf from the current folder.
    shutil.copy(fixture, tmp_path / "invoice.pdf")
    monkeypatch.chdir(tmp_path)
    exec(compile(quickstart_code(), "README.md quickstart", "exec"), {})

    assert (tmp_path / "outputs" / "invoice.json").is_file()
    assert (tmp_path / "outputs" / "invoice.txt").is_file()
