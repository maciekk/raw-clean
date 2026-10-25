"""Reading of existing darktable XMP metadata."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

DARKTABLE_NAMESPACE = "http://darktable.sf.net/"
RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP_NAMESPACE = "http://ns.adobe.com/xap/1.0/"
PURPLE_LABEL = 4


class MetadataError(Exception):
    """Raised when an existing sidecar cannot be interpreted safely."""


def read_color_labels(sidecar: Path) -> frozenset[int]:
    """Read darktable colour-label numbers from one existing XMP sidecar.

    Darktable stores its labels as an RDF sequence in
    ``darktable:colorlabels``. Purple has value 4. We also recognize the
    standard XMP ``Label="Purple"`` form which darktable itself imports.
    """
    try:
        root = ElementTree.parse(sidecar).getroot()
    except (OSError, ElementTree.ParseError) as error:
        raise MetadataError(f"cannot read XMP {sidecar.name}: {error}") from error

    labels: set[int] = set()
    colorlabels_tag = f"{{{DARKTABLE_NAMESPACE}}}colorlabels"
    rdf_li_tag = f"{{{RDF_NAMESPACE}}}li"

    for colorlabels in root.iter(colorlabels_tag):
        for item in colorlabels.iter(rdf_li_tag):
            value = (item.text or "").strip()
            try:
                label = int(value)
            except ValueError as error:
                raise MetadataError(
                    f"invalid darktable colour label {value!r} in {sidecar.name}"
                ) from error
            if label not in range(5):
                raise MetadataError(
                    f"unknown darktable colour label {label!r} in {sidecar.name}"
                )
            labels.add(label)

    xmp_label = f"{{{XMP_NAMESPACE}}}Label"
    for element in root.iter():
        attribute = element.attrib.get(xmp_label)
        if attribute is not None and attribute.casefold() == "purple":
            labels.add(PURPLE_LABEL)
        if element.tag == xmp_label and (element.text or "").strip().casefold() == "purple":
            labels.add(PURPLE_LABEL)

    return frozenset(labels)


def has_purple_label(sidecar: Path) -> bool:
    """Return whether an existing sidecar contains an observable purple label."""
    return PURPLE_LABEL in read_color_labels(sidecar)
