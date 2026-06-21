# TASK-003 — Fluid property service

**Status:** IN_PROGRESS  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001, TASK-002  
**GitHub Issue:** #6  
**Branch:** `codex/task-003-property-service`

## Objective

Provide a deterministic, injectable fluid-property service with CoolProp as the default backend and a contract suitable for future REFPROP and enterprise data.

## In scope

- Fluid identifiers and mixture representation.
- `TP`, `PH`, pressure-saturation and temperature-saturation queries.
- Phase identification and explicit near-saturation handling.
- Property range, backend and convergence errors.
- Backend version and git-revision provenance.
- Explicit cache-key design without hidden mutable engineering state.
- Tier-1 validation for Water, Air, R134a and R717.

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
- [x] Water, Air, R134a and R717 validation cases are covered by tests.
- [x] Invalid fluid and invalid state errors are structured.
- [x] Two-phase and near-saturation states are explicitly rejected from single-phase queries.
- [x] Results record backend name, version, git revision and state provenance.
- [x] Deterministic cache keys and cache inspection are implemented.
- [x] Tests require no network access.
- [x] Round-1 review: 8 items addressed (reference state, validation matrix, PH ref-state, backend naming, serialization, PH tolerance, mixture boundary, error regressions).
- [ ] GitHub CI passes on Python 3.11 and 3.12.
- [ ] Engineering review is complete.

## Test plan

- nominal liquid and gas TP states;
- TP-to-PH cross consistency;
- saturation liquid/vapor states;
- exact saturation and two-phase rejection;
- invalid fluids and invalid numeric inputs;
- Tier-1 versus unvalidated-fluid policy;
- cache determinism and mixture identity;
- PH reference-state mismatch rejection;
- JSON round-trip serialization (FluidState, SaturationState);
- PH saturation tolerance reference-state invariance;
- mixture capability boundary (representation vs calculation);
- error-boundary regressions (out-of-range, above-critical, unsupported backend, malformed composition, empty name, stable error codes, failed-query cache).

## Scope boundary

Do not add heat-balance equations, exchanger correlations, geometry selection, costing or mechanical design in this task.
