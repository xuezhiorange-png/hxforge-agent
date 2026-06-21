# HXForge Engineering Decision Log

This document is the authoritative v0.1 engineering-decision baseline.

## Approval record

- **Decision set:** DEC-001 through DEC-017
- **Status:** APPROVED
- **Approver:** Engineering owner / project owner
- **Approval date:** 2026-06-21
- **Approval scope:** v0.1 architecture, public data contracts and downstream task constraints
- **Review basis:** TASK-001 engineering review rounds 1–3 and five baseline representation cases
- **Implementation rule:** Approved decisions define policy and contracts. Numerical model details still require task-level implementation, tests, applicability checks and validation.

## Decision index

| ID | Approved decision | Status | Primary dependency |
|---|---|---|---|
| DEC-001 | First complete vertical slice is single-phase double-pipe / hairpin | APPROVED | TASK-007–010 |
| DEC-002 | Shell-and-tube and plate may participate in screening before detailed solvers exist | APPROVED | Screening workflow |
| DEC-003 | Unvalidated two-phase sizing/rating returns `NOT_IMPLEMENTED` | APPROVED | TASK-003, TASK-006, TASK-080+ |
| DEC-004 | No hidden numerical engineering defaults | APPROVED | All public schemas |
| DEC-005 | SI calculation kernel; absolute temperature and temperature difference are distinct | APPROVED | TASK-002 |
| DEC-006 | Results use `workflow_stage`, `verification_level` and derived `requires_review` | APPROVED | TASK-005, API, reports |
| DEC-007 | Preliminary calculations never claim certified code compliance | APPROVED | Reports and rule packs |
| DEC-008 | Numerical outputs require provenance and structured warnings | APPROVED | TASK-005 |
| DEC-009 | Candidate generation is limited to approved manufacturable catalogs | APPROVED | TASK-009, TASK-016 |
| DEC-010 | Blocking errors prevent recommendation and report-ready state | APPROVED | All workflows |
| DEC-011 | CoolProp is the first default v0.1 property backend | APPROVED | TASK-003 |
| DEC-012 | Correlations declare individual applicability envelopes; reject outside by default | APPROVED | TASK-004, TASK-007 |
| DEC-013 | Geometry candidates must be sourced, versioned and manufacturable | APPROVED | TASK-009, TASK-016–017 |
| DEC-014 | Numerical solvers use typed, solver-specific convergence criteria | APPROVED | TASK-006, TASK-008–009 |
| DEC-015 | Sizing selects discrete geometry; rating does not modify supplied geometry | APPROVED | TASK-008–009 |
| DEC-016 | Fluid validation is managed in three tiers | APPROVED | TASK-003 and release validation |
| DEC-017 | Fouling resistance uses a structured and verifiable source object | APPROVED | Input schemas, reports |

## Normative decisions

### DEC-001 — First vertical slice

The first end-to-end calculation workflow is single-phase double-pipe / hairpin service. It must prove input validation, property calls, heat balance, rating, sizing, candidate comparison, provenance and reporting before other detailed exchanger solvers are expanded.

### DEC-002 — Screening before detailed implementation

Shell-and-tube and plate exchangers may participate in technology screening before detailed sizing or rating is implemented. Screening must never fabricate detailed thermal, hydraulic or geometric results for an unavailable module.

### DEC-003 — Two-phase capability boundary

Condensation, evaporation and other two-phase services may be identified and represented by the public state schema, but detailed sizing/rating returns `NOT_IMPLEMENTED` until approved models and validation cases are available. A single-phase model must never be used as a fallback.

### DEC-004 — No hidden engineering defaults

Fouling resistance, area margin, roughness, material, corrosion allowance, cost basis, correlation choice and similar engineering values must be supplied by the user or resolved from an approved, visible and traceable rule/catalog source.

### DEC-005 — Unit policy

The deterministic calculation core uses SI units. API and report layers may convert to requested display units. Absolute temperature and temperature difference are separate quantity dimensions; absolute pressure and pressure difference are also separate.

### DEC-006 — Result-state model

Every run carries three independent fields.

#### `workflow_stage`

`DRAFT`, `INPUT_VALIDATED`, `THERMAL_SERVICE_RESOLVED`, `TECHNOLOGIES_SCREENED`, `CANDIDATES_GENERATED`, `CANDIDATES_RATED`, `ENGINEERING_CHECKED`, `COSTED`, `VERIFICATION_COMPLETED`, `REPORT_READY`, `BLOCKED`, `NOT_IMPLEMENTED`, `NON_CONVERGED`.

#### `verification_level`

