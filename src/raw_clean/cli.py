"""Command-line interface for raw-clean."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from raw_clean import __version__
from raw_clean.discovery import DiscoveryError
from raw_clean.planning import PlanningError, build_plan
from raw_clean.reporting import render_plan

EXIT_OK = 0
EXIT_ATTENTION = 1


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


def _scan(shoot_dir: Path) -> int:
    try:
        plan = build_plan(shoot_dir)
    except (DiscoveryError, PlanningError) as error:
        print(f"raw-clean: error: {error}", file=sys.stderr)
        return EXIT_ATTENTION

    use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    print(render_plan(plan, color=use_color), end="")
    return EXIT_ATTENTION if plan.blocked else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the raw-clean command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return _scan(args.shoot_dir)

    parser.error("the 'quarantine' command is not implemented yet")
