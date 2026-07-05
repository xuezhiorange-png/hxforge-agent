# TASK-016 Alpha Preview v0.1 — Expected Outputs (placeholder)

This directory is reserved for **golden output JSON files** that will
describe the expected outputs of the future trial runner against each fixture
skeleton under `../fixtures/`.

## Current state of this directory

In slice `TASK-016-TRIAL-001`, **this directory contains no golden output
JSON files**. The directory exists only as a placeholder so that the
`../README.md` reference to this path is valid.

## Why golden outputs are absent in this slice

Per the design document (`docs/trials/TASK-016-alpha-preview-v0.1.md`,
section 8 + section 9 + section 11), golden outputs are produced and
verified by the runner / golden-verification-test work that is scoped to a
later slice:

- `TASK-016-TRIAL-004`: add minimal runner script
- `TASK-016-TRIAL-005`: add golden verification tests and CI manifest ownership

Until Charles separately authorizes those slices, no golden output JSON
files are produced, no runner is implemented, no test code is added, and no
CI shard-manifest changes are made.

## What will eventually live here (not in this slice)

When a later explicitly-authorized slice implements the runner, the following
files are expected to land in this directory:

| File (future, not in this slice) | Future case | Future expected runner output |
|---|---|---|
| `case_001_result.golden.json` | catalog_success | success JSON with catalog_content_hash, ordered_geometry_ids, record_hashes |
| `case_002_result.golden.json` | hairpin_success | success JSON with hairpin_geometry_id and reference IDs |
| `case_003_blocker.golden.json` | unapproved_geometry | blocker JSON with error_code=geometry_record_unapproved |
| `case_004_blocker.golden.json` | missing_pipe_reference | blocker JSON with error_code=geometry_reference_missing, reference_field=pipe_geometry_id |
| `case_005_blocker.golden.json` | dimension_inconsistent | blocker JSON with error_code=geometry_dimension_inconsistent |

## Governance reminder

- This directory's existence does NOT authorize the runner or golden outputs
  to be implemented.
- Each future file here requires its own explicit Charles authorization via
  `TASK-016-TRIAL-004` or `TASK-016-TRIAL-005`.
- TASK-017+ remains blocked.
- TASK-015A is not mutated.
- Frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract bodies
  are not mutated.

## Slice marker

This directory is tagged with the slice identifier `TASK-016-TRIAL-001` and
will be expanded in later explicitly-authorized slices.