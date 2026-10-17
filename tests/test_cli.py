"""Tests for the command-line skeleton."""

from pathlib import Path

from raw_clean.cli import build_parser


def test_scan_accepts_shoot_directory() -> None:
    args = build_parser().parse_args(["scan", "/tmp/example shoot"])

    assert args.command == "scan"
    assert args.shoot_dir == Path("/tmp/example shoot")


def test_quarantine_accepts_shoot_directory() -> None:
    args = build_parser().parse_args(["quarantine", "/tmp/example shoot"])

    assert args.command == "quarantine"
    assert args.shoot_dir == Path("/tmp/example shoot")
