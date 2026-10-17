# raw-clean implementation plan

## Purpose

`raw-clean` is a small, local command-line utility for a JPEG-first photography workflow.
The photographer reviews JPEGs and marks exceptional images purple in darktable. The tool
then makes RAW-retention decisions durable by renaming the corresponding RAW to include
`.KEEP`, and moves unneeded RAWs into a reversible quarantine.

The guiding principle is:

> First calculate and clearly present the right answer. Only then apply it.

The implementation should remain small, readable, and easy to audit. Python is preferred
over shell because safe path handling, XML parsing, collision detection, and recoverable
filesystem operations are central to the tool.

## User-facing commands

```console
raw-clean scan SHOOT_DIR
raw-clean quarantine SHOOT_DIR
```

`scan` is read-only. `quarantine` recalculates and displays the same plan, asks for
confirmation, promotes purple RAWs to `.KEEP`, and then quarantines the remaining eligible
RAWs.

A shorthand such as `raw-clean SHOOT_DIR` may eventually alias `scan`, but explicit commands
come first.

## Core rules

1. A RAW already named `NAME.KEEP.<raw-extension>` is always preserved.
2. Purple found in the existing darktable XMP for either a RAW or its matching JPEG causes
   an ordinary RAW to be promoted to `NAME.KEEP.<raw-extension>`.
3. An unmarked RAW with a matching JPEG is a normal quarantine candidate.
4. An unmarked RAW without a matching JPEG is an orphan candidate. It may be quarantined,
   but only after an additional explicit confirmation.
5. A malformed or unreadable relevant XMP sidecar blocks action on the affected RAW.
6. Ambiguous associations and destination collisions block action rather than being guessed
   through.
7. JPEGs and JPEG-specific XMP sidecars are never changed.
8. A RAW-specific XMP sidecar moves or is renamed together with its RAW.
9. Existing files are never overwritten.
10. The tool does not permanently delete images.

Purple detection is deliberately best effort. Missing XMP and a zero-purple result are both
normal. Labels that exist only in darktable's database cannot be observed by this tool.

## Decisions that tighten the original design

### Multiple RAWs with one stem

If more than one RAW shares the same directory and base stem, for example:

```text
IMG0001.JPG
IMG0001.RAF
IMG0001.DNG
```

the association is ambiguous. All affected RAWs are blocked and reported. A JPEG label will
not implicitly retain multiple RAW files.

Likewise, multiple matching JPEGs, including case-only or `.jpg`/`.jpeg` collisions, are
ambiguous and block the affected RAW.

### Malformed metadata despite another positive label

Any malformed or unreadable relevant sidecar blocks the affected RAW, even if the other
member's sidecar successfully reports purple. This is intentionally conservative. An
existing `.KEEP` name still wins without metadata inspection.

### Symlinks and file types

Discovery considers regular files only and does not follow directory symlinks. This avoids
escaping the requested shoot tree or operating on surprising targets.

### Confirmation model

A quarantine run asks for:

1. General confirmation of promotions and ordinary quarantine moves.
2. A separate, explicit confirmation before moving orphan RAWs.

Merely invoking the `quarantine` command does not imply approval of orphan moves.

### Operation ordering

The tool computes and preflights a complete plan before mutation. During execution it:

1. Applies all purple-to-`.KEEP` promotions, including RAW sidecars.
2. Stops before quarantine if promotion preflight or setup fails.
3. Moves ordinary quarantine candidates.
4. Moves orphan candidates only if separately approved.

Unexpected runtime failures stop further work and produce a clear partial-operation report.
Individual moves should be atomic same-filesystem renames.

### Quarantine layout

Each execution uses a unique sibling directory, for example:

```text
2026-10-17-shoot/
2026-10-17-shoot-RAW-Quarantine-20261017T143012/
```

Relative subdirectories from the shoot are preserved. Unique run directories avoid silently
merging separate operations and make collision behavior straightforward.

The tool initially refuses cross-filesystem moves rather than falling back to copy-and-delete.

### Darktable catalog behavior

Renaming a RAW outside darktable may leave darktable's catalog referring to its former path.
This is expected: `.KEEP` is intended to be the durable, application-independent retention
marker. The documentation and execution summary should mention this without attempting to
modify darktable's database.

## Plan model and accounting

Both `scan` and `quarantine` consume the same immutable plan. Every discovered RAW belongs to
exactly one top-level category:

- existing `.KEEP`
- purple promotion
- ordinary quarantine
- orphan quarantine
- blocked

The report must make this equation true and visible:

```text
total RAWs = existing KEEP + promotions + ordinary quarantine + orphan quarantine + blocked
```

Each planned mutation contains its source and destination paths. Warnings and block reasons
are represented explicitly rather than inferred while rendering output.

## Proposed source layout

```text
raw-clean/
├── pyproject.toml
├── README.md
├── IMPLEMENTATION_PLAN.md
├── src/
│   └── raw_clean/
│       ├── __init__.py
│       ├── cli.py          # argument parsing, confirmations, and exit codes
│       ├── models.py       # immutable dataclasses and enums
│       ├── discovery.py    # filesystem inventory and file associations
│       ├── metadata.py     # darktable XMP parsing
│       ├── planning.py     # retention policy; no filesystem mutation
│       ├── reporting.py    # TTY and plain-text summaries
│       └── execution.py    # checked renames and quarantine moves
└── tests/
    ├── fixtures/
    └── ...
```

