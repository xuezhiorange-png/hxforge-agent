# TASK-016 Alpha Preview v0.1

> Internal-only trial package for the completed TASK-016 approved tube, pipe,
> and hairpin geometry catalog. This directory contains documentation and
> fixture skeletons only. The runner, golden outputs, and test coverage are
> intentionally NOT implemented in this slice.

## Scope of this slice (TASK-016-TRIAL-001)

This slice (`TASK-016-TRIAL-001`) creates only:

1. This `README.md` (package overview).
2. A `fixtures/README.md` describing the 5 fixture skeletons.
3. Five fixture skeleton `.input.json` files (deterministic, human-readable).
4. An `expected/README.md` explaining that golden outputs are intentionally
   absent and reserved for a later explicitly-authorized slice.

## What is intentionally NOT in this slice

The following are **explicitly deferred** to later, separately-authorized
slices:

- Executable runner (`scripts/run_task016_alpha_preview_v0_1_case.py` or
  equivalent) — NOT implemented.
- Golden output JSON files under `expected/` — NOT implemented.
- Test coverage that proves fixture determinism — NOT implemented.
- CI shard-manifest ownership for any new test files — NOT modified.
- Any runtime assertion code — NOT implemented.

The `expected/` directory is created as an empty placeholder with a README that
explains the deferral. No `.golden.json` files exist in this slice.

## Governance reminders

- **Audience**: internal engineering reviewers and maintainers only.
- **Maturity**: alpha / internal preview.
- **Guarantee level**: deterministic examples only, not production suitability.
- **TASK-017+ remains blocked**: no material grade, mass, mechanical
  suitability, cost, pressure-drop, fouling, vendor availability, procurement
  status, public-API, report-rendering, DB/ORM/Alembic, deployment, UI, or
  TASK-017+ semantics are permitted in this slice or any later slice.
- **TASK-015A is not mutated.**
- **Frozen TASK-011 / TASK-012 / TASK-013 / TASK-014 / TASK-015 contract bodies
  are not mutated.**
- **Use of these fixtures requires later explicit Charles authorization.**
  No runner, test, golden output, or downstream consumer may read these
  fixtures until Charles has separately authorized the corresponding slice
  (per TASK-016-TRIAL-001 through TASK-016-TRIAL-006 in the design document).

## Authority baseline

- TASK-016 Alpha Preview v0.1 design PR: #68 (merged)
- Design merge commit: `984eee5de49a3805182b54841463ebbba91fca88`
- Design file: `docs/trials/TASK-016-alpha-preview-v0.1.md`
- TASK-016 design FCAS: `654a2708de808c9f1518f1a69eda92f95a4d37c5`
- TASK-016 implementation PR: #67 (merged)
- TASK-016 implementation merge commit: `ac7a4152698f039b4d6795f6a814228cb3c43def`
- TASK-016 implementation Issue: #66 (closed / completed)
- TASK-016-TRIAL dedicated Issue: #70

## Slice marker

This directory's contents are tagged with the slice identifier
`TASK-016-TRIAL-001` so future slices can clearly distinguish which
fixtures / docs were introduced in which authorization window.