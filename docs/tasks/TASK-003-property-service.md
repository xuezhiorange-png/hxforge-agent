# TASK-003 — Fluid property service

**Status:** DONE  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001, TASK-002  
**GitHub Issue:** #6  
**Branch:** `codex/task-003-property-service`  
**Final approval:** `docs/reviews/TASK-003-final-approval.md`

## Objective

Provide a deterministic, injectable fluid-property service with CoolProp as the default backend and a contract suitable for future REFPROP and enterprise data.

## In scope

- Fluid identifiers and mixture representation.
- `TP`, `PH`, pressure-saturation and temperature-saturation queries.
- Phase identification and explicit near-saturation handling.
- Property range, backend and convergence errors.
- Backend version and git-revision provenance.
- Explicit cache-key design without hidden mutable engineering state.
- Tier-1 support for Water, Air, R134a and R717.

## Expected files

- `src/hexagent/properties/base.py`
- `src/hexagent/properties/coolprop_provider.py`
- `src/hexagent/properties/errors.py`
- `src/hexagent/core/contracts.py`
- `tests/unit/test_properties.py`
- `docs/PROPERTY_BACKENDS.md`

## Acceptance criteria

- [x] Provider protocol and typed property results are defined.
- [x] TP and PH query paths are implemented.
- [x] Saturation queries by pressure and temperature are implemented.
- [x] Water, Air, R134a and R717 support and regression cases are covered by tests.
- [x] Invalid fluid and invalid state errors are structured.
- [x] Two-phase and near-saturation states are explicitly rejected from single-phase queries.
- [x] Results record backend name, version, git revision and state provenance.
- [x] Deterministic cache keys and cache inspection are implemented.
- [x] Tests require no network access.
- [x] Round 1 engineering review resolved.
- [x] Round 2 engineering review resolved.
- [x] Round 3 engineering review resolved.
- [x] Round 4 engineering review resolved.
- [x] GitHub CI passes on Python 3.11 and 3.12.
- [x] Engineering review is complete.

## Verification

- Reviewed code head: `44e7516e98a153623c6e28bc430ecd54439ec9f0`.
- CI run: `27905712482` — success.
- Gates: Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12.
- Test suite: 191 passed.

## Test plan covered

- nominal liquid and gas TP states;
- TP-to-PH cross consistency;
- saturation liquid/vapor states;
- exact saturation and two-phase rejection;
- invalid fluids and invalid numeric inputs;
- Tier-1 versus unvalidated-fluid policy;
- cache determinism and mixture identity;
- required PH reference-state identity and mismatch rejection;
- strict JSON round trips for FluidState, SaturationState and PropertyServiceError;
- PH saturation tolerance reference-state invariance;
- mixture capability boundary: representable, calculation unsupported in v0.1;
- error-boundary regressions and message-independent backend-failure classification;
- validation provenance for backend-regression, support-allowlist and unvalidated opt-in cases.

## Scope boundary

This task does not add heat-balance equations, exchanger correlations, geometry selection, costing, mechanical design or downstream two-phase exchanger solvers.
