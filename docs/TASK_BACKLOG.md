# HXForge Task Backlog

This is the project-level work breakdown. Detailed executable cards for the first implementation sequence are in `docs/tasks/`.

Status values: `DONE`, `IN_PROGRESS`, `READY_FOR_REVIEW`, `READY`, `BLOCKED`, `PLANNED`, `DRAFT`.

- `READY_FOR_REVIEW` = implementation complete, engineering review passed, awaiting PR merge
- `READY` = approved dependency/task ready to start

## M0 — Repository and engineering baseline

| ID | Task | Status | Depends on |
|---|---|---|---|
| TASK-000 | Repository, CI and engineering scaffold | DONE | — |
| TASK-001 | Freeze v0.1 scope, terminology and engineering assumptions | DONE | TASK-000 |

## M1 — Deterministic calculation foundation

| ID | Task | Status | Depends on |
|---|---|---|---|
| TASK-002 | Implement unit-safe quantity model and SI semantics | DONE | TASK-001 |
| TASK-003 | Implement fluid-property contract and CoolProp provider | DONE | TASK-001, TASK-002 |
| TASK-004 | Implement immutable design-case revisions, calculation provenance and structured errors | DONE | TASK-001 |
| TASK-005 | Implement correlation registry and applicability engine | DONE | TASK-001 |
| TASK-006 | Implement heat-balance and specification closure | DONE | TASK-002, TASK-003, TASK-005 |
| TASK-011 (design) | Freeze benchmark-case governance contract | DONE | TASK-001 |
| TASK-011 (impl) | Collect, normalize, review and approve the first 20 benchmark cases | DONE | TASK-011 design |
| TASK-012 (design) | Define standards rule-pack and license boundary | DONE | TASK-001 |
| TASK-012 (impl) | Implement standards rule-pack runtime, license validator and CI boundary | DONE | TASK-012 design |
| TASK-013 (design) | Define material and cost data governance | DONE | TASK-001 |
| TASK-013 (impl) | Implement material and cost data governance | DONE | TASK-013 design |
| TASK-014 (design) | Define immutable case revisions and persistence contract | DONE | TASK-002, TASK-003, TASK-004, TASK-005, TASK-011, TASK-012, TASK-013 |
| TASK-014 (impl) | Implement immutable case revisions and persistence | DONE | TASK-014 design |
| TASK-015 (design) | Design CI, security and release automation hardening contract | DONE / DESIGN FROZEN | TASK-000 |
| TASK-015 (impl first slice) | Implement CI, security and release automation hardening (first slice) | DONE / MERGED / MAIN-CI-VERIFIED / CLOSED | TASK-015 design |
| TASK-015 (follow-up) | Follow-up implementation slice for CI/security/release automation hardening | FOLLOW-UP IN PROGRESS | TASK-015 impl first slice |

## M2 — Double-pipe vertical slice

