"""Filesystem discovery and photograph association."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAW_EXTENSIONS = frozenset(
    {".arw", ".cr2", ".cr3", ".dng", ".nef", ".orf", ".raf", ".rw2"}
)
JPEG_EXTENSIONS = frozenset({".jpeg", ".jpg"})

AssociationKey = tuple[Path, str]
SidecarKey = tuple[Path, str]


class DiscoveryError(Exception):
    """Raised when a complete and trustworthy inventory cannot be built."""


@dataclass(frozen=True)
class Inventory:
    """The relevant regular files found below one shoot directory."""

    root: Path
    raw_files: tuple[Path, ...]
    raws_by_key: dict[AssociationKey, tuple[Path, ...]]
    jpegs_by_key: dict[AssociationKey, tuple[Path, ...]]
    sidecars_by_key: dict[SidecarKey, tuple[Path, ...]]


def is_keep_raw(path: Path) -> bool:
    """Return whether a RAW has the exact, authoritative `.KEEP` marker."""
    return path.suffix.lower() in RAW_EXTENSIONS and path.stem.endswith(".KEEP")


def association_key(path: Path) -> AssociationKey:
    """Return the directory-and-stem key used to associate JPEG and RAW files."""
    stem = path.stem
    if is_keep_raw(path):
        stem = stem.removesuffix(".KEEP")
    return path.parent, stem.casefold()


def sidecars_for(inventory: Inventory, image: Path) -> tuple[Path, ...]:
    """Return sidecars whose image filename matches case-insensitively."""
    return inventory.sidecars_by_key.get((image.parent, image.name.casefold()), ())


def discover(root: Path) -> Inventory:
    """Recursively inventory relevant regular files without following symlinks."""
    root = root.expanduser()
    if root.is_symlink():
        raise DiscoveryError(f"shoot directory must not be a symlink: {root}")
    if not root.exists():
        raise DiscoveryError(f"shoot directory does not exist: {root}")
    if not root.is_dir():
        raise DiscoveryError(f"shoot path is not a directory: {root}")

    root = root.resolve()
    raw_files: list[Path] = []
    raw_groups: dict[AssociationKey, list[Path]] = {}
    jpeg_groups: dict[AssociationKey, list[Path]] = {}
    sidecar_groups: dict[SidecarKey, list[Path]] = {}
    walk_errors: list[str] = []

    def record_walk_error(error: OSError) -> None:
        walk_errors.append(str(error))

    for directory, dirnames, filenames in os.walk(
        root, followlinks=False, onerror=record_walk_error
    ):
        directory_path = Path(directory)
        # os.walk does not descend through directory symlinks when followlinks is false,
        # but pruning them here also makes that policy explicit.
        dirnames[:] = [
            name for name in dirnames if not (directory_path / name).is_symlink()
        ]

        for name in filenames:
            path = directory_path / name
            if path.is_symlink() or not path.is_file():
                continue

            extension = path.suffix.lower()
            if extension in RAW_EXTENSIONS:
                raw_files.append(path)
                raw_groups.setdefault(association_key(path), []).append(path)
            elif extension in JPEG_EXTENSIONS:
                jpeg_groups.setdefault(association_key(path), []).append(path)
            elif extension == ".xmp":
                image_name = name[: -len(path.suffix)]
                sidecar_groups.setdefault(
                    (directory_path, image_name.casefold()), []
                ).append(path)

    if walk_errors:
        details = "; ".join(walk_errors)
        raise DiscoveryError(f"could not read the complete shoot tree: {details}")

    def freeze_groups(groups: dict[AssociationKey, list[Path]]) -> dict[AssociationKey, tuple[Path, ...]]:
        return {
            key: tuple(sorted(paths, key=lambda path: path.name.casefold()))
            for key, paths in groups.items()
        }

    return Inventory(
        root=root,
        raw_files=tuple(
            sorted(raw_files, key=lambda path: str(path.relative_to(root)).casefold())
        ),
        raws_by_key=freeze_groups(raw_groups),
        jpegs_by_key=freeze_groups(jpeg_groups),
        sidecars_by_key=freeze_groups(sidecar_groups),
    )
