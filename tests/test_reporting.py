"""Tests for plain and terminal-styled scan reports."""

from pathlib import Path

from raw_clean.planning import build_plan
from raw_clean.reporting import render_plan


def test_plain_report_has_no_terminal_escapes(tmp_path: Path) -> None:
    (tmp_path / "photo.JPG").write_bytes(b"jpeg")
    (tmp_path / "photo.RAF").write_bytes(b"raw")

    report = render_plan(build_plan(tmp_path), color=False)

    assert "\033[" not in report
    assert "TOTAL RAWs TO PRESERVE" in report


def test_colored_report_uses_terminal_emphasis(tmp_path: Path) -> None:
    report = render_plan(build_plan(tmp_path), color=True)

    assert "\033[1m" in report
    assert "\033[35m" in report
