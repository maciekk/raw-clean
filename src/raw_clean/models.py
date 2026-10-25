"""Domain models for read-only raw-clean plans."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Category(Enum):
    """The one retention outcome assigned to each discovered RAW."""

    KEEP_EXISTING = "existing KEEP"
    PROMOTE = "purple promotion"
    QUARANTINE = "ordinary quarantine"
    QUARANTINE_ORPHAN = "orphan quarantine"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PlannedRaw:
    """A decision about one RAW file, including files relevant to that decision."""

    source: Path
    relative_path: Path
    category: Category
    size: int
    jpeg: Path | None = None
    raw_sidecar: Path | None = None
    destination: Path | None = None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    """A complete, immutable plan for one shoot directory."""

    root: Path
    quarantine_root: Path
    items: tuple[PlannedRaw, ...]

    def in_category(self, category: Category) -> tuple[PlannedRaw, ...]:
        """Return plan items in a category, preserving display order."""
        return tuple(item for item in self.items if item.category is category)

    @property
    def total_raws(self) -> int:
        return len(self.items)

    @property
    def existing_keepers(self) -> tuple[PlannedRaw, ...]:
        return self.in_category(Category.KEEP_EXISTING)

    @property
    def promotions(self) -> tuple[PlannedRaw, ...]:
        return self.in_category(Category.PROMOTE)

    @property
    def ordinary_quarantine(self) -> tuple[PlannedRaw, ...]:
        return self.in_category(Category.QUARANTINE)

    @property
    def orphan_quarantine(self) -> tuple[PlannedRaw, ...]:
        return self.in_category(Category.QUARANTINE_ORPHAN)

    @property
    def blocked(self) -> tuple[PlannedRaw, ...]:
        return self.in_category(Category.BLOCKED)

    @property
    def protected_count(self) -> int:
        return len(self.existing_keepers) + len(self.promotions)

    @property
    def quarantine_size(self) -> int:
        return sum(
            item.size
            for item in (*self.ordinary_quarantine, *self.orphan_quarantine)
        )