`UNVERIFIED`, `PRELIMINARY`, `BENCHMARK_VALIDATED`, `ENGINEERING_APPROVED`, `N/A`.

#### `requires_review`

This is derived, not user supplied.

It is `false` only in either of these cases:

1. `verification_level = ENGINEERING_APPROVED`, with no open warnings, blockers, unresolved assumptions or deviations; or
2. the run terminates without an engineering result (`BLOCKED`, `NOT_IMPLEMENTED` or `NON_CONVERGED`) and `verification_level = N/A`.

It is `true` for all usable results that have not reached `ENGINEERING_APPROVED`, including `BENCHMARK_VALIDATED` results.

### DEC-007 — Compliance boundary

HXForge does not claim certified ASME, TEMA, API or statutory compliance from preliminary calculations. Licensed standards and qualified engineering review remain external approval requirements.

### DEC-008 — Provenance and warnings

Every numerical result records resolved inputs, unit conversions, property backend and version, correlation IDs and versions, applicability results, intermediate calculations, convergence data, warnings, blockers, software version and commit identity.

### DEC-009 — Catalog-limited optimization

Sizing may only select approved discrete dimensions and configurations from versioned catalogs. Continuous optimizers may rank combinations but may not invent non-procurable dimensions.

### DEC-010 — Blocking behavior

A blocking input, safety, property, convergence, applicability or specification-closure condition prevents candidate recommendation and prevents `REPORT_READY`.

### DEC-011 — Property backend

CoolProp is the first default v0.1 property backend behind an injectable `PropertyProvider` contract. Alternative backends remain replaceable but are not assumed implemented.

### DEC-012 — Correlation applicability

Each registered correlation declares its own Reynolds, Prandtl, geometry, roughness, fluid and phase envelope. Inputs outside the envelope are rejected by default. Transition interpolation is permitted only through an explicitly approved and validated composite model, with a warning and provenance.

### DEC-013 — Manufacturable geometry

Every candidate geometry carries catalog ID, entry ID, version/revision, source and material/surface provenance. Hairpin length constraints are checked independently for manufacturer capability, transport, installation and maintenance access. File format is an ADR-level software decision.

### DEC-014 — Convergence framework

Heat-balance acceptance is separate from numerical solver convergence.

- Heat-balance error uses an absolute-value denominator and non-zero reference floor.
- Every iterative solver declares a typed primary variable, typed absolute tolerance, dimensionless relative tolerance, scaling quantity and residual definition.
- A typical criterion is `abs(delta_x) <= absolute_tolerance + relative_tolerance * scaling_quantity`.
- Temperature scales are expressed directly in kelvin after SI normalization; no repeated offset conversion is allowed.
- Maximum iterations are configurable and traceable.
- Failure terminates as `NON_CONVERGED`; the last iterate is not returned as a valid result.

### DEC-015 — Sizing and rating margins

Sizing accepts a catalog candidate only when:

`actual_area >= required_area × (1 + required_margin)`.

Rating never modifies the supplied structure. It reports actual area, required area, area margin and duty margin as outputs.

### DEC-016 — Fluid validation tiers

- **Tier 1, required before TASK-003 completion:** Water, Air, R134a single-phase, R717 single-phase.
- **Tier 2, required before v0.1 release:** R404A single-phase and R507A single-phase, independently tested.
- **Tier 3, separate incompressible-fluid work:** MPG, MPG2, APG and other glycol-water models with explicit concentration basis and validity range.

Two-phase R134a/R717 service remains subject to DEC-003.

### DEC-017 — Fouling source contract

`fouling_resistance.source` contains:

- `source_type`: `STANDARD`, `VENDOR`, `USER` or `ASSUMED`;
- `reference_id`;
- `edition`;
- `table_or_clause`;
- `verification_status`: `VERIFIED` or `UNVERIFIED_REFERENCE`;
- `note`.

An unverified reference produces a warning. Explicit zero fouling must use `USER` or `ASSUMED`, state that zero fouling was deliberately selected and produce a warning.

## Approved implementation clarifications

- New public APIs must use an explicit versioned `state_spec` union (`TP`, `PH` or `PQ`). Legacy inlet-temperature/inlet-pressure fields may only be handled by a clearly deprecated compatibility adapter, not by a hidden engineering default.
- Deterministic calculation identity is stored in `calculation_hash`; mutable review and approval metadata is protected separately by `audit_record_hash`.
- Example standards and catalog references marked `UNVERIFIED_REFERENCE` are documentation placeholders only and cannot be treated as approved engineering data.

## Change control

Any change to these decisions requires a new decision ID or a `SUPERSEDED` record that identifies the replacing decision, affected schemas, migration impact and required regression updates.
