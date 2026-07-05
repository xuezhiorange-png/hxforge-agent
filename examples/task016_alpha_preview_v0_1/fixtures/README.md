# TASK-016 Alpha Preview v0.1 — Fixture Skeletons

This directory holds **5 fixture skeleton JSON files** that mirror the trial
cases defined in the design document (`docs/trials/TASK-016-alpha-preview-v0.1.md`,
section 8). Each fixture skeleton is deterministic, human-readable, and
**contains no engineering calculation output**.

## Fixture skeletons

| Fixture | case_type | expected_status | Intended future blocker (if any) |
|---|---|---|---|
| `catalog_success.input.json` | success | `pass` | — |
| `hairpin_success.input.json` | success | `pass` | — |
| `unapproved_geometry.input.json` | blocker | `blocked` | `geometry_record_unapproved` |
| `missing_pipe_reference.input.json` | blocker | `blocked` | `geometry_reference_missing` (with `reference_field: pipe_geometry_id`) |
| `dimension_inconsistent.input.json` | blocker | `blocked` | `geometry_dimension_inconsistent` |

## Common JSON envelope (per design §9)

Every fixture skeleton carries the following top-level fields:

| Field | Purpose |
|---|---|
| `trial_version` | Identifies the Alpha Preview version (`task-016-alpha-preview-v0.1`) |
| `case_id` | Stable per-case identifier (e.g. `case_001_catalog_success`) |
| `case_type` | One of `success` / `blocker` |
| `intent` | Human-readable description of what this fixture is intended to demonstrate |
| `expected_status` | Expected future runner output status (`pass` / `blocked`) |
| `notes` | Human-readable notes explaining what is and is not covered by this skeleton |
| `fixture_input` | The actual input payload for the future runner (catalog JSON for `load_geometry_catalog`) |

## What is intentionally absent

These fixture skeletons **do not** contain:

- Expected golden output JSON (reserved for a later slice under `expected/`).
- Reference to any executable runner or script.
- Test code.
- CI shard-manifest entries.
- Any TASK-017+ semantics (material grade, mass, mechanical suitability,
  cost, pressure-drop, fouling, vendor availability, procurement, etc.).

## Intended future use

When a later explicitly-authorized slice implements the runner
(`TASK-016-TRIAL-004`), each `.input.json` file in this directory will be
loaded by the runner, fed to `load_geometry_catalog()` from
`hexagent.geometry_catalogs`, and the runner will compare the resulting
catalog success/blocker outcome against the `expected_status` and (for
blocker fixtures) the intended blocker category listed above.

Until that slice is separately authorized by Charles, these fixture skeletons
are documentation only — they MUST NOT be loaded, parsed, or executed by any
runtime code in the repository.

## Slice marker

Each fixture carries a `_slice` annotation set to `TASK-016-TRIAL-001` so
future slices can clearly attribute which fixture was introduced in which
authorization window.