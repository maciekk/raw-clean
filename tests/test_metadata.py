"""Tests for darktable XMP colour-label reading."""

from pathlib import Path

import pytest

from raw_clean.metadata import MetadataError, has_purple_label, read_color_labels

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "name",
    ["purple-jpeg.JPG.xmp", "purple-raw.RAF.xmp", "multiple-labels.xmp"],
)
def test_detects_darktable_purple(name: str) -> None:
    assert has_purple_label(FIXTURES / name)


def test_reads_multiple_labels() -> None:
    assert read_color_labels(FIXTURES / "multiple-labels.xmp") == frozenset({1, 4})


def test_non_purple_labels_are_not_purple() -> None:
    assert not has_purple_label(FIXTURES / "no-purple.xmp")


def test_malformed_xmp_is_an_error() -> None:
    with pytest.raises(MetadataError, match="cannot read XMP"):
        has_purple_label(FIXTURES / "malformed.xmp")


def test_standard_xmp_purple_label_is_recognized(tmp_path: Path) -> None:
    sidecar = tmp_path / "photo.jpg.xmp"
    sidecar.write_text(
        """<?xml version="1.0"?>
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
          <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
            <rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/"
                             xmp:Label="Purple" />
          </rdf:RDF>
        </x:xmpmeta>
        """,
        encoding="utf-8",
    )

    assert has_purple_label(sidecar)
