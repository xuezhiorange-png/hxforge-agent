# TASK-001 — Engineering requirements baseline

**Status:** DONE  
**Milestone:** M0  
**Priority:** P0  
**Depends on:** TASK-000  
**GitHub Issue:** #3  
**Pull Request:** #2

## Objective

Freeze the v0.1 product and engineering baseline before additional solver development. The approved baseline is specific enough for coding tools to implement schemas and validation rules without inventing scope, terminology, engineering defaults or compliance claims.

## Completed work packages

### TASK-001A — Product scope and release boundary

Completed in `docs/PRODUCT_REQUIREMENTS.md`:

- target users and use scenarios;
- supported exchanger families and capability levels;
- screening, sizing, rating, comparison and reporting workflows;
- first complete vertical slice;
- explicit v0.1 exclusions;
- human engineering review and compliance boundaries.

### TASK-001B — Controlled engineering glossary

Completed in `docs/ENGINEERING_GLOSSARY.md`, including operating/design/test conditions, thermal and hydraulic terms, result states, applicability and provenance terminology.

### TASK-001C — Input/output dictionary

Completed in `docs/INPUT_OUTPUT_DICTIONARY.md`, including:

- unit-bearing public fields;
- explicit required/optional/conditional rules;
- versioned TP/PH/PQ state specification;
- exchanger-specific geometry contracts;
- structured fouling sources;
- result-state fields;
- calculation and audit hashes.

### TASK-001D — Workflow and capability matrix

Completed in `docs/WORKFLOW_MATRIX.md`, including minimum inputs, specification closure, supported/unsupported behavior, output availability and workflow-state transitions.

### TASK-001E — Decisions and representation review

Completed through:

- `docs/DECISION_LOG.md` with DEC-001 through DEC-017 approved;
- `docs/BASELINE_CASES.md` with five fixed representation cases;
- engineering review rounds 1–3 under `docs/reviews/`.

## Approved baseline cases

1. Water-to-water single-phase double-pipe sizing.
2. Water-to-water fixed-geometry double-pipe rating with catalog provenance.
3. Air-to-water shell-and-tube technology screening.
4. Water-to-water plate-exchanger screening with sanitation and cleaning constraints.
5. R134a two-phase request represented by PQ state specification and terminated as `NOT_IMPLEMENTED`.

## Acceptance criteria

- [x] Every v0.1 workflow has a complete minimum input set.
- [x] No public engineering term has multiple meanings.
- [x] Required, optional and conditional fields are explicit.
- [x] Absolute pressure and pressure difference are distinct.
- [x] Absolute temperature and temperature difference are distinct.
- [x] No numerical engineering default is hidden or implied.
- [x] Supported and unsupported capability boundaries are explicit.
- [x] Three-way state model (`workflow_stage`, `verification_level`, `requires_review`) is defined.
- [x] Five baseline cases are fixed with concrete fluids, state specifications, geometry and structured sources.
- [x] No output language can be confused with certified pressure-vessel design.
- [x] Deterministic `calculation_hash` and separate `audit_record_hash` are defined.
- [x] Engineering owner approved DEC-001 through DEC-017 in `docs/DECISION_LOG.md`.

## Final approval record

- Engineering review completed: 2026-06-21.
- Latest CI before approval: Python 3.11 and Python 3.12 quality jobs passed.
- Approved downstream start: TASK-002.
- TASK-003 and later tasks remain subject to their specific dependencies and validation gates.

## Coding-tool instruction for the next task

Start TASK-002 only. Implement the unit-safe quantity model and SI boundary semantics against the approved DEC-005 and public input/output contracts. Do not begin property-service, heat-balance or exchanger-correlation work in the same pull request.