Prefer standard-library functionality: `argparse`, `pathlib`, `dataclasses`, `enum`, and
`xml.etree.ElementTree`. `pytest` is an appropriate development dependency.

This module structure is a guide, not a requirement to create abstractions prematurely.
Plain functions and small domain-specific dataclasses are preferred over class hierarchies
or a generic file-operation framework.

## Implementation stages

### Stage 0 — Confirm metadata and operation details

- Collect small, anonymized darktable-generated XMP fixtures for:
  - purple on a JPEG
  - purple on a RAW
  - multiple labels including purple
  - labels without purple
  - malformed XML
- Confirm darktable sidecar naming in the installed version.
- Confirm the exact purple value and XML namespace/structure.
- Decide the initial RAW extension allowlist.
- Document the exit-code policy and precise confirmation prompts.

Metadata fixtures should be checked into `tests/fixtures/`. They are integration examples,
not a promise that every future darktable version uses the same representation.

### Stage 1 — Complete read-only planner

Implement `raw-clean scan` with no mutation code path:

- Recursive regular-file discovery without following directory symlinks.
- Case-insensitive RAW/JPEG extension recognition while preserving actual names.
- `.KEEP` recognition.
- JPEG and RAW-sidecar association.
- Ambiguity and collision detection.
- Purple parsing from JPEG and RAW XMP.
- Complete categorization and destination calculation.
- Human-readable report with exact totals, keeper names, orphan names, bytes, and warnings.
- Selective ANSI emphasis only for a TTY and when `NO_COLOR` is not set.
- Legible plain text when redirected or piped.

All planning-policy acceptance tests should pass before mutation is added.

### Stage 2 — Safe promotion

Add the first mutation phase behind `raw-clean quarantine`:

- Recompute the plan at invocation time.
- Display the complete plan and request general confirmation.
- Preflight every promotion source and destination.
- Rename purple RAWs to `.KEEP`.
- Rename RAW-specific XMP sidecars consistently.
- Never overwrite.
- Make completed promotions naturally safe on rerun.
- Stop before quarantine if the promotion phase cannot be completed safely.

During development this stage may temporarily stop after promotions, but it should not be
presented as a complete production quarantine workflow until Stage 3 is implemented.

### Stage 3 — Quarantine execution

- Create a unique sibling quarantine directory safely.
- Preserve relative subdirectory structure.
- Move RAWs and RAW-specific sidecars together.
- Require separate approval for orphan RAWs.
- Refuse cross-filesystem operations.
- Stop on unexpected failures and report completed, pending, skipped, and failed actions.
- Test interruptions and repeated runs.

### Stage 4 — Recovery, packaging, and polish

- Write a simple manifest recording original and quarantine paths.
- Add a `restore` command after the manifest format is stable.
- Add conspicuously named opt-in flags for deliberate scripted operation.
- Improve concise diagnostics and operation logs.
- Add packaging, installation, and usage documentation.
- Initialize and publish the GitHub repository when the initial skeleton is ready.

A manifest is considered part of the intended safety story even if `restore` is implemented
later. It should be a transparent format such as JSON Lines rather than a database.

## Testing strategy

Most tests should create temporary directory trees and assert against a generated plan.
Mutation tests should operate only in temporary directories.

Important cases include:

- ordinary JPEG/RAW pair
- orphan RAW
- existing `.KEEP` with and without JPEG
- purple on JPEG only, RAW only, and both
- no sidecars and zero purple labels
- malformed and unreadable sidecars
- multiple labels in one sidecar
- duplicate RAW stems and duplicate JPEG stems
- destination collisions
- RAW sidecar promotion and quarantine
- spaces, Unicode, mixed-case extensions, and nested directories
- symlinks and non-regular files
- existing quarantine-like directories
- simulated interruption and rerun
- TTY versus non-TTY reporting
- `NO_COLOR`
- dry-run filesystem snapshots proving that scan changes nothing
- count invariants for every generated plan

## Readability guidelines

- Keep policy decisions in `planning.py`, separate from filesystem mutation.
- Use named dataclasses instead of loosely structured dictionaries.
- Use explicit categories such as `KEEP_EXISTING`, `PROMOTE`, `QUARANTINE`,
  `QUARANTINE_ORPHAN`, and `BLOCKED`.
- Prefer functions named for the workflow, such as `discover_raw_files`,
  `read_darktable_labels`, `build_plan`, `apply_promotions`, and
  `move_to_quarantine`.
- Comment safety reasoning and non-obvious domain behavior, not ordinary Python syntax.
- Avoid clever path transformations and hidden global state.
- Keep dependencies minimal and justify any runtime dependency before adding it.

## Definition of the first production-ready release

The first release is ready when:

- scan and quarantine are driven by the same tested plan;
- purple detection works against representative darktable XMP fixtures;
- scans are demonstrably read-only;
- `.KEEP`, malformed metadata, ambiguity, and overwrite protections are enforced;
- promotions happen before quarantine;
- orphan movement requires separate approval;
- quarantine is reversible through preserved paths and a manifest;
- interrupted runs fail visibly and can be inspected or safely rerun;
- reports make protected RAWs, purple promotions, orphan candidates, and blocked files
  obvious;
- JPEGs and JPEG-side sidecars are never modified.
