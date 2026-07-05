# TASK-017 — Materials, Mass and Preliminary Mechanical Checks Implementation Kickoff

> Implementation planning document for TASK-017. This document is
> PLANNING-ONLY: no production code under `src/`, no test
> implementation under `tests/`, no `.github/` mutations. Each
> implementation slice must be separately authorized by Charles.

## 1. Authority and status

| Field | Value |
|---|---|
| Authorizing issue | #74 |
| Backlog item | TASK-017 (impl) — Add materials, mass and preliminary mechanical checks — implementation |
| Design contract | `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md` |
| Design contract status | **DESIGN FROZEN** (see design doc §19.4) |
| **Frozen Contract Authority Commit SHA** | **`6ed5b7dc7d8df163796eacb838afcf5702a4c53a`** (design contract content SHA at freeze) |
| **Frozen Contract Authority Base SHA** | **`fbb05ae71f21e6cfd4d1041afb5958c863166248`** (PR #71 merge, stable) |
| Design reviewed Head at freeze | `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` |
| Design freeze commit | `95bbdbe94c31fcfea0c07fd47e51bf982c4b49c2` |
| Design PR | #73 (merged `2026-07-05T18:19:27Z`, merge commit `757e748dcef825b13397473977b181913c0cbfa8`) |
| Design Issue | #72 (closed / completed / `2026-07-05T18:36:26Z`) |
| Current main HEAD | `757e748dcef825b13397473977b181913c0cbfa8` |
| Implementation branch | `codex/task-017-materials-mass-mechanical-implementation` |
| Implementation branch base | `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge) |
| Implementation status | **NOW AUTHORIZED FOR KICKOFF ONLY** (planning + slice plan, no core production logic) |

## 2. Implementation scope

The TASK-017 implementation layer consumes the frozen TASK-013
material governance records and the frozen TASK-016 approved
geometry catalog to produce:

1. **MaterialSelector** — read-only consumer of TASK-013
   `property_values[]`. Returns `MaterialResolutionResult` per
   `component_role`.
2. **MassCalculator** — deterministic mass totals broken down by
   `component_role` (inner_tube / outer_pipe / hairpin_bend /
   fittings), each with its own `MaterialResolutionResult`.
3. **PreliminaryMechanicalChecker** — bounded screening checks
   (allowable stress, minimum wall, straight-pipe span) for
   pressure-bearing metal components (`inner_tube` / `outer_pipe`),
   with `BLOCKED_FOR_DETAILED_DESIGN` boundary for any input
   outside the preliminary envelope.

## 3. Slice plan (inherited from design §14)

The TASK-017 implementation is recommended to be split into 5
slices (per design §14), each requiring separate authorization:

| Slice | Scope | File boundary | Dependencies |
|---|---|---|---|
| **A** | MaterialSelector + read-only TASK-013 consumer | `src/hexagent/material_mass_mechanical/material_selector.py` + tests | TASK-013 (read-only) |
| **B** | MassCalculator + MassBreakdown (consumes Slice A) | `src/hexagent/material_mass_mechanical/mass_calculator.py` + tests | Slice A, TASK-016 (read-only) |
| **C** | PreliminaryMechanicalChecker with allowable-stress check only | `src/hexagent/material_mass_mechanical/preliminary_checker.py` + tests | Slice A |
| **D** | PreliminaryMechanicalChecker extended with minimum-wall and straight-pipe-span checks | `src/hexagent/material_mass_mechanical/preliminary_checker.py` extension + tests | Slices A + B + C |
| **Closeout** | Merge implementation PR, refresh Issue #74 body with merge evidence, close Issue #74 | docs-only mutations | Slices A + B + C + D |

Each slice requires:
- Separate authorization Issue (or explicit re-authorization on #74).
- Single PR with files limited to §13 Future implementation file
  boundary (i.e. only the new subtree).
- CI green (lint / typecheck / unit-tests / regression-tests).
- Tracked working tree clean.

## 4. Allowed file boundary

Per design contract §13 (with §13.1 naming rationale):

| Path | Allowed for implementation |
|---|---|
| `src/hexagent/material_mass_mechanical/` (new subtree) | YES — implementation only |
| `src/hexagent/material_mass_mechanical/__init__.py` | YES — package marker |
| `src/hexagent/material_mass_mechanical/material_selector.py` | YES (Slice A) |
| `src/hexagent/material_mass_mechanical/mass_calculator.py` | YES (Slice B) |
| `src/hexagent/material_mass_mechanical/preliminary_checker.py` | YES (Slices C + D) |
| `tests/material_mass_mechanical/` | YES — test files only |
| `docs/tasks/TASK-017-*.md` (planning docs, this file) | YES — docs only |
| `docs/TASK_BACKLOG.md` (evidence rows) | YES — docs only |

## 5. Forbidden scope

Per design contract §3.2:

- **No** `MaterialSelector`, `MassCalculator`, or
  `PreliminaryMechanicalChecker` production logic in this planning
  commit (logic lives in Slices A / B / C / D).
- **No** mutation of `src/hexagent/` outside
  `material_mass_mechanical/` subtree.
- **No** mutation of `tests/` outside `material_mass_mechanical/`
  subtree.
- **No** mutation of `docs/tasks/TASK-011-*.md` …
  `docs/tasks/TASK-016-*.md`.
- **No** mutation of `ci-shard-manifest.yml`.
- **No** mutation of `.github/`.
- **No** mutation of TASK-011 / TASK-012 / TASK-013 / TASK-014 /
  TASK-015 / TASK-015A / TASK-016 frozen contracts or
  implementation.
- **No** pressure-drop / C4 / cost / new-solver / production-solver
  modification.
- **No** detailed mechanical design (FEA, fatigue, creep, seismic,
  wind, weld, NDE).
- **No** two-phase / refrigerants / shell-and-tube / plate / air
  cooler / microchannel content (TASK-020+).
- **No** secret registration / OIDC / registry push / external
  service integration.
- **No** TASK-018+ work.
- **No** closing the authorizing Issue (#74) until closeout slice.
- **No** marking this PR Ready for review until core implementation
  slices are merged.

## 6. Test plan (per design §11)

When Slices A/B/C/D execute, they MUST include:

1. **Unit tests** for every §6 mass formula and every §9
   mechanical check, covering PASS / MARGINAL / BLOCKED
   transitions.
2. **Boundary tests** at the envelope thresholds
   (`hoop_stress = 0.6 * allowable`, `1.5 mm` wall, `L / 360`
   deflection).
3. **Blocker tests** for every error code in design §7 (10 codes
   after freeze + 3 new codes = 13 codes).
4. **Determinism tests**: identical inputs across two
   invocations must produce byte-identical JSON and identical
   SHA-256 hashes, across Python 3.10, 3.11, 3.12.
5. **Frozen-task tests**: the implementation MUST NOT modify any
   frozen TASK-011/012/013/014/015/016 contract artifact
   (verifiable via `git diff --name-only <base>..<impl-head>`
   returning only `src/hexagent/material_mass_mechanical/` and
   `tests/material_mass_mechanical/`).
6. **No-pressure-drop test**: a guard test asserts that no
   pressure-drop correlation id appears anywhere in the TASK-017
   code path.
7. **No-cost test**: a guard test asserts that no currency code,
   CAPEX / OPEX / life-cycle symbol appears anywhere in the
   TASK-017 code path.

## 7. CI ownership plan (per design §12)

Each implementation slice PR must be observed against all of:

- `lint` job: `uv run --locked ruff check .`
- `typecheck` job: `uv run --locked mypy src/ tests/`
- `unit-tests` job:
  `uv run --locked pytest tests/material_mass_mechanical -q`
- `regression-tests` job: full suite, no regression vs. base.
- `ci-shard-manifest` job: confirms `ci-shard-manifest.yml` was
  not modified by the implementation PR.

The implementation PR is **NOT** authorized to modify
`ci-shard-manifest.yml` or `.github/`.

## 8. JSON / hash / ordering rules (per design §10)

The implementation MUST adhere to the design §10 rules:

1. Every `MassBreakdown` and `MechanicalCheckReport` is
   serializable to JSON via a documented `MechanicalSchema`.
2. JSON keys are sorted lexicographically before hashing.
3. Floating-point values are formatted with a documented
   `Decimal` quantizer: 6 decimal places for kg, 4 decimal
   places for m / mm / MPa / °C, 9 decimal places for GPa.
4. The result hash is the lowercase hex SHA-256 of the UTF-8
   encoded canonical JSON.
5. Provenance fields are included in the hashed JSON.
6. Optional fields are either present with `null` or absent per
   the documented schema.

## 9. Error codes (per design §7, frozen at 13 codes)

| Code | Used for |
|---|---|
| `MATERIAL_GOVERNANCE_INCOMPLETE` | TASK-013 property_name missing / unit mismatch |
| `MATERIAL_GOVERNANCE_UNAPPROVED` | TASK-013 approval_state != "approved" |
| `MATERIAL_RESOLUTION_MISSING_ROLE` | `material_resolutions_by_component_role` missing role |
| `GEOMETRY_CATALOG_UNAPPROVED` | TASK-016 geometry not approved |
| `GEOMETRY_CATALOG_INCONSISTENT` | TASK-016 dimension inconsistency |
| `HAIRPIN_BEND_INPUT_INCOMPLETE` | hairpin fields missing |
| `ALLOWABLE_STRESS_EXCEEDED` | mechanical: hoop_stress > 0.8 * allowable |
| `MINIMUM_WALL_VIOLATED` | mechanical: effective_wall below threshold |
| `UNSUPPORTED_SPAN_EXCEEDED` | mechanical: span exceeded |
| `BLOCKED_FOR_DETAILED_DESIGN` | mechanical: outside envelope |
| `MECHANICAL_CHECK_UNSUPPORTED_ROLE` | mechanical: hairpin_bend/fittings role |
| `INPUT_DIMENSIONAL_INCONSISTENT` | input: negative dimension |
| `INPUT_UNIT_INCONSISTENT` | input: non-SI unit |

All 13 codes are stable, mutually exclusive (where applicable),
and testable.

## 10. Slice authorization template (for future rounds)

Each future slice round should follow this template:

```
Authorization:
- Slice: <A/B/C/D/Closeout>
- Branch: codex/task-017-materials-mass-mechanical-implementation
- PR base: <main SHA at slice time>
- Files allowed: src/hexagent/material_mass_mechanical/<slice>.py + tests/material_mass_mechanical/<slice>_test.py
- Files NOT allowed: src/ outside subtree, tests/ outside subtree, .github/, ci-shard-manifest.yml, frozen contracts

Forbidden mutations:
- No pressure-drop / C4 / cost / new-solver / production-solver-mutation
- No TASK-018+
- No close Issue #74 (until closeout slice)
- No Ready / merge until CI green
```

## 11. Self-reference guard

The Frozen Contract Authority Commit SHA
(`6ed5b7dc7d8df163796eacb838afcf5702a4c53a`) is a literal in
this document. Any future implementation slice commit MUST NOT
modify this document's §1 SHA row unless rotating the design
contract itself (which requires a new TASK-017 design amendment).

The implementation branch base = `757e748dcef825b13397473977b181913c0cbfa8`
(= PR #73 merge commit) MUST be recorded in every implementation
slice PR body and `docs/TASK_BACKLOG.md` evidence row.

## 12. Three-way SHA synchronization

For each implementation slice, the Frozen Contract Authority
Commit SHA MUST be recorded in three places:

1. Design contract body §19.1 (immutable once frozen).
2. Implementation slice PR body — "Frozen Design Authority SHA"
   section.
3. `docs/TASK_BACKLOG.md` evidence row.

Plus the implementation slice SHA itself recorded at:

4. Slice PR body — "Slice reviewed Head" section.
5. Slice merge commit (after merge).
6. `docs/TASK_BACKLOG.md` evidence row.

Any divergence between locations is an audit-trail defect.

## 13. Acceptance criteria for THIS kickoff document

This kickoff document is acceptable to Charles only if:

1. All 13 sections above are present and concrete.
2. The Frozen Contract Authority Commit SHA literal
   (`6ed5b7dc…`) matches the design contract §19.1.
3. The implementation branch base SHA (`757e748d…`) matches
   `origin/main` HEAD.
4. The slice plan (A/B/C/D/Closeout) is small enough that each
   slice is reviewable in one round.
5. The allowed file boundary (§4) is consistent with design §13.
6. The forbidden scope (§5) is consistent with design §3.2.
7. No production code is included in this kickoff commit.

## 14. Closeout criteria

When the final implementation slice (D + Closeout) is merged:

1. Implementation closeout docs PR records the merge SHA in three
   places (Issue #74 body, implementation PR body, `docs/TASK_BACKLOG.md`
   evidence row).
2. Issue #74 closeout comment records the final implementation
   SHA and post-merge CI evidence.
3. Issue #74 is closed with `state_reason=completed`.
4. `docs/TASK_BACKLOG.md` TASK-017 (impl) row is updated from
   "NOT AUTHORIZED" → "DONE / MERGED / MAIN-CI-VERIFIED / CLOSED".
5. TASK-017 implementation status: DONE / MERGED / MAIN-CI-VERIFIED
   / CLOSED.

## 15. Self-reference guard verification

| SHA | Value |
|---|---|
| Frozen Contract Authority Commit SHA (this doc §1) | `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` |
| Implementation branch base (= origin/main = PR #73 merge) | `757e748dcef825b13397473977b181913c0cbfa8` |
| Implementation kickoff commit (this round's commit, NOT YET EXISTED) | (will be different from above) |
| Self-reference? | No (kickoff commit will be a new commit on top of `757e748d…`) |

## 16. Document revision history

| Revision | Author | Date | Notes |
|---|---|---|---|
| Rev 1 (kickoff) | Charles via TASK-017 implementation kickoff | 2026-07-05 | Initial planning document. 16 sections covering authority, scope, slice plan, file boundary, forbidden scope, test plan, CI ownership, JSON/hash rules, error codes, slice authorization template, self-reference guard, three-way SHA sync, acceptance criteria, closeout criteria. |