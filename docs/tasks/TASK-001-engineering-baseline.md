# TASK-001 — Engineering requirements baseline

**Status:** IN_PROGRESS  
**Milestone:** M0  
**Priority:** P0  
**Depends on:** TASK-000  
**GitHub Issue:** #3  
**Draft PR:** #2

## Objective

Freeze the v0.1 product and engineering baseline before additional solver development. The output of this task must be specific enough that a coding tool can implement schemas and validation rules without inventing scope, terminology, engineering defaults or compliance claims.

## Why this task comes first

Units, property calls, heat-balance closure, exchanger modules and reports all depend on shared meanings for inputs, outputs and result states. Starting calculation code before these decisions are approved would create incompatible schemas and hidden assumptions.

## Work packages

### TASK-001A — Product scope and release boundary

Deliver `docs/PRODUCT_REQUIREMENTS.md` defining:

- target users and main use scenarios;
- supported exchanger families;
- screening, sizing, rating, comparison and report workflows;
- first complete vertical slice;
- explicit v0.1 exclusions;
- human engineering review and compliance boundaries.

### TASK-001B — Controlled engineering glossary

Deliver `docs/ENGINEERING_GLOSSARY.md` defining at minimum:

- screening, sizing and rating;
- operating, design and test conditions;
- duty, approach temperature, temperature cross and LMTD;
- allowable and calculated pressure drop;
- fouling resistance and area margin;
- preliminary mechanical design and code compliance;
- candidate, recommendation, warning, blocker and provenance.

### TASK-001C — Input/output dictionary

Deliver `docs/INPUT_OUTPUT_DICTIONARY.md` defining every public field:

- business and engineering meaning;
- data type and unit dimension;
- required, optional or conditional status;
- ownership and source;
- validation rule;
- default policy;
- output confidence and status.

### TASK-001D — Workflow and capability matrix

Deliver `docs/WORKFLOW_MATRIX.md` defining:

- minimum input combinations for each workflow;
- specification-closure rules;
- supported and unsupported service types;
- output availability by workflow;
- warning, blocker and `NOT_IMPLEMENTED` behavior;
- state transitions.

### TASK-001E — Decisions and representation review

Deliver:

- `docs/DECISION_LOG.md` with explicit owner approval status;
- `docs/BASELINE_CASES.md` containing five representative documentation cases;
- a review record confirming that no case needs an undocumented field or hidden default.

## Required baseline cases

1. Water-to-water single-phase double-pipe sizing.
2. Water-to-water fixed-geometry double-pipe rating.
3. Gas-to-liquid shell-and-tube technology screening.
4. Plate-exchanger screening with sanitation and cleaning constraints.
5. Unsupported two-phase refrigerant evaporator returning `NOT_IMPLEMENTED` or `BLOCKED`.

## In scope

- product and engineering terminology;
- v0.1 capability boundaries;
- public data contracts at documentation level;
- result statuses and human-review requirements;
- explicit default and unsupported-scope policies;
- example-case representation review.

## Out of scope

- heat-transfer or pressure-drop equations;
- correlation selection;
- property calculations;
- database implementation;
- detailed mechanical formulas;
- numerical engineering defaults;
- vendor-equivalent geometry claims;
- certified code-compliance logic.

## Acceptance criteria

- [x] Every v0.1 workflow has a complete minimum input set.
- [x] No public engineering term has multiple meanings.
- [x] Required, optional and conditional fields are explicit.
- [x] Absolute pressure and pressure difference are distinct.
- [x] Absolute temperature and temperature difference are distinct.
- [x] No numerical engineering default is hidden or implied.
- [x] Supported and unsupported capability boundaries are explicit.
- [x] Three-way state model (workflow_stage, verification_level, requires_review) is defined.
- [x] Five baseline cases are fixed with concrete fluids, geometry, and structured fouling sources.
- [x] No output language can be confused with certified pressure-vessel design.
- [x] Result hash has a deterministic canonical payload definition.
- [ ] Engineering owner approves or rejects each proposed decision in `DECISION_LOG.md`.

## Review gates

### Gate 1 — Scope review

Approve TASK-001A before detailed schema implementation begins.

### Gate 2 — Dictionary review

Approve TASK-001B through TASK-001D before TASK-002 starts.

### Gate 3 — Representation review

Approve all five baseline cases and the decision log before TASK-001 is marked `DONE`.

## Coding-tool instruction

This task is documentation and schema design only. Do not add engineering equations, correlations or numerical fallbacks. Do not resolve an open engineering decision by guessing. Record unresolved items in `docs/DECISION_LOG.md` and keep downstream tasks blocked until the owner decides.

## Completion response

Report:

- documents changed;
- decisions still awaiting approval;
- ambiguities found in the current domain models;
- five-case representation-review result;
- whether TASK-002 is unblocked.
