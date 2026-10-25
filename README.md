# raw-clean

`raw-clean` will be a small, local command-line utility for a JPEG-first photography
workflow. It will preserve selected RAW files using a durable `.KEEP` filename marker and
move other RAWs into a reversible quarantine.

The intended workflow is:

```console
raw-clean scan SHOOT_DIR
raw-clean quarantine SHOOT_DIR
```

The read-only `scan` command is implemented. It recursively inventories a shoot, reads
existing darktable XMP labels, applies the retention rules, and reports the resulting plan.
It never changes files. The `quarantine` command is not implemented yet.

See [DESIGN.md](DESIGN.md) for the workflow and safety model, and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the staged implementation plan.

## Current usage

```console
raw-clean scan ~/Pictures/2026-10-17-shoot
```

A scan exits with status `0` when it produces a complete plan and status `1` when files are
blocked or the shoot cannot be scanned safely. Missing XMP and zero detected purple labels
are normal and do not block a plan.

The initial RAW allowlist is RAF, CR2, CR3, NEF, ARW, ORF, RW2, and DNG. Matching is
case-insensitive. Purple detection recognizes darktable's `darktable:colorlabels` RDF
sequence, where purple is value `4`, as well as the standard XMP `Label="Purple"` form.

## Development

The project requires Python 3.11 or newer. Install it in an isolated environment with the
development dependencies:

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```
