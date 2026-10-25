"""Tests for read-only RAW retention planning."""

from __future__ import annotations

import shutil
from pathlib import Path

from raw_clean.models import Category
from raw_clean.planning import build_plan

FIXTURES = Path(__file__).parent / "fixtures"


def make_file(path: Path, contents: bytes = b"raw") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return path


def add_fixture(shoot: Path, image_name: str, fixture: str) -> Path:
    destination = shoot / f"{image_name}.xmp"
    shutil.copyfile(FIXTURES / fixture, destination)
    return destination


def categories_by_name(shoot: Path) -> dict[str, Category]:
    return {
        item.source.relative_to(shoot.resolve()).as_posix(): item.category
        for item in build_plan(shoot).items
    }


def test_classifies_core_workflow(tmp_path: Path) -> None:
    make_file(tmp_path / "ordinary.JPG")
    make_file(tmp_path / "ordinary.RAF")
    make_file(tmp_path / "orphan.NEF")
    make_file(tmp_path / "manual.KEEP.CR3")

    make_file(tmp_path / "jpeg-purple.jpeg")
    make_file(tmp_path / "jpeg-purple.arw")
    add_fixture(tmp_path, "jpeg-purple.jpeg", "purple-jpeg.JPG.xmp")

    make_file(tmp_path / "nested" / "raw-purple.JPG")
    make_file(tmp_path / "nested" / "raw-purple.RW2")
    add_fixture(tmp_path / "nested", "raw-purple.RW2", "purple-raw.RAF.xmp")

    assert categories_by_name(tmp_path) == {
        "jpeg-purple.arw": Category.PROMOTE,
        "manual.KEEP.CR3": Category.KEEP_EXISTING,
        "nested/raw-purple.RW2": Category.PROMOTE,
        "ordinary.RAF": Category.QUARANTINE,
        "orphan.NEF": Category.QUARANTINE_ORPHAN,
    }


def test_missing_sidecars_and_zero_purple_are_normal(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    add_fixture(tmp_path, "photo.JPG", "no-purple.xmp")

    plan = build_plan(tmp_path)

    assert len(plan.ordinary_quarantine) == 1
    assert not plan.blocked


def test_purple_on_both_members_is_one_promotion(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    add_fixture(tmp_path, "photo.JPG", "purple-jpeg.JPG.xmp")
    add_fixture(tmp_path, "photo.RAF", "purple-raw.RAF.xmp")

    plan = build_plan(tmp_path)

    assert len(plan.promotions) == 1
    assert plan.promotions[0].destination == tmp_path / "photo.KEEP.RAF"


def test_malformed_relevant_sidecar_blocks_raw(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    add_fixture(tmp_path, "photo.JPG", "purple-jpeg.JPG.xmp")
    add_fixture(tmp_path, "photo.RAF", "malformed.xmp")

    plan = build_plan(tmp_path)

    assert len(plan.blocked) == 1
    assert "cannot read XMP" in plan.blocked[0].reasons[0]


def test_multiple_raws_with_one_stem_are_blocked(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    make_file(tmp_path / "PHOTO.dng")

    plan = build_plan(tmp_path)

    assert len(plan.blocked) == 2
    assert all("multiple RAWs" in item.reasons[0] for item in plan.blocked)


def test_multiple_jpegs_with_one_stem_block_raw(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "PHOTO.jpeg")
    make_file(tmp_path / "photo.RAF")

    plan = build_plan(tmp_path)

    assert len(plan.blocked) == 1
    assert "multiple JPEGs" in plan.blocked[0].reasons[0]


def test_existing_keep_wins_despite_ambiguous_stem(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.KEEP.RAF")
    make_file(tmp_path / "photo.DNG")

    plan = build_plan(tmp_path)

    assert len(plan.existing_keepers) == 1
    assert plan.existing_keepers[0].source.name == "photo.KEEP.RAF"
    assert len(plan.blocked) == 1


def test_promotion_destination_collision_blocks_raw(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    add_fixture(tmp_path, "photo.JPG", "purple-jpeg.JPG.xmp")
    add_fixture(tmp_path, "photo.RAF", "no-purple.xmp")
    make_file(tmp_path / "photo.KEEP.RAF.xmp", b"collision")

    plan = build_plan(tmp_path)

    assert len(plan.blocked) == 1
    assert "destination already exists" in plan.blocked[0].reasons[0]


def test_raw_sidecar_is_associated_with_planned_move(tmp_path: Path) -> None:
    make_file(tmp_path / "photo.JPG")
    make_file(tmp_path / "photo.RAF")
    sidecar = add_fixture(tmp_path, "photo.RAF", "no-purple.xmp")

    plan = build_plan(tmp_path)

    assert plan.ordinary_quarantine[0].raw_sidecar == sidecar


def test_directory_symlinks_are_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    make_file(outside / "hidden.RAF")
    shoot = tmp_path / "shoot"
    shoot.mkdir()
    (shoot / "linked").symlink_to(outside, target_is_directory=True)

    assert build_plan(shoot).total_raws == 0


def test_plan_accounting_and_sizes(tmp_path: Path) -> None:
    make_file(tmp_path / "one.JPG")
    make_file(tmp_path / "one.RAF", b"1234")
    make_file(tmp_path / "two.NEF", b"12")

    plan = build_plan(tmp_path)

    accounted = (
        len(plan.existing_keepers)
        + len(plan.promotions)
        + len(plan.ordinary_quarantine)
        + len(plan.orphan_quarantine)
        + len(plan.blocked)
    )
    assert plan.total_raws == accounted
    assert plan.quarantine_size == 6
    assert plan.ordinary_quarantine[0].destination == plan.quarantine_root / "one.RAF"
    assert plan.orphan_quarantine[0].destination == plan.quarantine_root / "two.NEF"
    assert plan.quarantine_root.parent == tmp_path.parent
    assert not plan.quarantine_root.exists()
