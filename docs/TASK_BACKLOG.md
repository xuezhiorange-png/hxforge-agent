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
| TASK-012 | Define standards rule-pack and license boundary | PLANNED | TASK-001 |
| TASK-013 | Define material and cost data governance | PLANNED | TASK-001 |
| TASK-014 | Implement immutable case revisions and persistence | PLANNED | TASK-002, TASK-003, TASK-005 |
| TASK-015 | Harden CI, security scans and release automation | PLANNED | TASK-000 |

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
| TASK-017 | Add materials, mass and preliminary mechanical checks | PLANNED | TASK-012, TASK-013, TASK-016 |
| TASK-018 | Add C0/C1 cost model and life-cycle energy estimate | PLANNED | TASK-009, TASK-013, TASK-017 |
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
6. Start TASK-012 design only after TASK-011 closeout is merged.
7. Complete TASK-012 through TASK-019 before starting shell-and-tube
   development.

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
