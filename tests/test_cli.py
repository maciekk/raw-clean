"""Tests for the command-line skeleton."""

from pathlib import Path

from raw_clean.cli import build_parser, main


def test_scan_accepts_shoot_directory() -> None:
    args = build_parser().parse_args(["scan", "/tmp/example shoot"])

    assert args.command == "scan"
    assert args.shoot_dir == Path("/tmp/example shoot")


def test_quarantine_accepts_shoot_directory() -> None:
    args = build_parser().parse_args(["quarantine", "/tmp/example shoot"])

    assert args.command == "quarantine"
    assert args.shoot_dir == Path("/tmp/example shoot")


def test_scan_reports_plan_without_changing_files(tmp_path: Path, capsys) -> None:
    jpeg = tmp_path / "holiday photo.JPG"
    raw = tmp_path / "holiday photo.RAF"
    jpeg.write_bytes(b"jpeg")
    raw.write_bytes(b"raw")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    exit_code = main(["scan", str(tmp_path)])

    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    output = capsys.readouterr().out
    assert exit_code == 0
    assert before == after
    assert "RAW files found: 1" in output
    assert "TOTAL RAWs TO QUARANTINE:          1" in output
    assert "No files changed." in output
    assert "\033[" not in output


def test_scan_returns_attention_exit_for_blocked_raw(tmp_path: Path, capsys) -> None:
    (tmp_path / "photo.JPG").write_bytes(b"jpeg")
    (tmp_path / "PHOTO.jpeg").write_bytes(b"jpeg")
    (tmp_path / "photo.RAF").write_bytes(b"raw")

    exit_code = main(["scan", str(tmp_path)])

    assert exit_code == 1
    assert "multiple JPEGs share this stem" in capsys.readouterr().out
