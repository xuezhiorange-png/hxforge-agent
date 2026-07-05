# TASK-016 Alpha Preview v0.1 — Expected Outputs

This directory holds **5 expected output JSON files** that describe the
expected outputs of the future trial runner against each fixture skeleton
under `../fixtures/`.

## Current state of this directory

In slice `TASK-016-TRIAL-002`, **this directory contains 5 expected output
JSON files**:

- `catalog_success.expected.json`
- `hairpin_success.expected.json`
- `unapproved_geometry.expected.json`
- `missing_pipe_reference.expected.json`
- `dimension_inconsistent.expected.json`

These are **static expected output skeletons** paired with the 5 fixture
skeletons under `../fixtures/`.

## What is still NOT in this slice (TASK-016-TRIAL-002)

Even with the expected output skeletons now present, the following are
**explicitly deferred** to later, separately-authorized slices:

- **Runner is still NOT implemented** — the `scripts/` directory does not
  exist. No code will load these expected files and compare against actual
  runner output until Charles separately authorizes `TASK-016-TRIAL-004`.
- **Tests are still NOT implemented** — no test code under `tests/` will
  consume these expected files until Charles separately authorizes
  `TASK-016-TRIAL-005`.
- **CI shard-manifest ownership is NOT modified** — `ci-shard-manifest.yml`
  is unchanged until Charles separately authorizes `TASK-016-TRIAL-005`.

## Hash origin

For the 2 success-case expected outputs (`catalog_success.expected.json`,
`hairpin_success.expected.json`), the `catalog_content_hash`, `record_hashes`,
and `ordered_geometry_ids` fields contain **real deterministic SHA-256
hashes and canonical ordering** that were computed from the corresponding
fixture skeletons at the time of `TASK-016-TRIAL-002` using the merged
TASK-016 implementation (PR #67 merge commit
`ac7a4152698f039b4d6795f6a814228cb3c43def`).

For the 3 blocker-case expected outputs (`unapproved_geometry.expected.json`,
`missing_pipe_reference.expected.json`, `dimension_inconsistent.expected.json`),
the `error_code` and `context` fields were also captured from running the
fixtures against the same TASK-016 implementation.

These values are **placeholders unless explicitly regenerated in a later
authorized slice** that re-runs the hashes against the canonical fixture
payload (e.g., if any fixture input is updated, the corresponding expected
output must also be regenerated atomically with the same commit, otherwise
the expected/actual diff would not be authoritative).

## What these files are NOT

These files are **not executable acceptance evidence yet**:

- No CI run consumes them.
- No test asserts that actual output equals these expected values.
- No runner code parses these files.
- No comparison logic exists anywhere in the repository.

They are documentation artifacts that record the expected runner output for
each fixture skeleton, intended for use by a future explicitly-authorized
slice (likely `TASK-016-TRIAL-005`) that implements golden-verification
tests.

## Defect-fix note for `unapproved_geometry.input.json`

The fixture skeleton at `../fixtures/unapproved_geometry.input.json` was
modified during `TASK-016-TRIAL-002` to fix a contract defect discovered
during expected-output generation:

- The TASK-016-TRIAL-001 version used `approval_state: "pending"`, but the
  TASK-016 implementation (PR #67, `src/hexagent/geometry_catalogs/catalog.py`
  line 414) explicitly does NOT raise `geometry_record_unapproved` at load
  time for the `"pending"` state — line 414 is a no-op `continue`.
- To preserve the fixture's intent (showing the unapproved-path blocker)
  while making the fixture actually trigger the blocker, the value was
  changed to `approval_state: "invalid_state"`, which is not in
  `VALID_APPROVAL_STATES = {approved, pending, rejected, retired}` and
  therefore triggers the line 381 check.
- This is recorded in the fixture's `_defect_note` field.

The `unapproved_geometry.expected.json` file reflects this fixed fixture.

## What will eventually live here (in later slices)

When a later explicitly-authorized slice implements golden-verification
tests (likely `TASK-016-TRIAL-005`), these 5 `.expected.json` files are
expected to be consumed by tests that:

1. Load each fixture input via `load_geometry_catalog()`.
2. Compare actual success/blocker output against the corresponding
   `expected/*.expected.json` file.
3. Assert exact match on `status`, `catalog_content_hash`, `ordered_geometry_ids`,
   `record_hashes` (for success) or `error_code`, `context` (for blocker).

Until those slices are separately authorized by Charles, no such test code
exists, and these expected files are documentation-only.

## Governance reminder

- These files' existence does NOT authorize the runner, tests, or CI shard
  ownership to be implemented.
- Each future slice touching these files requires its own explicit Charles
  authorization.
- TASK-017+ remains blocked.
- TASK-015A is not mutated.
- Frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract bodies
  are not mutated.

## Slice marker

These files are tagged with the slice identifier `TASK-016-TRIAL-002` (the
expected outputs themselves) and `TASK-016-TRIAL-001+TASK-016-TRIAL-002-defect-fix`
(the corrected fixture). Future slices may extend or regenerate these
artifacts under their own slice authorization.