"""Human-readable rendering of raw-clean plans and results."""

from __future__ import annotations

from raw_clean.models import Plan

_BOLD = "\033[1m"
_PURPLE = "\033[35m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


def format_bytes(size: int) -> str:
    """Format a byte count using compact binary units."""
    value = float(size)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def render_plan(plan: Plan, *, color: bool = False) -> str:
    """Render a complete scan report without changing the plan or filesystem."""
    def styled(text: str, *codes: str) -> str:
        if not color:
            return text
        return f"{''.join(codes)}{text}{_RESET}"

    ordinary = plan.ordinary_quarantine
    orphans = plan.orphan_quarantine
    blocked = plan.blocked

    lines = [
        styled("RAW CLEAN — DRY RUN", _BOLD),
        "=" * 44,
        f"Shoot directory: {plan.root}",
        f"RAW files found: {plan.total_raws}",
        "",
        styled("KEEP", _BOLD),
        f"  Already .KEEP:                     {len(plan.existing_keepers)}",
        f"  Purple labels detected (new KEEP): {len(plan.promotions)}",
        styled(
            f"  TOTAL RAWs TO PRESERVE:             {plan.protected_count}",
            _BOLD,
            _PURPLE,
        ),
    ]

    if plan.promotions:
        lines.extend(["", styled("  Newly detected purple keepers:", _BOLD)])
        for item in plan.promotions:
            assert item.destination is not None
            destination = item.destination.relative_to(plan.root)
            lines.append(f"    {item.relative_path} -> {destination}")

    lines.extend(
        [
            "",
            styled("QUARANTINE", _BOLD),
            f"  With matching JPEG:                {len(ordinary)}",
            styled(
                f"  Without matching JPEG:             {len(orphans)}"
                + ("  WARNING: possible RAW-only" if orphans else ""),
                _YELLOW,
            ),
            f"  TOTAL RAWs TO QUARANTINE:          {len(ordinary) + len(orphans)}",
            f"  Approx. RAW space moved:           {format_bytes(plan.quarantine_size)}",
            f"  Planned quarantine directory:      {plan.quarantine_root}",
        ]
    )

    if orphans:
        lines.extend(["", styled("  RAWs without matching JPEGs:", _BOLD, _YELLOW)])
        lines.extend(f"    {item.relative_path}" for item in orphans)

    lines.extend(
        [
            "",
            styled("BLOCKED", _BOLD),
            f"  RAWs requiring attention:          {len(blocked)}",
        ]
    )
    for item in blocked:
        lines.append(f"    {item.relative_path}")
        lines.extend(f"      - {reason}" for reason in item.reasons)

    lines.extend(
        [
            "",
            "Purple detection is best effort from existing on-disk metadata.",
            "Labels stored only in darktable's database are not visible.",
            styled("No files changed.", _BOLD),
        ]
    )
    return "\n".join(lines) + "\n"
