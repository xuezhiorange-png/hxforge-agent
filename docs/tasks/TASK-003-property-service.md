# TASK-003 — Fluid property service

**Status:** READY  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001, TASK-002

## Objective

Provide a deterministic, injectable fluid-property service with CoolProp as the default backend and a contract suitable for future REFPROP and enterprise data.

## In scope

- Fluid identifiers and mixture representation.
- `TP`, `PH` and saturation queries.
- Phase identification and near-saturation handling.
- Property range, backend and convergence errors.
- Backend version and state provenance.
- Cache key design without hidden mutable state.

## Expected files

- `src/hexagent/properties/base.py`
- `src/hexagent/properties/coolprop_provider.py`
- `src/hexagent/properties/errors.py`
- `tests/unit/test_properties.py`
- `docs/PROPERTY_BACKENDS.md`

## Acceptance criteria

- [ ] Water and at least two common refrigerants return density, cp, viscosity, conductivity and enthalpy.
- [ ] Invalid fluid and invalid state errors are structured.
- [ ] Two-phase or ambiguous states are not silently treated as single phase.
- [ ] Results record backend name and version.
- [ ] Tests do not depend on network access.

## Test plan

Nominal liquid/gas states, saturation boundary, invalid states, deterministic repeatability and cross-property consistency checks.
