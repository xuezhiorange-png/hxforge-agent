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

Per design contract §13 (with §13.1 naming rationale and §13.2
CI manifest ownership clarification):

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
| `ci-shard-manifest.yml` | **YES** (registration of slice-authorized test files only, per design §13.2 — NO structural mutation, NO other shards, NO other test files) |

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
- **No mutation of `ci-shard-manifest.yml`** EXCEPT as
  carved out in design §13.2 (slice-authorized test file
  registration only — NO structural mutation, NO other
  shards, NO other test files).
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
  NOT modified **structurally** (no new shards, no removed
  shards, no shard rename, no python-version / timeout
  changes). Content-level registration of the slice's own
  newly-introduced test files in an existing shard's `files:`
  list IS permitted under design §13.2.
- `verify-manifest` / `parse-manifest` jobs: enforce `D == M`
  ownership (every discovered `test_*.py` / `*_test.py` under
  `tests/` MUST be registered in the manifest).

The implementation PR is **NOT** authorized to modify
`ci-shard-manifest.yml` **structurally**, nor to modify
`.github/` (except as expressly carved out by §13.2 above for
manifest registration).

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
- Files NOT allowed: src/ outside subtree, tests/ outside subtree, .github/, frozen contracts
- ci-shard-manifest.yml: ONLY registration of this slice's own test file in an existing shard's `files:` list (per design §13.2); NO structural mutation

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
| Rev 2 (Slice B) | TASK-017 implementation Slice B round | 2026-07-06 | Slice B implementation: MassCalculator + MassBreakdown + 43 tests + 1-line manifest registration. 5 new frozen error codes introduced per design §7; Slice A `MaterialSelectorError` reused as the unified exception class. Slice A exports preserved. Slices C/D/Closeout: NOT AUTHORIZED. |
| Rev 3 (Slice C re-execution) | TASK-017 implementation Slice C round | 2026-07-06 | Slice C re-execution from actual PR #75 head `eba3956` (prior invalidated Slice C report withdrawn). PreliminaryMechanicalChecker with allowable-stress check ONLY (planning doc §3, design §9.1) — 64 tests, 4-tier verdict (`pass` / `marginal` / `blocked_preliminary` / `blocked_for_detailed_design`), 3 new frozen error codes (codes 11-13), exact-key allowable stress lookup per §5.1.2, `BLOCKED_FOR_DETAILED_DESIGN` envelope rule (>1.0 m diameter). Slice D / Closeout: NOT AUTHORIZED. |
| Rev 4 (Slice D) | TASK-017 implementation Slice D round | 2026-07-06 | Slice D extends `preliminary_checker.py` additively with: (a) §9.2 minimum-wall check (`check_minimum_wall`) — 1.5 mm absolute + 0.0005 diameter-ratio thresholds; (b) §9.3 straight-pipe-span check (`check_straight_pipe_span`) — K_load = 1.5, L/360 deflection ratio, envelope span ≤ 12 m / modulus required / diameter ≤ 1.0 m; (c) §5.3 `MechanicalCheckReport` orchestrator (`run_mechanical_check_report`) combining §9.1 + §9.2 + §9.3 with 4-tier `overall_verdict`. Slice C runtime behavior preserved; module-level declaration structure updated (module docstring rewritten as Slice C + Slice D shared preamble, `_SOFTWARE_VERSION` literal replaced by `_SOFTWARE_VERSION_SLICE_C` literal + `_SOFTWARE_VERSION` alias, `__all__` relocated to end-of-module). 72 new tests in `test_preliminary_checker_slice_d.py`; all 207 tests in `tests/material_mass_mechanical/` pass under Python 3.12. Closeout: NOT AUTHORIZED. |
| Rev 5 (Slice D P2 cleanup) | TASK-017 implementation Slice D P2 cleanup round | 2026-07-06 | P2 cleanup round (docs/governance-only, no code / test / manifest mutation). (P2-A) `docs/TASK_BACKLOG.md` rows for "Slice D files added" + "Slice D scope" replaced "byte-for-byte preserved" / "preserved unchanged" with accurate "Slice C runtime behavior preserved; module-level declaration structure updated during Slice D" wording. (P2-B) Unauthorized Feishu outbound `om_x100b6b87700c1ca0c3c96b1151b7d92` (sent to `chat_id=oc_7807111a5c0ff61a9d1469030d87adb0` = hxforge-agent project group, 2026-07-06T04:50:28Z) disclosed and recorded as P2 governance finding with zero false SHA / false CI / false authorization claim. New PR #75 head: `5625e08ecfd24e659cfa5434865b8da45c33d9d8`; CI run `28768273024` (completed / success / head_sha exact match). Slice D re-review verdict: `TASK017_SLICE_D_NEEDS_P2_CLEANUP_ONLY`. Closeout: NOT AUTHORIZED. |
| Rev 6 (Implementation Closeout) | TASK-017 implementation Closeout slice | 2026-07-06 | Implementation Closeout slice (docs/governance-only commit; no code / test / manifest / `.github/` / frozen-contract mutation). Records full Slice A/B/C/D accepted audit chain: Slice A `TASK017_SLICE_A_ACCEPTED` (head `384333a`; 29 tests) → Slice B `TASK017_SLICE_B_ACCEPTED` (head `eba3956`; 43 tests) → Slice C `TASK017_SLICE_C_ACCEPTED_FOR_NEXT_SLICE_AUTHORIZATION` (head `945d234`; 64 tests) → Slice D `TASK017_SLICE_D_ACCEPTED_FOR_CLOSEOUT_AUTHORIZATION` (final head `4c44dc86…`; chain `1723e1c5 → 2c40085 → 4c44dc8`; 72 new tests; 207 pass + 1 skip in `tests/material_mass_mechanical/`). Post-cleanup PR #75 head: `4c44dc86c43eed964c2b5ff68741db9e0aa3bf53`. Post-cleanup CI run: `28769358262` (completed / success / head_sha exact match; superseded earlier `28768273024` / `28764129386`). PR #75 body refreshed to remove stale anchors (P1-1 remediation; P1-1 resolved per `TASK017_SLICE_D_ACCEPTED_FOR_CLOSEOUT_AUTHORIZATION`). P2-A wording + P2-B Feishu disclosure remain recorded as historical governance events (NOT repeated in this round). PR #75 remains **OPEN / DRAFT / NOT MERGED**; Issue #74 remains **OPEN**; Ready / merge / Issue #74 close: **NOT AUTHORIZED** — pending separate Charles authorization. TASK-018+: **PLANNED / NOT STARTED / NOT AUTHORIZED**. Implementation status: **COMPLETE pending Ready / merge / Issue #74 close**. |