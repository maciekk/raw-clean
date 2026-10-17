"""Command-line interface for raw-clean."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from raw_clean import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="raw-clean",
        description="Preserve selected RAW photographs and quarantine the rest safely.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="preview retention and quarantine decisions without changing files",
    )
    scan_parser.add_argument("shoot_dir", type=Path, metavar="SHOOT_DIR")

    quarantine_parser = subparsers.add_parser(
        "quarantine",
        help="promote keepers and move other RAWs into quarantine",
    )
    quarantine_parser.add_argument("shoot_dir", type=Path, metavar="SHOOT_DIR")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the raw-clean command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    parser.error(f"the {args.command!r} command is not implemented yet")
