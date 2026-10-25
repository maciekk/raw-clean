"""Read-only retention and quarantine planning."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from raw_clean.discovery import (
    Inventory,
    association_key,
    discover,
    is_keep_raw,
    sidecars_for,
)
from raw_clean.metadata import MetadataError, has_purple_label
from raw_clean.models import Category, Plan, PlannedRaw


class PlanningError(Exception):
    """Raised when no complete plan can be produced."""


def _path_exists(path: Path) -> bool:
    """Check for any destination entry, including a broken symlink."""
    return os.path.lexists(path)


def _raw_size(raw: Path) -> tuple[int, str | None]:
    try:
        return raw.stat().st_size, None
    except OSError as error:
        return 0, f"cannot read RAW file information: {error}"


def _promotion_destination(raw: Path) -> Path:
    return raw.with_name(f"{raw.stem}.KEEP{raw.suffix}")


def _choose_quarantine_root(shoot_root: Path) -> Path:
    """Choose a currently unused sibling directory without creating it."""
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    shoot_name = shoot_root.name or "root"
    base = shoot_root.parent / f"{shoot_name}-RAW-Quarantine-{timestamp}"
    candidate = base
    suffix = 2
    while _path_exists(candidate):
        candidate = base.with_name(f"{base.name}-{suffix}")
        suffix += 1
    return candidate


def _blocked_item(
    inventory: Inventory,
    raw: Path,
    size: int,
    reasons: list[str],
    *,
    jpeg: Path | None = None,
    raw_sidecar: Path | None = None,
) -> PlannedRaw:
    return PlannedRaw(
        source=raw,
        relative_path=raw.relative_to(inventory.root),
        category=Category.BLOCKED,
        size=size,
        jpeg=jpeg,
        raw_sidecar=raw_sidecar,
        reasons=tuple(reasons),
    )


def _plan_raw(
    inventory: Inventory, raw: Path, quarantine_root: Path
) -> PlannedRaw:
    size, size_error = _raw_size(raw)
    relative_path = raw.relative_to(inventory.root)

    # The filename marker is authoritative. Association and metadata problems do not
    # weaken an existing KEEP declaration.
    if is_keep_raw(raw):
        return PlannedRaw(
            source=raw,
            relative_path=relative_path,
            category=Category.KEEP_EXISTING,
            size=size,
        )

    reasons: list[str] = []
    if size_error:
        reasons.append(size_error)

    key = association_key(raw)
    matching_raws = inventory.raws_by_key[key]
    if len(matching_raws) > 1:
        names = ", ".join(path.name for path in matching_raws)
        reasons.append(f"multiple RAWs share this stem: {names}")

    matching_jpegs = inventory.jpegs_by_key.get(key, ())
    jpeg: Path | None = None
    if len(matching_jpegs) > 1:
        names = ", ".join(path.name for path in matching_jpegs)
        reasons.append(f"multiple JPEGs share this stem: {names}")
    elif matching_jpegs:
        jpeg = matching_jpegs[0]

    raw_sidecars = sidecars_for(inventory, raw)
    raw_sidecar: Path | None = None
    if len(raw_sidecars) > 1:
        names = ", ".join(path.name for path in raw_sidecars)
        reasons.append(f"multiple RAW sidecars match: {names}")
    elif raw_sidecars:
        raw_sidecar = raw_sidecars[0]

    jpeg_sidecar: Path | None = None
    if jpeg is not None:
        jpeg_sidecars = sidecars_for(inventory, jpeg)
        if len(jpeg_sidecars) > 1:
            names = ", ".join(path.name for path in jpeg_sidecars)
            reasons.append(f"multiple JPEG sidecars match: {names}")
        elif jpeg_sidecars:
            jpeg_sidecar = jpeg_sidecars[0]

    if reasons:
        return _blocked_item(
            inventory,
            raw,
            size,
            reasons,
            jpeg=jpeg,
            raw_sidecar=raw_sidecar,
        )

    purple = False
    for sidecar in (raw_sidecar, jpeg_sidecar):
        if sidecar is None:
            continue
        try:
            purple = has_purple_label(sidecar) or purple
        except MetadataError as error:
            reasons.append(str(error))

    if reasons:
        return _blocked_item(
            inventory,
            raw,
            size,
            reasons,
            jpeg=jpeg,
            raw_sidecar=raw_sidecar,
        )

    if purple:
        destination = _promotion_destination(raw)
        if _path_exists(destination):
            reasons.append(f"promotion destination already exists: {destination.name}")

        if raw_sidecar is not None:
            sidecar_destination = destination.with_name(
                destination.name + raw_sidecar.suffix
            )
            if _path_exists(sidecar_destination):
                reasons.append(
                    "promotion sidecar destination already exists: "
                    f"{sidecar_destination.name}"
                )

        if reasons:
            return _blocked_item(
                inventory,
                raw,
                size,
                reasons,
                jpeg=jpeg,
                raw_sidecar=raw_sidecar,
            )

        return PlannedRaw(
            source=raw,
            relative_path=relative_path,
            category=Category.PROMOTE,
            size=size,
            jpeg=jpeg,
            raw_sidecar=raw_sidecar,
            destination=destination,
        )

    category = Category.QUARANTINE if jpeg is not None else Category.QUARANTINE_ORPHAN
    return PlannedRaw(
        source=raw,
        relative_path=relative_path,
        category=category,
        size=size,
        jpeg=jpeg,
        raw_sidecar=raw_sidecar,
        destination=quarantine_root / relative_path,
    )


def build_plan(root: Path) -> Plan:
    """Discover a shoot and assign exactly one safe outcome to every RAW."""
    try:
        inventory = discover(root)
    except OSError as error:
        raise PlanningError(f"cannot scan shoot directory: {error}") from error

    quarantine_root = _choose_quarantine_root(inventory.root)
    items = tuple(
        _plan_raw(inventory, raw, quarantine_root) for raw in inventory.raw_files
    )
    return Plan(
        root=inventory.root,
        quarantine_root=quarantine_root,
        items=items,
    )
