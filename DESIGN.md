# raw-clean design

## Summary

`raw-clean` supports a JPEG-first photography workflow:

> Shoot RAW+JPEG, triage the JPEGs, and keep RAWs only by exception.

A photographer marks an exceptional image **purple** in darktable, on either the JPEG or
RAW. When that label is visible in existing on-disk XMP metadata, `raw-clean` renames the
associated RAW from a name such as `DSCF1234.RAF` to `DSCF1234.KEEP.RAF`. A RAW can also be
marked manually by adding `.KEEP` to its filename.

Unmarked RAWs are moved to a separate, reversible quarantine rather than permanently
deleted.

> Purple means “make this a keeper.” `.KEEP` means “this is a keeper.”

Purple is a convenient request. The `.KEEP` filename is the durable guarantee. Quarantine
is the safety net, and the dry-run report is the human verification step.

## Why the tool exists

For this workflow, the camera's JPEG is normally the final photograph. RAW files are useful
only occasionally—for difficult exposure recovery or unusually valuable photographs that
may warrant substantial future editing. Keeping every RAW adds storage and management work
without much benefit.

The tool deliberately does not decide whether a photograph is good. The photographer makes
that decision while reviewing images. `raw-clean` only applies the resulting retention
signal safely and consistently.

## Everyday workflow

1. Capture RAW+JPEG.
2. Review JPEGs and delete rejects in darktable or another viewer.
3. Mark the few images whose RAWs should survive with darktable's purple colour label.
4. Allow darktable to write or synchronize sidecar metadata, if needed.
5. Run a read-only preview:

   ```console
   raw-clean scan SHOOT_DIR
   ```

6. Check the protected count, purple keeper filenames, quarantine count, and orphan warnings.
7. Apply the plan:

   ```console
   raw-clean quarantine SHOOT_DIR
   ```

8. Inspect and manually purge the quarantine later.

The tool reads existing files only. It does not inspect or modify darktable's catalog, so a
label stored only in that database is not visible to `raw-clean`.

## Retention rules

| Condition | Result |
| --- | --- |
| RAW is named `NAME.KEEP.RAF` or equivalent | Preserve it, regardless of JPEG or metadata |
| Ordinary RAW; purple found on its RAW or matching JPEG | Rename it to include `.KEEP` and preserve it |
| Ordinary RAW; no purple; matching JPEG exists | Quarantine the RAW and its RAW-specific sidecar |
| Ordinary RAW; no purple; matching JPEG is absent | Warn and quarantine only after extra confirmation |
| Relevant metadata is unreadable or malformed | Block the affected RAW and warn |
| File association or destination is ambiguous | Block the affected RAW and warn |
| Sidecar is absent | Treat it as no observed purple; this is normal |

JPEGs and JPEG-specific sidecars are never renamed, moved, edited, or deleted.

Files match only within the same directory and by the same base filename. Extension matching
is case-insensitive. `.KEEP` is ignored only when finding the base name of a marked RAW.
Ambiguous matches are blocked rather than guessed through.

## Examples

```text
DSCF1001.JPG + DSCF1001.RAF              → RAW quarantined
DSCF1002.JPG [purple] + DSCF1002.RAF     → RAW becomes DSCF1002.KEEP.RAF
DSCF1003.JPG + DSCF1003.RAF [purple]     → RAW becomes DSCF1003.KEEP.RAF
DSCF1004.KEEP.RAF (no JPEG)              → RAW preserved
DSCF1005.RAF (no JPEG)                   → warned; extra approval required
```

If more than one RAW or JPEG shares the same stem, the association is considered ambiguous.
For example, `IMG0001.RAF`, `IMG0001.DNG`, and `IMG0001.JPG` are blocked rather than treating
one JPEG label as a retention request for both RAWs.

## Purple detection

Purple detection is intentionally best effort. Darktable may keep labels only in its catalog
until sidecars are synchronized, and future metadata formats may differ. The tool therefore:

- reads only existing on-disk XMP sidecars;
- checks both the JPEG and RAW sidecars;
- treats a label on either member as one retention request;
- accepts missing sidecars and zero purple labels as normal;
- does not claim that label detection is complete or “verified”;
- blocks an affected RAW on an actual read or parse error;
- does not silently disable the metadata reader and treat everything as unlabelled.

If one relevant sidecar is malformed, the RAW is blocked even if the other sidecar reports
purple. An existing `.KEEP` filename remains authoritative and requires no metadata check.

## Safety model

The safety properties are more important than convenience:

1. `scan` is strictly read-only.
2. `.KEEP` always wins.
3. Observed purple is promoted to `.KEEP` before any quarantine moves begin.
4. Every planned destination is checked before mutation.
5. Existing files are never overwritten.
6. Errors and ambiguous mappings protect the affected RAW.
7. Orphan RAWs require a separate explicit confirmation.
8. RAW-specific sidecars move or are renamed with their RAW.
9. JPEGs and JPEG-side sidecars are never changed.
10. Quarantine is outside the scanned tree and preserves relative paths.
11. Initial implementations refuse cross-filesystem moves rather than using copy-and-delete.
12. The tool has no routine permanent-delete command.

Filesystem operations cannot form one global transaction. The tool applies atomic
same-filesystem renames in a careful order, stops on unexpected failures, and reports partial
progress clearly. Separate quarantine runs use separate sibling directories rather than
silently merging their contents.

## Human-readable reporting

The operator is the final check against missing or unsynchronized labels. Reports should make
these items especially obvious:

- total RAW files found;
- existing `.KEEP` files;
- newly detected purple keepers, including exact filenames;
- total RAWs that will remain protected;
- ordinary quarantine candidates;
- orphan candidates, including names;
- blocked files and reasons;
- approximate bytes moved.

Every RAW belongs to exactly one top-level category:

```text
total RAWs = existing KEEP + promotions + ordinary quarantine + orphan quarantine + blocked
```

TTY output may use bold and selective colour, but wording—not colour alone—must carry the
meaning. Redirected output and `NO_COLOR` mode remain plain and legible.

## Supported file concepts

RAW recognition uses a conservative allowlist of common formats, initially expected to
include formats such as RAF, CR2, CR3, NEF, ARW, ORF, RW2, and DNG. Recognition is
case-insensitive while original filename casing is preserved.

Only regular files are considered, and recursive discovery does not follow directory
symlinks. A RAW sidecar is expected to use darktable's normal image-name-plus-`.xmp` form,
such as `DSCF1234.RAF.xmp`.

Renaming a RAW outside darktable may leave darktable's catalog referring to its old path. That
is an accepted consequence of making `.KEEP` an application-independent marker; the tool
will not rewrite darktable's database.

## Non-goals

`raw-clean` is not intended to provide:

- photo review, editing, or RAW development;
- automatic judgments about image quality;
- a taxonomy of retention reasons such as `BEST`, `PRINT`, or `RECOVER`;
- custom marker sidecars or a central photo database;
- darktable catalog access or mutation;
- guarantees about unsynchronized, database-only labels;
- elaborate confidence scoring or metadata preflight rituals;
- automatic archival or permanent deletion.

The intended result is a small, auditable, reversible utility—not a photo-management system.

## Implementation guidance

Planning and mutation must remain separate. Both `scan` and `quarantine` should build the
same complete plan; reporting displays that plan, while execution applies it only after
preflight and confirmation.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the staged implementation, proposed
Python structure, and testing strategy.
