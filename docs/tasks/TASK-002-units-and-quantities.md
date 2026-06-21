# TASK-002 — Unit-safe quantity model

**Status:** DONE  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001  
**GitHub Issue:** #4  
**Pull Request:** #5

## Objective

Implement strict public quantity parsing and SI normalization under approved DEC-005, including correct treatment of absolute temperatures, temperature differences, absolute pressure and pressure difference.

## Completed scope

- Pydantic quantity schema and Pint adapter.
- Explicit unit allowlists by physical quantity kind.
- SI normalization and display-unit conversion.
- Absolute temperature versus delta-temperature semantics.
- Absolute pressure versus pressure-difference semantics.
- TP/PH/PQ state-specification contracts.
- Structured fouling resistance with provenance.
- Strict public input validation and structured errors.
- Physical hard bounds.
- JSON/OpenAPI quantity metadata.
- Canonical serialization and round-trip behavior.
- Legacy TP compatibility adapter behavior.
- Unit, property-based, schema, API and integration regression tests.
- `docs/UNITS.md`.

## Implemented quantity kinds

- mass flow;
- volume flow;
- absolute temperature;
- temperature difference;
- absolute pressure;
- pressure difference;
- power/duty;
- area;
- length;
- velocity;
- fouling resistance;
- specific enthalpy;
- dimensionless values.

## Acceptance criteria

- [x] Invalid dimensions are rejected with structured errors.
- [x] Celsius/Fahrenheit absolute temperatures convert correctly.
- [x] Temperature differences do not receive absolute-temperature offsets.
- [x] Mass flow, volume flow, pressure, duty, area and fouling resistance are covered.
- [x] Absolute pressure and pressure difference use separate public types.
- [x] Generic unchecked `Quantity` construction is rejected.
- [x] Public domain fields use typed quantities.
- [x] SI/display conversions support deterministic serialization and round trips.
- [x] State-spec discriminated union (TP/PH/PQ) is implemented with version `1.0`.
- [x] Structured fouling resistance is the canonical required public field.
- [x] Hard physical invariants are enforced.
- [x] Strict public input models reject unknown fields.
- [x] Unit constraints are exposed in JSON/OpenAPI schema metadata.
- [x] Canonical TP payloads pass validation and the double-pipe endpoint boundary.
- [x] Unsupported state schema versions are rejected.
- [x] `fluid.backend` is required.
- [x] Missing fouling resistance returns API 422 and is schema-required.
- [x] Round-1, Round-2 and Round-3 review findings are resolved.
- [x] GitHub CI passes on Python 3.11 and 3.12.
- [x] Final engineering approval is recorded.

## Final validation record

- Ruff: passed.
- mypy: passed for 26 source files.
- pytest: 108 passed (85 unit and 23 integration/regression tests).
- pip-audit: passed in GitHub CI.
- Missing-fouling API behavior: HTTP 422.
- `StreamSpec` schema includes `fouling_resistance` in `required`.
- Final approval: `docs/reviews/TASK-002-final-approval.md`.

## Out of scope

- fluid property calculations;
- heat-balance or specification-closure solvers;
- exchanger heat-transfer or pressure-drop correlations;
- material, cost or standards-provider logic;
- two-phase calculation implementation.

## Next task

TASK-003 may begin in a separate branch and pull request. It is limited to the property-provider contract and validated property service.
