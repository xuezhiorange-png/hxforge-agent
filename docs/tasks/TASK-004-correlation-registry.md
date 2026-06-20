# TASK-004 — Correlation registry and applicability engine

**Status:** READY  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001

## Objective

Create a registry that prevents anonymous equations and evaluates whether a correlation is valid for a given geometry, phase and dimensionless-number range.

## In scope

- Correlation metadata schema.
- Versioned ID, source, purpose, geometry and phase.
- Applicability limits and uncertainty.
- Selection priority and explicit extrapolation policy.
- Registry lookup and provenance export.

## Expected files

- `src/hexagent/correlations/registry.py`
- `src/hexagent/correlations/models.py`
- `src/hexagent/correlations/catalog/*.yaml`
- `tests/unit/test_correlation_registry.py`
- `docs/CORRELATION_POLICY.md`

## Acceptance criteria

- [ ] Unregistered equations cannot be selected by solver services.
- [ ] Applicability returns `VALID`, `WARNING` or `REJECTED` with reasons.
- [ ] Source and uncertainty are present for every registered model.
- [ ] Overlapping correlations have deterministic selection rules.
- [ ] Extrapolation is never silent.

## Test plan

Boundary values, conflicting registrations, missing metadata, deterministic selection and serialized provenance.
