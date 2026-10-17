# raw-clean

`raw-clean` will be a small, local command-line utility for a JPEG-first photography
workflow. It will preserve selected RAW files using a durable `.KEEP` filename marker and
move other RAWs into a reversible quarantine.

The intended workflow is:

```console
raw-clean scan SHOOT_DIR
raw-clean quarantine SHOOT_DIR
```

The project is currently at the initial scaffolding stage. **The command does not yet scan
or modify photographs.** See [DESIGN.md](DESIGN.md) for the workflow and safety model, and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the staged implementation plan.

## Development

The project requires Python 3.11 or newer. Install it in an isolated environment with the
development dependencies:

```console
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```
