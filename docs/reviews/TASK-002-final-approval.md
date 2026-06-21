# TASK-002 Final Engineering Approval

**Task:** TASK-002 — Unit-safe quantity model  
**Pull request:** #5  
**Decision:** APPROVED  
**Approval date:** 2026-06-21  
**Approver:** Engineering owner / project owner

## Approved scope

The following implementation is approved for v0.1:

- typed Pydantic engineering quantities;
- explicit Pint-backed unit allowlists;
- SI normalization and display conversion;
- separation of absolute temperature from temperature difference;
- separation of absolute pressure from pressure difference;
- TP/PH/PQ state-specification contracts with version `1.0`;
- explicit required property backend;
- canonical structured fouling resistance with source metadata;
- strict public input models using `extra="forbid"`;
- physical hard bounds for absolute temperature, absolute pressure, mass flow, area, length and fouling resistance;
- generated quantity schema metadata;
- legacy TP compatibility without conflicting new/legacy state inputs;
- canonical TP integration at the existing double-pipe API boundary;
- structured validation errors and regression tests.

## Final clarification

The legacy `inlet_temperature` and `inlet_pressure` fields remain a temporary compatibility path only. Canonical new integrations must use `state_spec`. Unsourced bare fouling values are not accepted.

PH and PQ states are representable by the public schema but remain outside the implemented calculation scope. They must return explicit unsupported behavior until property and two-phase tasks are completed.

## Verification

- Python 3.11 quality job: passed.
- Python 3.12 quality job: passed.
- Ruff, mypy, pytest and pip-audit: passed.
- Local regression suite: 108 tests passed.
- Missing required fouling returns API 422.
- `StreamSpec` JSON Schema lists `fouling_resistance` as required.

## Downstream authorization

TASK-003 may begin in a separate branch and pull request. Its scope is the property-provider contract and validated CoolProp-backed property service. It must not add exchanger correlations or heat-balance logic in the same pull request.