| ID | Task | Status | Depends on |
|---|---|---|---|
| TASK-007 | Implement single-phase tube and annulus correlations | DONE | TASK-003, TASK-004, TASK-006 |
| TASK-008 | Implement fixed-geometry double-pipe rating | DONE | TASK-005, TASK-006, TASK-007 |
| TASK-009 (Phase 1-2) | Implement manufacturable sizing and candidate optimization (catalog, gate, materialization, evaluation, identity, zero-TI rating adapter) | DONE | TASK-008 |
| TASK-009 (Phase 3 design) | Deterministic feasibility, ranking and Top-N contract | DONE | TASK-009 Phase 2 |
| TASK-009 (Phase 3 impl) | Deterministic feasibility, ranking and Top-N implementation | DONE | TASK-009 Phase 3 design |
| TASK-009 (Issue #26) | Fix inherited heat-balance golden and rating test failures | DONE | TASK-009 Phase 3 |
| TASK-010 (design) | Freeze versioned API and traceable report contract | DONE | TASK-009 |
| TASK-010 (impl) | Implement versioned API and traceable report | DONE | TASK-010 design |
| TASK-015A | Deterministic test environment and CI sharding | DONE | TASK-010 |
| TASK-016 | Add approved tube, pipe and hairpin geometry catalog | PLANNED | TASK-001 |
| TASK-017 (design) | Add materials, mass and preliminary mechanical checks — design contract | **DESIGN FROZEN** / IMPLEMENTATION NOT AUTHORIZED | TASK-012 (impl), TASK-013, TASK-016 |
| TASK-017 (impl) | Add materials, mass and preliminary mechanical checks — implementation | **TASK-017 IMPLEMENTATION CLOSEOUT READY FOR REVIEW** (MaterialSelector + MassCalculator + PreliminaryMechanicalChecker §9.1 + §9.2 + §9.3 + §5.3 orchestrator + tests; PR #75 remains DRAFT; Ready / merge / Issue #74 close: NOT AUTHORIZED — pending separate Charles authorization) | TASK-017 design |
| TASK-018 | Add C0/C1 cost model and life-cycle energy estimate | **IMPLEMENTATION SLICES A/B/C MERGED / CLOSED OUT**; closeout governance-sync docs PR opened as documentation-only (Issue #85) | TASK-009, TASK-013, TASK-017 |
| TASK-019 | Add Golden cases and double-pipe validation report | PLANNED | TASK-007–TASK-018 |

## M3 — Shell-and-tube single phase

TASK-020 through TASK-039 cover TEMA configuration schemas, tube layout, shell diameter, tube-side rating, Kern screening, Bell–Delaware, pressure-drop decomposition, thermal expansion screening, preliminary mechanical boundaries, materials, costing, optimization, API, report and Golden validation.

## M4 — Plate heat exchangers

TASK-040 through TASK-059 cover gasketed, brazed and semi-welded types; licensed plate catalogs; channel geometry; heat transfer; channel, port and distribution pressure drop; gasket/material compatibility; CIP risk; costing; optimization; API, report and validation.

## M5 — Air coolers

TASK-060 through TASK-079 cover forced/induced draft configurations, dry/wet air properties, finned-tube heat transfer, fin efficiency, air-side pressure drop, fan/system curves, altitude and recirculation corrections, noise and freeze screening, structure, costing, optimization, API, report and validation.

## M6 — Two-phase and refrigerants

TASK-080 through TASK-099 cover phase-region segmentation, pure-fluid and mixture saturation behavior, condensation, evaporation, two-phase pressure drop, acceleration pressure drop, dryout/flooding checks, charge estimation, glide, uncertainty and validation.

## M7 — Microchannel

TASK-100 through TASK-119 cover multiport tubes, louver fins, headers, circuiting, refrigerant distribution, charge, maldistribution risk, frost/drainage interfaces, corrosion and brazing constraints, optimization, API, report and validation.

## M8 — Simulation and CAD

TASK-120 through TASK-139 cover distributed 1D models, solver convergence, OpenFOAM case generation, meshing and grid-independence plans, CFD post-processing, CalculiX/Code_Aster adapters, parametric CAD, STEP/DXF exports and simulation provenance.

## M9 — Enterprise platform

TASK-140 through TASK-159 cover organizations, roles, review/approval workflow, private rule packs, vendor catalogs, cost bases, historical-project calibration, object storage, worker isolation, backups, observability, deployment and disaster recovery.

## Next execution sequence

1. Complete project-governance closeout for TASK-000 through TASK-010.
2. Design and approve TASK-015A deterministic test environment and CI sharding.
3. Implement and merge TASK-015A without changing frozen TASK-010 behavior.
4. TASK-011 benchmark-case governance design is merged and frozen by PR #37.
5. TASK-011 implementation is merged and closed out by PR #38 (Issue #36
   CLOSED, main post-merge CI SUCCESS). The TASK-011 closeout docs PR
   records this milestone in the evidence tables below.
6. TASK-012 design contract is merged and frozen by PR #41
   (merge commit `d1e5c316ee1b0b71211e932ff7fbcb5935f77246`,
   reviewed Head `28b6330f8c5221d75f101f6810157d81a428f446`,
   main post-merge CI `28700595841` — SUCCESS). TASK-012
   implementation was merged by PR #44 (reviewed head
   `7b1a6bd4bdc5111b2ead53849b0e96e0e3f5fcf9`, merge commit
   `ea3b898e57aa6abc73b9367552cffae3d24c027d`,
   merged_at `2026-07-04T11:05:02Z`).
7. TASK-012 implementation is merged and closed out by PR #44
   (Issue #43 CLOSED with state_reason=completed at
   `2026-07-04T11:13:03Z`, closeout comment `4881751607`,
   main post-merge CI `28704210885` — SUCCESS).
   The TASK-012 implementation closeout docs PR records this
   milestone in the evidence tables below.
8. TASK-013 design contract has been merged and is now
   DESIGN FROZEN on main:
   - Initial reviewed Head `9b23af758a7cccf6ad0257d6c008ecc266012d32`
     received review comment `4629537005` (CHANGES_REQUESTED).
   - Remediation commit `bc0856da6a4c99a04afb03fca6caf2c4a563f6ac`
     on the same branch addressed P0/P1/P2 items and produced
     final reviewed Head `bc0856da6a4c99a04afb03fca6caf2c4a563f6ac`,
     which received round 2 review `4629604406` (PASS) with
     PR CI run `28706044096` (completed / success).
   - Final-flow preflight review `4629613493` flagged a
     `docs/TASK_BACKLOG.md` evidence-staleness blocker before
     Ready / Merge.
   - Evidence-fix commit `10e7335015289a2b6bf6561e1e5e629cdaeeadf7`
     on the same branch received final-flow evidence-fix review
     `4629635280` (PASS / preflight clear) with PR CI run
     `28706983959` (completed / success).
   - PR #47 was merged at `2026-07-04T13:10:58Z` (merge commit
     `ee7aa092bca854316be961b536c7a121490aa385`); main post-merge
     CI run `28707278871` completed / success.
   - Closeout docs PR (on branch `docs/task-013-design-closeout`)
     records the merge SHA, main post-merge CI, and frozen design
     status in the Merge evidence table.
   TASK-013 implementation has been merged and closed out
   (Issue #49 CLOSED / completed). See item 10 below for the
   implementation evidence; the TASK-013 implementation closeout
   docs PR records this milestone in the evidence tables below.
9. TASK-014 has been merged and closed out. TASK-015 design is now
   IN DRAFT (Issue #57, design PR not yet opened in this snapshot).
   TASK-016, TASK-017, TASK-018, TASK-019, and TASK-020+
   (shell-and-tube / plate / air-cooler / two-phase / refrigerant)
   remain PLANNED / NOT STARTED unless later governance grants
   separate explicit authorization.
10. TASK-013 implementation has been merged and closed out:
    - Implementation Issue #49: CLOSED (state_reason=completed)
    - Implementation PR #50 on branch
      `codex/task-013-material-cost-governance-runtime`
    - PR #50 reviewed Head: `d85f1c70236527a104f3f3ed9231cdf66d896150`
    - PR #50 merge SHA: `917bd3a761824fc8d11dcf187dbd8d6c91bfc942`
    - PR #50 merged_at: `2026-07-04T16:19:19Z`
    - PR #50 PR-head CI: `28710499786` — SUCCESS
    - PR #50 Main Post-Merge CI: `28712202985` — SUCCESS
    - Frozen Contract Authority SHA:
      `ee7aa092bca854316be961b536c7a121490aa385` (PR #47 design
      merge)
    - Final closeout comment id: `4883048106`
    - Issue #49 closed_at: `2026-07-04T16:26:04Z`
    - The implementation created only the files allowed by the
      TASK-013 design contract Section 19 envelope
      (`src/hexagent/material_costs/`, `tests/material_costs/`) and
      did NOT modify any frozen TASK-011 / TASK-012 / TASK-013
      contract body, any workflow, any benchmark artifact, or any
      runtime persistence / API / DB artifact.
    - TASK-013 implementation status: DONE / MERGED / MAIN-CI-VERIFIED /
      CLOSED.
    - TASK-014 implementation status: DONE / MERGED / MAIN-CI-VERIFIED /
      CLOSED (see items 11+ for the implementation closeout evidence).
    - TASK-015 design status: AUTHORIZED BY Issue #57 / IN DRAFT PR.
    - TASK-015 implementation: NOT AUTHORIZED.
    - TASK-015A historical: CLOSED / MERGED (unchanged).
    - TASK-016+ remains PLANNED / NOT STARTED unless later
      governance grants separate explicit authorization.

11. TASK-014 implementation has been merged and closed out:
    - Implementation Issue #55: CLOSED (state_reason=completed)
    - Implementation PR #56 on branch
      `codex/task-014-immutable-case-revisions-persistence`
    - PR #56 reviewed Head: `df351f07f86ac9c6c827375ceb5410fce8249607`
    - PR #56 merge SHA: `66e718c90a54f84ab0f9b0bedc34e67a3f5177bc`
    - PR #56 merged_at: `2026-07-05T05:05:08Z`
    - PR #56 PR-head CI: `28729781313` — SUCCESS
    - PR #56 Main Post-Merge CI: `28730227363` — SUCCESS
    - Frozen Contract Authority SHA:
      `6f337a6e81a8c2a7ba8059285aeef39bba59c7cb` (PR #53 design
      merge)
    - Final closeout comment id: `4884933296`
    - Issue #55 closed_at: `2026-07-05T05:14:36Z`
    - The implementation created only the files allowed by the
      TASK-014 design contract Section 17 envelope
      (`src/hexagent/case_revisions/`, `tests/case_revisions/`) and
      did NOT modify any frozen TASK-011 / TASK-012 / TASK-013 /
      TASK-014 contract body, any workflow, any benchmark artifact,
      or any runtime persistence / API / DB artifact.
    - TASK-014 implementation status: DONE / MERGED / MAIN-CI-VERIFIED /
      CLOSED.

12. TASK-015 design is now AUTHORIZED by Issue #57:
    - Design Issue #57: OPEN
    - Design branch: `docs/task-015-ci-security-and-release-automation-design`
    - Design PR: (this PR — DRAFT)
    - Design status: AUTHORIZED BY Issue #57 / IN DRAFT PR
    - Design contract file:
      `docs/tasks/TASK-015-ci-security-and-release-automation.md`
    - TASK-015 implementation: NOT AUTHORIZED
    - TASK-015A historical: CLOSED / MERGED (unchanged; this design
      does not mutate, reopen, or supersede any TASK-015A asset)
    - TASK-016+ : PLANNED / NOT STARTED

## Merge evidence

| Task | PR |
|---|---|
| TASK-000 | #1 |
| TASK-001 | #2 |
| TASK-002 | #5 |
| TASK-003 | #7 |
| TASK-004 | #9 |
| TASK-005 | #11 |
| TASK-006 | #14 |
| TASK-007 | #18 |
| TASK-008 | #21 |
| TASK-009 | #24 |
| TASK-010 design | #29 |
| TASK-010 impl | #31 |
| TASK-015A | #35 |
| TASK-011 design | #37 |
| TASK-011 impl | #38 |
| TASK-012 design | #41 |
| TASK-012 impl | #44 |
| TASK-013 design | #47 |
| TASK-013 impl | #50 |
| TASK-014 design | #53 |
| TASK-014 impl | #56 |

| Item | Value |
|---|---|
| TASK-010 Design PR | #29 |
| TASK-010 Design reviewed Head | `252b9499c681ac98722ff173b854ea023b5ec03a` |
| TASK-010 Design merge SHA | `210bdf4069cfd5e1282e4c9b5cc7da02bb7c5170` |
| TASK-010 Implementation PR | #31 |
| Reviewed Head | `7c6b62931f5c9d12a0259ffd938ba80f757e65e1` |
| Merge SHA | `971df0007aa4b7b979598ba5568f702ab76af56f` |
| Final Review | `4609799752` |
| Final PR CI | `28522537592` |
| Main Post-Merge CI (PR #31) | `28523901677` |
| Main Post-Merge CI (PR #32) | `28526790197` |
| Frozen Contract SHA | `9a1faeb92f4015a62f9d9add0739f3853a876415` |
| Contract Closure | APPROVED |
| TASK-015A PR | #35 |
| TASK-015A Issue | #33 — CLOSED |
| TASK-015A reviewed Head | `393be83fb6282929495ee309759884aedf178bcf` |
| TASK-015A merge SHA | `9b45f96adc5a58c207570c69f7a58c77cfe1d4cc` |
| TASK-015A PR CI | `28678326754` — SUCCESS |
| TASK-015A Nightly | `28678519599` — SUCCESS |
| TASK-015A Main Post-Merge CI | `28689412008` — SUCCESS |
| TASK-011 Design Issue | #36 — CLOSED |
| TASK-011 Design PR | #37 |
| TASK-011 Design reviewed Head | `7cfdb4f0989b6d384533c7a29e9a2156c731bd0f` |
| TASK-011 Design merge SHA | `bee6b57b8004b6c257ec81738430781fe0b7ee19` |
| TASK-011 Design final review | `4628651936` — PASS |
| TASK-011 Design status | DESIGN FROZEN / IMPLEMENTATION NOT AUTHORIZED |
| TASK-011 Impl Issue | #36 — CLOSED |
| TASK-011 Impl PR | #38 |
| TASK-011 Impl reviewed Head | `3d1bc890bc8e11e430e33dcd705ece063cda9891` |
| TASK-011 Impl merge SHA | `860c674c6f1d68bf127435c12f5d23e4395fe0f7` |
| TASK-011 Impl PR CI | `28698159020` — SUCCESS |
| TASK-011 Impl Main Post-Merge CI | `28698630316` — SUCCESS |
| TASK-011 Impl authority comment | `4881002738` / `IC_kwDOTATQrM8AAAABIu4w8g` |
| TASK-011 Impl status | DONE / ISSUE CLOSED |
| TASK-012 Design Issue | #40 — OPEN |
| TASK-012 Design PR | #41 |
| TASK-012 Design branch | `docs/task-012-standards-license-boundary` |
| TASK-012 Design base | `f78716e4cd348e46157a2a610c8fc4191a0c9dd9` (main @ TASK-011 closeout merge) |
| TASK-012 Design reviewed Head | `28b6330f8c5221d75f101f6810157d81a428f446` |
| TASK-012 Design merge SHA | `d1e5c316ee1b0b71211e932ff7fbcb5935f77246` |
| TASK-012 Design merged_at | `2026-07-04T08:30:52Z` |
| TASK-012 Design PR CI | `28700361861` — SUCCESS |
| TASK-012 Design Main Post-Merge CI | `28700595841` — SUCCESS |
| TASK-012 Design freeze comment | `4881316929` |
| TASK-012 Design additional freeze comment | `4881320152` |
| TASK-012 Design frozen contract file | `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` |
| TASK-012 Design status | DONE / DESIGN FROZEN / IMPLEMENTATION NOT AUTHORIZED |
| TASK-012 Impl Issue | #43 — CLOSED (state_reason=completed) |
| TASK-012 Impl PR | #44 |
| TASK-012 Impl branch | `codex/task-012-rule-pack-runtime-license-boundary` |
| TASK-012 Impl base | `b5a2ecdc3cc75afb7086c70ca3bd12ae275b8609` (main @ TASK-012 closeout docs merge) |
| TASK-012 Impl reviewed Head | `7b1a6bd4bdc5111b2ead53849b0e96e0e3f5fcf9` |
| TASK-012 Impl merge SHA | `ea3b898e57aa6abc73b9367552cffae3d24c027d` |
| TASK-012 Impl merged_at | `2026-07-04T11:05:02Z` |
| TASK-012 Impl PR CI | `28703861025` — SUCCESS |
| TASK-012 Impl Main Post-Merge CI | `28704210885` — SUCCESS |
| TASK-012 Impl review comment | `4629345980` (CHANGES REQUESTED) — addressed in PR #44 head |
| TASK-012 Impl Issue closed_at | `2026-07-04T11:13:03Z` |
| TASK-012 Impl closeout comment | `4881751607` |
| TASK-012 Impl frozen contract file | `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` (unchanged) |
| TASK-012 Impl status | DONE / MERGED / VERIFIED / CLOSED |
| TASK-013 Design Issue | #46 — CLOSED (state_reason=completed) |
| TASK-013 Design PR | #47 |
| TASK-013 Design branch | `docs/task-013-material-cost-data-governance` |
| TASK-013 Design base | `56e7ec01d54fb938ac1c4c14b318eb34b03e3f86` (main @ TASK-012 implementation closeout merge) |
| TASK-013 Design initial reviewed Head | `9b23af758a7cccf6ad0257d6c008ecc266012d32` |
| TASK-013 Design initial review | `4629537005` — CHANGES_REQUESTED |
| TASK-013 Design remediation Head | `bc0856da6a4c99a04afb03fca6caf2c4a563f6ac` |
| TASK-013 Design final reviewed Head | `bc0856da6a4c99a04afb03fca6caf2c4a563f6ac` |
| TASK-013 Design final review | `4629604406` — PASS |
| TASK-013 Design PR CI | `28706044096` — SUCCESS |
| TASK-013 Design final-flow preflight review | `4629613493` — BLOCKED pending evidence fix |
| TASK-013 Design final-flow evidence-fix review | `4629635280` — PASS / preflight clear |
| TASK-013 Design merge SHA | `ee7aa092bca854316be961b536c7a121490aa385` |
| TASK-013 Design merged_at | `2026-07-04T13:10:58Z` |
| TASK-013 Design main post-merge CI | `28707278871` — SUCCESS |
| TASK-013 Design freeze comment | `4882214342` |
| TASK-013 Design closeout PR | #48 |
| TASK-013 Design closeout merge SHA | `aa19e096c3a662687b1ef8dcc0fe2cb12a3b8b60` |
| TASK-013 Design closeout main post-merge CI | `28707812178` — SUCCESS |
| TASK-013 Design frozen contract file | `docs/tasks/TASK-013-material-cost-data-governance.md` |
| TASK-013 Design status | DONE / DESIGN FROZEN / IMPLEMENTATION AUTHORIZED |
| TASK-013 Impl Issue | #49 — CLOSED (state_reason=completed) |
| TASK-013 Impl PR | #50 |
| TASK-013 Impl branch | `codex/task-013-material-cost-governance-runtime` |
| TASK-013 Impl base | `aa19e096c3a662687b1ef8dcc0fe2cb12a3b8b60` (main @ TASK-013 design closeout merge) |
| TASK-013 Impl reviewed Head | `d85f1c70236527a104f3f3ed9231cdf66d896150` |
| TASK-013 Impl merge SHA | `917bd3a761824fc8d11dcf187dbd8d6c91bfc942` |
| TASK-013 Impl merged_at | `2026-07-04T16:19:19Z` |
| TASK-013 Impl PR-head CI | `28710499786` — SUCCESS |
| TASK-013 Impl Main Post-Merge CI | `28712202985` — SUCCESS |
| TASK-013 Impl closeout comment | `4883048106` |
| TASK-013 Impl Issue closed_at | `2026-07-04T16:26:04Z` |
| TASK-013 Impl frozen contract file | `docs/tasks/TASK-013-material-cost-data-governance.md` (unchanged) |
| TASK-013 Impl status | DONE / MERGED / MAIN-CI-VERIFIED / CLOSED |
| TASK-014 design Issue | #52 — CLOSED (state_reason=completed) |
| TASK-014 design PR | #53 — MERGED |
| TASK-014 design reviewed Head | `807e6afc77a3ae38b6a639b436b177d96ccf0f60` |
| TASK-014 design merge SHA / Frozen Contract Authority SHA | `6f337a6e81a8c2a7ba8059285aeef39bba59c7cb` |
| TASK-014 design merged_at | `2026-07-05T03:05:30Z` |
| TASK-014 design PR-head CI | `28714724247` — completed / success |
| TASK-014 design main post-merge CI | `28727736263` — completed / success |
| TASK-014 design frozen contract file | `docs/tasks/TASK-014-immutable-case-revisions-persistence.md` |
| TASK-014 design status | DONE / DESIGN FROZEN |
| TASK-014 design closeout PR | #54 — MERGED |
| TASK-014 design closeout merge SHA | `4e0a6413004d4c23ae89f45713796631d624d6cb` |
| TASK-014 design closeout merged_at | `2026-07-05T03:24:22Z` |
| TASK-014 design closeout main post-merge CI | `28728146017` — completed / success |
| TASK-014 implementation Issue | #55 — CLOSED (state_reason=completed) |
| TASK-014 implementation PR | #56 — MERGED |
| TASK-014 implementation branch | `codex/task-014-immutable-case-revisions-persistence` |
| TASK-014 implementation reviewed Head | `df351f07f86ac9c6c827375ceb5410fce8249607` |
| TASK-014 implementation merge SHA | `66e718c90a54f84ab0f9b0bedc34e67a3f5177bc` |
| TASK-014 implementation merged_at | `2026-07-05T05:05:08Z` |
| TASK-014 implementation PR-head CI | `28729781313` — completed / success |
| TASK-014 implementation Main Post-Merge CI | `28730227363` — completed / success |
| TASK-014 implementation closeout comment | `4884933296` |
| TASK-014 implementation Issue closed_at | `2026-07-05T05:14:36Z` |
| TASK-014 implementation frozen contract file | `docs/tasks/TASK-014-immutable-case-revisions-persistence.md` (unchanged) |
| TASK-014 implementation status | DONE / MERGED / MAIN-CI-VERIFIED / CLOSED |
| TASK-015 design Issue | #57 — CLOSED (state_reason=completed) |
| TASK-015 design PR | #58 — MERGED |
| TASK-015 design reviewed Head | `13722b591409c38c65c187083154e50d0088f655` |
| TASK-015 design merge SHA / Frozen Contract Authority SHA | `39135e269b014e9c9310ac403a60591393d46b2d` |
| TASK-015 design merged_at | `2026-07-05T05:54:09Z` |
| TASK-015 design PR-head CI | `28730839821` — completed / success |
| TASK-015 design closeout PR | #59 — MERGED |
| TASK-015 design closeout merge SHA | `1f3b5de42c4d51c3261d45ab4899a7be5bbfdaed` |
| TASK-015 design closeout merged_at | `2026-07-05T06:07:08Z` |
| TASK-015 design status | DONE / DESIGN FROZEN |
| TASK-015 implementation Issue | #60 — CLOSED (state_reason=completed) |
| TASK-015 implementation PR | #61 — MERGED |
| TASK-015 implementation branch | `codex/task-015-ci-security-release-automation-implementation` |
| TASK-015 implementation reviewed Head | `63b82e1af6d92940e4b3acd420258faf4ea41e62` |
| TASK-015 implementation merge SHA | `eec63cb9a3e52f481f5278281186c0d99b3e196b` |
| TASK-015 implementation merged_at | `2026-07-05T08:43:29Z` |
| TASK-015 implementation PR-head CI | `28733615928` — completed / success |
| TASK-015 implementation Main Post-Merge CI | `28735155632` — completed / success (local/direct REST; connector `workflow_runs: []` recorded as evidence-source mismatch, NOT failure) |
| TASK-015 implementation closeout comment | `4885427862` |
| TASK-015 implementation Issue closed_at | `2026-07-05T08:45:07Z` |
| TASK-015 implementation frozen contract file | `docs/tasks/TASK-015-ci-security-and-release-automation.md` (unchanged) |
| TASK-015 implementation status | DONE / MERGED / MAIN-CI-VERIFIED / CLOSED |
| TASK-015 follow-up Issue | #62 — OPEN |
| TASK-015 follow-up PR | #63 — OPEN / DRAFT / NOT MERGED |
| TASK-015 follow-up branch | `codex/task-015-followup-slice-ci-security-release-hardening` |
| TASK-015 follow-up base | `eec63cb9a3e52f481f5278281186c0d99b3e196b` (main @ TASK-015 implementation merge) |
| TASK-015 follow-up status | AUTHORIZED BY Issue #62 / DRAFT / NOT READY / NOT MERGED |
| TASK-017 design Issue | #72 — OPEN |
| TASK-017 design branch | `docs/task-017-materials-mass-preliminary-mechanical-design` |
| TASK-017 design base | `fbb05ae71f21e6cfd4d1041afb5958c863166248` (main @ PR #71 merge) |
| TASK-017 design reviewed Head (pre-freeze) | `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` |
| TASK-017 Frozen Contract Authority Commit SHA | `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` |
| TASK-017 Frozen Contract Authority Base SHA | `fbb05ae71f21e6cfd4d1041afb5958c863166248` |
| TASK-017 design PR CI | `28748836440` — completed / success / head_sha `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` exact match |
| TASK-017 design frozen contract file | `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md` |
| TASK-017 design status | **DESIGN FROZEN** / Implementation Issue: #74 OPEN |
| TASK-018 design Issue | #76 — CLOSED (state_reason=completed, closed_at=`2026-07-07T11:59:55Z`) |
| TASK-018 design branch | `docs/task-018-c0-c1-cost-life-cycle-energy-design` (merged via PR #77; PR-head CI `28858333023` completed/success, branch is now fully subsumed into main at `05e4990f1…`) |
| TASK-018 design base | `5f96cf761d470b82faa1a5d164eefd42360c7df9` (main @ PR #75 merge) |
| TASK-018 design reviewed Head (pre-freeze) | `19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8` |
| TASK-018 Frozen Contract Authority Commit SHA | `19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8` |
| TASK-018 Frozen Contract Authority Base SHA | `5f96cf761d470b82faa1a5d164eefd42360c7df9` |
| TASK-018 design PR | #77 — MERGED (merge commit `05e4990f1fb00c10ac94812721b6630d0d61db8a`, merged_at `2026-07-07T11:07:50Z`) |
| TASK-018 design PR-head CI | `28858333023` — completed / success / head_sha `19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8` exact match |
| TASK-018 design post-merge main CI | `28861564333` — completed / success / head_sha `05e4990f1fb00c10ac94812721b6630d0d61db8a` exact match (= merge commit). 30 jobs total = 19 success + 11 push-policy-skipped + 0 failed + 0 cancelled (lint / parse-manifest / verify-manifest / collect-global-main py3.11+3.12 / 13 × shard-main py3.11+3.12 all green) |
| TASK-018 design freeze comment | `4903276112` (sha256 `8601b2dee2dd98f3dd5df78a9bc7949889a62db2bbf6dd2c044526f39c074c7b`, 3430 bytes; posted 2026-07-07T11:29:52Z) |
| TASK-018 design review verdict (Round-1) | `ACCEPTED_FOR_READY_AUTHORIZATION` (0 P0 / 0 P1 / 2 non-blocking P2 wording nits — P2-1 status-narrative staleness in §1; P2-2 incomplete 5-input enumeration in §3.2 — **deferred** to a future design-amendment PR per TASK-018 §19.3 anti-rewrite rule + TASK-017 design-amendment precedent PR #46) |
| TASK-018 design frozen contract file | `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` (636 lines; blob `e4a4d74a2d7acd224326dde42eaeab3da83b499e` on main @ `05e4990f1…`) |
| TASK-018 design status | **DESIGN FROZEN** / Implementation Issue: #83 (Slice C Issue) OPEN |
| TASK-018 implementation Issues | Slice A #79 / Slice B #81 / Slice C #83 — all CLOSED (state_reason=completed) |
| TASK-018 implementation Issue (closeout governance-sync) | #85 — OPEN (documentation-only governance-sync round opened in this branch) |
| TASK-018 implementation branches | Slice A: `codex/task-018-impl-slice-a-cost-model-selector` / Slice B: `codex/task-018-impl-slice-b-cost-calculator` / Slice C: `codex/task-018-impl-slice-c-life-cycle-energy-estimator` (all merged into main); Closeout docs branch: `docs/task-018-implementation-closeout-governance-sync` (this round) |
| TASK-018 implementation bases | Slice A: `19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8` (design frozen commit; design PR-head CI `28858333023` completed/success per `TASK-018 design PR-head CI` row above) → merged to main at `1a9c8121…` via PR #80; Slice B: `a78fac1068c150b80e2bb7f717f1b182e515a38d` (main @ PR #78 / design closeout merge) → merged to main at `8c6487da…` via PR #82; Slice C: `8c6487da5808430571d14424e92e5a478fc6e7e2` (main @ PR #82 / Slice B merge) → merged to main at `ef7ee33f…` via PR #84; Closeout docs base: `ef7ee33f238128219b4ddf0a198afbe1457582b2` (this round) |
| TASK-018 implementation status | Slice A: DONE / MERGED / MAIN-CI-VERIFIED / CLOSED (PR #80 / Issue #79); Slice B: DONE / MERGED / MAIN-CI-VERIFIED / CLOSED (PR #82 / Issue #81); Slice C: DONE / MERGED / MAIN-CI-VERIFIED / CLOSED (PR #84 / Issue #83); Closeout governance-sync docs PR: PENDING (DRAFT — this round) |
| TASK-018+ status (relative to TASK-018) | TASK-019+ PLANNED / NOT STARTED / NOT AUTHORIZED |
| TASK-018 implementation Slice A Issue | #79 — CLOSED (state_reason=completed, closed_at=`2026-07-07T14:06:10Z`, comments=1) |
| TASK-018 implementation Slice A closeout comment | `4904687239` |
| TASK-018 implementation Slice A PR | #80 — MERGED (merge commit `1a9c8121514c4c09ad4d310b503a8138afc5bbf9`, merged_at `2026-07-07T14:00:11Z`) |
| TASK-018 implementation Slice A branch | `codex/task-018-impl-slice-a-cost-model-selector` |
| TASK-018 implementation Slice A reviewed Head | `329105ab7856a65f740c69557f819b838957b62c` (Slice A commit on PR #80 branch; PR-head CI `28870830231` completed/success) |
| TASK-018 implementation Slice A merge SHA | `1a9c8121514c4c09ad4d310b503a8138afc5bbf9` |
| TASK-018 implementation Slice A merged_at | `2026-07-07T14:00:11Z` |
| TASK-018 implementation Slice A PR-head CI | `28870830231` — completed / success / head_sha `329105ab7856a65f740c69557f819b838957b62c` exact match |
| TASK-018 implementation Slice A Main Post-Merge CI | `28872056843` — completed / success / head_sha `1a9c8121514c4c09ad4d310b503a8138afc5bbf9` exact match (= merge commit) |
| TASK-018 implementation Slice A Issue closed_at | `2026-07-07T14:06:10Z` |
| TASK-018 implementation Slice A frozen contract file | `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` (unchanged) |
| TASK-018 implementation Slice A files added | `src/hexagent/costing/{__init__.py,cost_model_selector.py,errors.py}` + `tests/costing/{__init__.py,test_cost_model_selector.py,test_frozen_contract_unchanged.py}` |
| TASK-018 implementation Slice A test count | 32 selector tests + 5 frozen-contract tests (pytest `tests/costing/`) — 32 passed (frozen-contract tests skipped in CI sparse-checkout per preflight round); all green under Python 3.12 |
| TASK-018 Slice A CI manifest registration | 1 line added to existing `ci` shard (per design §13.2) |
| TASK-018 implementation Slice A verdict (audit chain) | `TASK018_SLICE_A_MERGED_CLOSED_OUT` (head `329105a…`; PR #80 merge `1a9c8121…`; main post-merge CI `28872056843` success) |
| TASK-018 implementation Slice B Issue | #81 — CLOSED (state_reason=completed, closed_at=`2026-07-07T16:29:36Z`, comments=1) |
| TASK-018 implementation Slice B closeout comment | `4906045271` |
| TASK-018 implementation Slice B PR | #82 — MERGED (merge commit `8c6487da5808430571d14424e92e5a478fc6e7e2`, merged_at `2026-07-07T16:24:17Z`) |
| TASK-018 implementation Slice B branch | `codex/task-018-impl-slice-b-cost-calculator` |
| TASK-018 implementation Slice B reviewed Head | `364db3406e1fa2802cf564e592518a7e07bbecf0` (Slice B commit on PR #82 branch; PR-head CI `28879718436` completed/success) |
| TASK-018 implementation Slice B merge SHA | `8c6487da5808430571d14424e92e5a478fc6e7e2` |
| TASK-018 implementation Slice B merged_at | `2026-07-07T16:24:17Z` |
| TASK-018 implementation Slice B PR-head CI | `28879718436` — completed / success / head_sha `364db3406e1fa2802cf564e592518a7e07bbecf0` exact match |
| TASK-018 implementation Slice B Main Post-Merge CI | `28881835876` — completed / success / head_sha `8c6487da5808430571d14424e92e5a478fc6e7e2` exact match (= merge commit) |
| TASK-018 implementation Slice B Issue closed_at | `2026-07-07T16:29:36Z` |
| TASK-018 implementation Slice B frozen contract file | `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` (unchanged) |
| TASK-018 implementation Slice B files added | `src/hexagent/costing/{__init__.py,cost_calculator.py}` + `tests/costing/test_cost_calculator.py` |
| TASK-018 implementation Slice B test count | 30 calculator tests (pytest `tests/costing/`); all passing under Python 3.12 |
| TASK-018 Slice B CI manifest registration | 1 line added to existing `ci` shard (per design §13.2; Slice A test entry kept, Slice B entry inserted immediately after) |
| TASK-018 implementation Slice B verdict (audit chain) | `TASK018_SLICE_B_MERGED_CLOSED_OUT` (head `364db34…`; PR #82 merge `8c6487da…`; main post-merge CI `28881835876` success) |
| TASK-018 implementation Slice C Issue | #83 — CLOSED (state_reason=completed, closed_at=`2026-07-07T17:58:05Z`, comments=1) |
| TASK-018 implementation Slice C closeout comment | `4906939341` |
| TASK-018 implementation Slice C PR | #84 — MERGED (merge commit `ef7ee33f238128219b4ddf0a198afbe1457582b2`, merged_at `2026-07-07T17:52:43Z`) |
| TASK-018 implementation Slice C branch | `codex/task-018-impl-slice-c-life-cycle-energy-estimator` |
| TASK-018 implementation Slice C reviewed Head | `20f4f8b8aec28dac437fe4673f8ead16aa9dda1e` (Slice C commit on PR #84 branch; PR-head CI `28885096585` completed/success) |
| TASK-018 implementation Slice C merge SHA | `ef7ee33f238128219b4ddf0a198afbe1457582b2` |
| TASK-018 implementation Slice C merged_at | `2026-07-07T17:52:43Z` |
| TASK-018 implementation Slice C PR-head CI | `28885096585` — completed / success |
| TASK-018 implementation Slice C Main Post-Merge CI | `28887201364` — completed / success / head_sha `ef7ee33f238128219b4ddf0a198afbe1457582b2` exact match (= merge commit) |
| TASK-018 implementation Slice C Issue closed_at | `2026-07-07T17:58:05Z` |
| TASK-018 implementation Slice C frozen contract file | `docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md` (unchanged) |
| TASK-018 implementation Slice C files added | `src/hexagent/costing/{__init__.py,life_cycle_energy_estimator.py}` + `tests/costing/test_life_cycle_energy_estimator.py` |
| TASK-018 implementation Slice C test count | 44 estimator tests (pytest `tests/costing/`); all passing under Python 3.12 |
| TASK-018 Slice C CI manifest registration | 1 line added to existing `ci` shard (per design §13.2; Slice A + Slice B entries kept, Slice C entry inserted immediately after) |
| TASK-018 implementation Slice C verdict (audit chain) | `TASK018_SLICE_C_MERGED_CLOSED_OUT` (head `20f4f8b…`; PR #84 merge `ef7ee33f…`; main post-merge CI `28887201364` success) |
| TASK-018 deferred §5.3 discount formula design-amendment | DEFERRED / NOT AUTHORIZED — per TASK-018 §5.3.2 Rule 2, the frozen contract does not prescribe the discount formula; Slice A / B / C implementations all follow **Option A** (`discounted_total_minor_units = null` + `unspecified_blocker` with `details.reason = "discount_formula_pending_design_amendment"`). A future TASK-018 §5.3 design-amendment PR is required before any real `discounted_total_minor_units` can be computed. NOT in this closeout round. |
| TASK-018 deferred §5.3.2 salvage formula design-amendment | DEFERRED / NOT AUTHORIZED — per TASK-018 §5.3.2 schema, `salvage_minor_units: <int>` is contractually required but no formula is prescribed. Slice A / B / C implementations hard-code `salvage_minor_units = 0` as a contract-compliant `<int>` placeholder (P2 governance nit per Slice C closeout). A future TASK-018 §5.3.2 design-amendment PR is required to prescribe the salvage formula. NOT in this closeout round. |
| TASK-018+ forbidden scopes (explicit not-started) | TASK-019+ — PLANNED / NOT STARTED / NOT AUTHORIZED; Issue #23 — NOT TOUCHED (administratively open, comments=80); Feishu outbound — NOT SENT in any TASK-018 round (Slice A / B / C / closeout all zero Feishu); no TASK-018 Slice D implementation (TASK-018 has no §9.2 / §9.3 implementation counterpart to TASK-017 Slice D — closeout here is documentation-only). |
| TASK-017 implementation Issue | #74 — OPEN |
| TASK-017 implementation branch | `codex/task-017-materials-mass-mechanical-implementation` |
| TASK-017 implementation base | `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge) |
| TASK-017 implementation planning doc | `docs/tasks/TASK-017-materials-mass-mechanical-implementation.md` |
| TASK-017 implementation status | **TASK-017 IMPLEMENTATION CLOSEOUT READY FOR REVIEW** (MaterialSelector + MassCalculator + PreliminaryMechanicalChecker §9.1 + §9.2 + §9.3 + §5.3 orchestrator + tests; PR #75 remains DRAFT; Ready / merge / Issue #74 close: NOT AUTHORIZED — pending separate Charles authorization) |
| TASK-017 implementation Slice A commit | `384333a4742a7de5e77308dda0f10fa9d46df939` (governance-repair commit; supersedes `f6afeda` Slice A format-fix) |
| TASK-017 implementation Slice A files added | `src/hexagent/material_mass_mechanical/{__init__.py,material_selector.py}` + `tests/material_mass_mechanical/{__init__.py,test_material_selector.py}` |
| TASK-017 implementation Slice A test count | 29 tests (pytest `tests/material_mass_mechanical/`); all passing under Python 3.12 |
| TASK-017 Slice A CI manifest registration | 1 line added to existing `ci` shard (per design §13.2 governance repair) |
| TASK-017 implementation Slice B commit | `eba39564336f3f29958f29d5241279298ce9769a` (Slice B format-fix; supersedes `2c242de` Slice B impl) |
| TASK-017 implementation Slice B files added | `src/hexagent/material_mass_mechanical/{__init__.py,mass_calculator.py}` + `tests/material_mass_mechanical/test_mass_calculator.py` |
| TASK-017 implementation Slice B test count | 43 tests (pytest `tests/material_mass_mechanical/`); all passing under Python 3.12 |
| TASK-017 Slice B CI manifest registration | 1 line added to existing `ci` shard (per design §13.2; Slice A test entry kept, Slice B entry inserted immediately after) |
| TASK-017 implementation Slice C commit | `945d234479400be4c65d0e0f757bcbfcf70b22ab` (Slice C re-execution; supersedes `eba3956` Slice B + first Slice C attempt `384333a` Slice A governance-repair commit chain) |
| TASK-017 implementation Slice C files added | `src/hexagent/material_mass_mechanical/{__init__.py,preliminary_checker.py,material_selector.py}` + `tests/material_mass_mechanical/test_preliminary_checker.py` |
| TASK-017 implementation Slice C test count | 64 tests (pytest `tests/material_mass_mechanical/`); all passing under Python 3.12 |
| TASK-017 Slice C CI manifest registration | 1 line added to existing `ci` shard (per design §13.2; Slice A + Slice B entries kept, Slice C entry inserted immediately after) |
| TASK-017 implementation Slice D commit | `5625e08ecfd24e659cfa5434865b8da45c33d9d8` (Slice D final head on PR #75 branch; published linear chain: `1723e1c5 → 2c40085 → 5625e08`; supersedes intermediate `82940c7` locally-amended attempt; no force-push) |
| TASK-017 implementation Slice D files added | `src/hexagent/material_mass_mechanical/{__init__.py,preliminary_checker.py}` (extended additively; Slice C runtime behavior preserved; Slice C module-level declaration structure updated during Slice D — module docstring rewritten as Slice C + Slice D shared preamble, `_SOFTWARE_VERSION` literal replaced by `_SOFTWARE_VERSION_SLICE_C` literal + `_SOFTWARE_VERSION` alias, `__all__` relocated to end-of-module) + `tests/material_mass_mechanical/{test_preliminary_checker.py,test_preliminary_checker_slice_d.py}` |
| TASK-017 implementation Slice D test count | 72 tests in `test_preliminary_checker_slice_d.py` (PASS / BLOCKED_PRELIMINARY / BLOCKED_FOR_DETAILED_DESIGN / input-guard / frozen-dataclass / determinism / §5.3 orchestrator aggregation / Slice C parity tests) + 1 documented skip (ratio-only-violation mathematically unreachable scenario); all 207 tests in `tests/material_mass_mechanical/` passing under Python 3.12 |
| TASK-017 implementation Slice D scope | Design §9.2 minimum-wall check + Design §9.3 straight-pipe-span check + Design §5.3 ``MechanicalCheckReport`` orchestrator (``run_mechanical_check_report``). Slice C's ``preliminary_check`` (§9.1) runtime behavior preserved inside the orchestrator. Slice C code section (above the Slice D header line in ``preliminary_checker.py``) has runtime behavior preserved but module-level declaration structure updated (see files-added row above for exact delta). |
| TASK-017 Slice D CI manifest registration | 1 line added to existing `ci` shard (per design §13.2; Slice A + Slice B + Slice C entries kept, Slice D entry inserted immediately after; no other shards / files modified, no structural mutation) |
| TASK-017 implementation Slice D CI run | `28768273024` — completed / success / head_sha `5625e08ecfd24e659cfa5434865b8da45c33d9d8` exact match (replaces invalidated earlier intermediate runs); job summary reports 45 success + 5 skipped + 0 failed against PR head `5625e08e…` |
| TASK-017 implementation Slice D re-review verdict | `TASK017_SLICE_D_NEEDS_P2_CLEANUP_ONLY` (read-only re-review 2026-07-06; code-acceptance PASS, 2 P2 governance findings: P2-A wording over-statement, P2-B unauthorized Feishu outbound) |
| TASK-017 implementation Slice D P2-A wording cleanup | `docs/TASK_BACKLOG.md` rows for "Slice D files added" + "Slice D scope" replaced "byte-for-byte preserved" / "preserved unchanged" with accurate "Slice C runtime behavior preserved; module-level declaration structure updated during Slice D" wording. Planning doc Rev 5 row added. No code / test / manifest changes. |
| TASK-017 implementation Slice D P2-B unauthorized Feishu outbound | Disclosed in P2 cleanup round. Slice D round sent Feishu `om_x100b6b87700c1ca0c3c96b1151b7d92` to `chat_id=oc_7807111a5c0ff61a9d1469030d87adb0` (hxforge-agent project group) at 2026-07-06T04:50:28Z without explicit per-round Feishu authorization. Content: zero false SHA / false CI / false authorization claim (all references verified against GitHub API). No code / PR / Issue side-effect. Recommended future guard: per-round Feishu outbound requires explicit authorization clause. **Disclosed historical governance event — NOT repeated in Closeout round.** |
| TASK-017 implementation Slice D PR body refresh remediation | Read-only re-review verdict `TASK017_SLICE_D_BLOCKED_BY_P1` (P1-1 stale audit anchor) → PR body refresh round (P1-1 remediation: stale head `5625e08…` → current `4c44dc86…`; stale CI `28768273024` → current `28769358262`; both reframed as superseded / withdrawn historical reference) → read-only re-review verdict `TASK017_SLICE_D_ACCEPTED_FOR_CLOSEOUT_AUTHORIZATION` (P1-1 resolved; no P0 / no P1 remaining; no P2 additions). |
| TASK-017 implementation Closeout commit | `cda181c025a9369e77a4ca38ddc21ccc718df292` (Closeout slice primary commit; appended to PR #75 branch linear chain `5625e08 → 4c44dc8 → cda181c`; no force-push; docs/governance-only). Follow-up TBD-fill commit `d193e4d4d04dd46517396a70a09796ea8f143fdf` + final-state refine commit `4edabadd45745fad48b01bffccbd20df68727cd8` + Closeout-chain-record commit `1215f58139d738df9e54bdbbd1be8d28da96f94b` + final-final-state-record commit `ad263d7f5c77b1fe71c1ada7c872fe86b41bfb55` also docs-only. Total Closeout docs-only chain: **5 commits**. |
| TASK-017 implementation Closeout files changed | `docs/TASK_BACKLOG.md` + `docs/tasks/TASK-017-materials-mass-mechanical-implementation.md` + PR #75 body (final closeout audit table + Slice A/B/C/D accepted chain + final anchors). No `src/` / `tests/` / `ci-shard-manifest.yml` / `.github/` / `pyproject.toml` / TASK-011/012/013/014/015/016 frozen contracts / TASK-015A / TASK-016 artifacts mutation. |
| TASK-017 implementation Closeout final head | `b3b4a02485f9476e8b4b3b78a5001a3d5fb0acb5` (= LOCAL_HEAD = REMOTE_HEAD = PR #75 headRefOid; SHA_MATCH verified post-push). Closeout docs-only chain (cumulative Closeout rounds): `cda181c → d193e4d → 4edabad → 1215f58 → ad263d7 → b3b4a02` — 6 commits, all docs/governance-only. **Self-referential note**: this row records the chain itself; the next docs-only commit (if any) will be appended at the end of the chain, and the chain notation remains valid regardless of how many iterative docs commits are added. The chain-anchor reference is the primary Closeout commit `cda181c025a9369e77a4ca38ddc21ccc718df292` (per Closeout requirement §1 "明确记录 current final implementation head" — `cda181c` is the implementation-pinning Closeout commit; subsequent docs-only commits are TBD-refinement follow-ups). |
| TASK-017 implementation Closeout final CI run | `28770878128` — completed / success / head_sha `ad263d7f5c77b1fe71c1ada7c872fe86b41bfb55` exact match (latest observed CI for the Closeout docs-only chain). 50 jobs total (45 success + 5 skipped main-branch-only + 0 failed); key jobs lint / verify-manifest / parse-manifest / resolve-authority / aggregate / final-gate all success (observation only — no manual rerun). Full CI chain (Closeout docs-only round): `28770087347` (cda181c) → `28770311526` (d193e4d) → `28770562032` (4edabad) → `28770584849` (1215f58) → `28770878128` (ad263d7, latest observed). **Per iteration discipline**: CI runs are recorded against their respective chain commits; the "current valid CI" is whichever CI run's head_sha matches PR #75 headRefOid at the time of any downstream operation. |
| TASK-017 implementation Slice A verdict (audit chain) | `TASK017_SLICE_A_ACCEPTED` (head `384333a4742a7de5e77308dda0f10fa9d46df939`; 29 tests) |
| TASK-017 implementation Slice B verdict (audit chain) | `TASK017_SLICE_B_ACCEPTED` (head `eba39564336f3f29958f29d5241279298ce9769a`; 43 tests) |
| TASK-017 implementation Slice C verdict (audit chain) | `TASK017_SLICE_C_ACCEPTED_FOR_NEXT_SLICE_AUTHORIZATION` (head `945d234479400be4c65d0e0f757bcbfcf70b22ab`; 64 tests) |
| TASK-017 implementation Slice D verdict (audit chain) | `TASK017_SLICE_D_ACCEPTED_FOR_CLOSEOUT_AUTHORIZATION` (final head `4c44dc86c43eed964c2b5ff68741db9e0aa3bf53`; chain `1723e1c5 → 2c40085 → 4c44dc8`; 72 new tests; total 207 passed + 1 skipped in `tests/material_mass_mechanical/`) |
| TASK-017 implementation Closeout verdict | `TASK017_IMPLEMENTATION_CLOSEOUT_READY_FOR_REVIEW` (this round; docs/governance-only; implementation complete pending Ready / merge / Issue #74 close) |
| TASK-017 implementation PR #75 status (post-Closeout) | **OPEN / DRAFT / NOT MERGED** (Ready / merge / Issue #74 close: NOT AUTHORIZED — pending separate Charles authorization) |
| TASK-017 implementation Issue #74 status (post-Closeout) | **OPEN** (NOT CLOSED — close-link will be manual via separate explicit Closeout-authorization round per Charles discretion; current PR body uses `Refs #74`, no auto-close keyword) |
| TASK-018+ status | **PLANNED / NOT STARTED / NOT AUTHORIZED** (TASK-018+ kickoff requires separate authorization) |
| TASK-015A historical | CLOSED / MERGED (unchanged; no TASK-015A asset mutated by any TASK-015 follow-up slice) |
| TASK-016+ | PLANNED / NOT STARTED |

13. TASK-017 design kickoff was AUTHORIZED by Issue #72:
    - Design Issue #72: CLOSED / COMPLETED / `2026-07-05T18:36:26Z`
    - Design branch: `docs/task-017-materials-mass-preliminary-mechanical-design`
    - Design file: `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md`
    - Design base: `fbb05ae71f21e6cfd4d1041afb5958c863166248` (main @ PR #71 merge)
    - Design status: **DESIGN FROZEN** (Frozen Contract Authority Commit SHA = `6ed5b7dc7d8df163796eacb838afcf5702a4c53a`, Base SHA = `fbb05ae71f21e6cfd4d1041afb5958c863166248`)
    - Design contract file: `docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md`
    - Design PR CI: `28748836440` — completed / success / head_sha exact match
    - Design PR #73: MERGED at `2026-07-05T18:19:27Z` (merge commit `757e748dcef825b13397473977b181913c0cbfa8`)
    - TASK-017 implementation: **AUTHORIZED FOR KICKOFF / NOT AUTHORIZED FOR CORE LOGIC**
    - TASK-018+ : PLANNED / NOT STARTED

14. TASK-017 implementation kickoff is now AUTHORIZED by Issue #74:
    - Implementation Issue #74: OPEN
    - Implementation branch: `codex/task-017-materials-mass-mechanical-implementation`
    - Implementation file: `docs/tasks/TASK-017-materials-mass-mechanical-implementation.md`
    - Implementation base: `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge)
    - Implementation status: **AUTHORIZED FOR KICKOFF / NOT AUTHORIZED FOR CORE LOGIC** (planning + slice plan only; no production code in this commit)
    - Implementation contract file: `docs/tasks/TASK-017-materials-mass-mechanical-implementation.md`
    - TASK-017 implementation Slices A / B / C / D / Closeout: NOT YET AUTHORIZED (each requires separate authorization)
    - TASK-018+: PLANNED / NOT STARTED

15. TASK-017 implementation Slice A is AUTHORIZED FOR REVIEW (MaterialSelector only):
    - Scope: MaterialSelector + read-only TASK-013 consumer (design §5.1); new types `MaterialResolutionRequest / Result / Provenance` only.
    - Forbidden scope: no MassCalculator, no PreliminaryMechanicalChecker, no pressure-drop, no C4, no cost logic, no TASK-018+.
    - Files added (4 new, 0 modifications outside the new subtree):
      - `src/hexagent/material_mass_mechanical/__init__.py` (package marker)
      - `src/hexagent/material_mass_mechanical/material_selector.py` (MaterialSelector)
      - `tests/material_mass_mechanical/__init__.py` (package marker)
      - `tests/material_mass_mechanical/test_material_selector.py` (29 tests)
    - Tests: 29 passed in 0.55s; full repo `ruff check .` clean; `mypy` on new subtree clean.
    - Frozen design contract SHA: `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` (exposed as module literal `FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA`).
    - Frozen design contract Base SHA: `fbb05ae71f21e6cfd4d1041afb5958c863166248`.
    - Implementation branch base: `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge; unchanged).
    - Slice A review verdict: `TASK017_SLICE_A_READY_FOR_REVIEW` (pending Charles review).
    - TASK-017 implementation Slices B / C / D / Closeout: NOT AUTHORIZED.
    - TASK-018+: PLANNED / NOT STARTED.

16. TASK-017 Slice A CI manifest governance repair is AUTHORIZED (manifest registration only):
    - Authorization scope: 4 narrow mutations (design §13.2 clarification, planning doc sync, backlog evidence row, 1-line manifest registration). No `src/`, no Slice A test content changes, no other shards, no `.github/`, no frozen contracts.
    - Design contract amendment (NEW §13.2): adds a narrow clarification that implementation slices MAY register their own slice-authorized test files in `ci-shard-manifest.yml` when `verify-manifest` requires D==M ownership. Clarification does NOT authorize unrelated CI shard changes, `.github/`, or test files outside the current slice.
    - Planning doc sync: §4 added `ci-shard-manifest.yml` row (with §13.2 carve-out); §5 carved out the blanket prohibition (matches design §13.2); §7 clarified `ci-shard-manifest` job scope (structural vs content-level); §10 updated the slice authorization template.
    - Manifest registration: 1 line added to the existing `ci` shard (immediately after the TASK-013 `material_costs/test_frozen_contract_unchanged.py` entry, before the `case_revisions` entries), preserving the existing indentation / shard structure / python versions / timeout:
      ```yaml
      - tests/material_mass_mechanical/test_material_selector.py
      ```
    - Shard selection rationale: the `ci` shard already houses TASK-013 `material_costs/*` tests (read-only governance consumer pattern, job=`shard-ci`, python=["3.11", "3.12"], timeout=300). Slice A's MaterialSelector is the read-only governance consumer for TASK-013 — same shard profile. NO new shard created.
    - Local validation BEFORE commit:
      - `ruff check .` All checks passed
      - `ruff format --check .` 254 files already formatted
      - `pytest tests/material_mass_mechanical/ tests/material_costs/` 191 passed (no regression)
      - `pytest tests/ci/test_shard_manifest.py` 12 passed (manifest contract preserved)
      - `python -m tests.ci.verify_manifest --manifest ci-shard-manifest.yml --test-root tests` `d_equals_m: true`, `discovered_count: 91`, `manifest_count: 91`, `status: "pass"`
    - TASK-017 implementation Slices B / C / D / Closeout: NOT AUTHORIZED.
    - TASK-018+: PLANNED / NOT STARTED.
    - Frozen design contract SHA: `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` (UNCHANGED — §13.2 is a governance clarification, not a content hash rotation).
    - Frozen design contract Base SHA: `fbb05ae71f21e6cfd4d1041afb5958c863166248` (UNCHANGED).


17. TASK-017 implementation Slice B is AUTHORIZED FOR REVIEW (MassCalculator only):
    - Scope: MassCalculator + MassBreakdown (design §5.2 + §6); consumes Slice A MaterialResolutionResult per component_role (read-only); consumes TASK-016 GeometryCatalog for hairpin tube-geometry lookup (read-only).
    - Forbidden scope: no PreliminaryMechanicalChecker (Slices C+D), no pressure-drop, no C4, no cost logic, no new solver, no TASK-018+, no mutation of TASK-013 records or TASK-016 catalog.
    - Files added (2 new, 1 modification to Slice A subtree package marker, 1-line manifest registration):
      - `src/hexagent/material_mass_mechanical/mass_calculator.py` (MassCalculator + 5 new frozen error codes + MassCalculationRequest / MassProvenance / MassBreakdown dataclasses)
      - `tests/material_mass_mechanical/test_mass_calculator.py` (43 tests covering §6 formulas, §7 errors, §10 determinism, §8 provenance, forbidden-scope guards)
      - `src/hexagent/material_mass_mechanical/__init__.py` (re-exports Slice B public types; Slice A exports preserved)
      - `ci-shard-manifest.yml` (1 line added immediately after Slice A test entry, preserving shard structure / python versions / timeout)
    - Tests: 43 passed in 0.54s; combined Slice A + Slice B + TASK-013 = 234 passed in 1.07s (no regression); full repo `ruff check .` clean; `mypy src/hexagent/material_mass_mechanical/ tests/material_mass_mechanical/` clean.
    - Slice B design §6 formulas implemented:
      - §6.1 inner_tube: density × π × ((outer/2)² − (inner/2)²) × length
      - §6.2 outer_pipe: same formula
      - §6.3 hairpin: density × π × ((outer/2)² − (inner/2)²) × π × bend_radius_m × number_of_tubes
      - §6.4 fittings: Σ overrides (× density / 7850.0 if density_normalization=True)
    - Slice B frozen error codes (5 of 13): `GEOMETRY_CATALOG_UNAPPROVED`, `GEOMETRY_CATALOG_INCONSISTENT`, `HAIRPIN_BEND_INPUT_INCOMPLETE`, `INPUT_DIMENSIONAL_INCONSISTENT`, `INPUT_UNIT_INCONSISTENT` — defined as Final[str] in `mass_calculator.py`. Remaining 3 codes (`MATERIAL_GOVERNANCE_*`, `MATERIAL_RESOLUTION_MISSING_ROLE`) re-imported from Slice A's single source of truth. Remaining 5 mechanical / input codes reserved for Slices C+D.
    - Slice B reuses Slice A's `MaterialSelectorError` exception class (extends via positional code / message / context), so the Slice A and Slice B exception hierarchies remain unified and the design §7 single-error-class contract is satisfied.
    - Provenance: 9 fields per §8 (8 minimum + `result_hash`); correlation_ids empty for mass per §8.
    - JSON / hash / ordering: §10 RFC 8785 canonical-JSON SHA-256 (lowercase hex, 64-char); 6-decimal kg quantization per §10.3.
    - Frozen design contract SHA: `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` (UNCHANGED — Slice B is implementation-only).
    - Frozen design contract Base SHA: `fbb05ae71f21e6cfd4d1041afb5958c863166248` (UNCHANGED).
    - Implementation branch base: `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge; unchanged).
    - Slice B review verdict: `TASK017_SLICE_B_READY_FOR_REVIEW` (pending Charles review).
    - TASK-017 implementation Slices C / D / Closeout: NOT AUTHORIZED.
    - TASK-018+: PLANNED / NOT STARTED.

18. TASK-017 implementation Slice C is DELIVERED (allowable-stress check only):
    - Scope (re-executed from actual PR #75 head `eba3956`; prior invalidated Slice C report withdrawn):
      - PreliminaryMechanicalChecker with allowable-stress check ONLY (planning doc §3, design §9.1).
      - Slices D / Closeout remain NOT AUTHORIZED.
    - Files added (1 new, 3 modifications, 1-line manifest registration):
      - `src/hexagent/material_mass_mechanical/preliminary_checker.py` (NEW; planning-doc-authorized file name; PreliminaryCheckRequest / PreliminaryCheckResult / PreliminaryCheckProvenance dataclasses; 4-tier verdict per §9.1)
      - `tests/material_mass_mechanical/test_preliminary_checker.py` (NEW; 64 tests covering §5.2.2 / §9.1 / §7 / §10.3 / §10.4)
      - `src/hexagent/material_mass_mechanical/material_selector.py` (+3 frozen error codes: codes 11-13, additive only)
      - `src/hexagent/material_mass_mechanical/__init__.py` (re-exports Slice C public types; Slice A + Slice B exports preserved)
      - `ci-shard-manifest.yml` (1 line added immediately after Slice B test entry, preserving shard structure)
    - Slice C frozen error codes (3 of 13, codes 11-13): `MECHANICAL_CHECK_INPUT_DIMENSIONAL_INCONSISTENT`, `MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT`, `MECHANICAL_CHECK_UNSUPPORTED_ROLE`. Defined in `material_selector.py` (single source of truth) + re-exported from `preliminary_checker.py`. Total codes exposed across A+B+C = 11 of 13; remaining 2 (`*_UNIT_INCONSISTENT` mechanical codes) reserved for Slice D.
    - 4-tier verdict per design §9.1: `pass` (ratio ≤ 0.6) / `marginal` (0.6 < ratio ≤ 0.8) / `blocked_preliminary` (ratio > 0.8) / `blocked_for_detailed_design` (diameter > 1.0 m preliminary envelope).
    - Allowable stress lookup: `allowable_stress_mpa[design_temperature_c]` (exact-key match per design §5.1.2; no interpolation per §5.1.2 final note). Missing/empty table or no exact key → `MECHANICAL_CHECK_INPUT_UNIT_INCONSISTENT`.
    - Provenance: 12 fields (8 minimum + `outer_diameter_m` + `inner_diameter_m` + `wall_thickness_m` + `allowable_temperature_c`).
    - Decimal precision: 6 dp per §10.3 on hoop_stress_mpa / allowable_stress_mpa / stress_utilization_ratio / provenance fields.
    - JSON / hash: §10.4 RFC 8785 canonical-JSON SHA-256 (lowercase hex, 64-char).
    - Forbidden scope verified: no pressure-drop / C4 / cost / new solver / Slice D tokens (`minimum_wall`, `straight_pipe_span`, `corrosion_allowance`, etc.) / Closeout tokens in module body.
    - Tests: 64 passed in 0.90s; combined Slice A + Slice B + Slice C = 136 (in `material_mass_mechanical/`); full repo `ruff check .` clean on Slice C files; `mypy src/hexagent tests/support/...` clean (0 issues across 140 files).
    - Frozen design contract SHA: `6ed5b7dc7d8df163796eacb838afcf5702a4c53a` (UNCHANGED — Slice C is implementation-only).
    - Frozen design contract Base SHA: `fbb05ae71f21e6cfd4d1041afb5958c863166248` (UNCHANGED).
    - Implementation branch base: `757e748dcef825b13397473977b181913c0cbfa8` (= main @ PR #73 merge; unchanged).
    - Slice C delivery verdict: `TASK017_SLICE_C_READY_FOR_REVIEW` (pending Charles review).
    - TASK-017 implementation Slice D / Closeout: NOT AUTHORIZED.
    - TASK-018+: PLANNED / NOT STARTED.

