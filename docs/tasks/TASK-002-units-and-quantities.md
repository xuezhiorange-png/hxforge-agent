# TASK-002 — Unit-safe quantity model

**Status:** IN_PROGRESS  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001  
**GitHub Issue:** #4  
**Branch:** `codex/task-002-units-and-quantities`

## Objective

Implement strict public quantity parsing and SI normalization under approved DEC-005, including correct treatment of absolute temperatures, temperature differences, absolute pressure and pressure difference.

## In scope

- Pydantic quantity schema and Pint adapter.
- Explicit unit allowlists by physical quantity kind.
- SI normalization and display-unit conversion.
- Absolute temperature versus delta-temperature semantics.
- Absolute pressure versus pressure-difference semantics.
- Structured conversion and validation errors.
- Serialization, canonicalization and round-trip behavior.
- Migration of current public domain fields to typed quantities.
- Parameterized and property-based tests.
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

## Expected files

- `src/hexagent/core/units.py`
- `src/hexagent/domain/quantities.py`
- `src/hexagent/domain/models.py`
- `tests/unit/test_units.py`
- `docs/UNITS.md`

## Acceptance criteria

- [x] Invalid dimensions are rejected with structured errors.
- [x] Celsius/Fahrenheit absolute temperatures convert correctly.
- [x] Temperature differences do not receive absolute-temperature offsets.
- [x] Mass flow, volume flow, pressure, duty, area and fouling resistance are covered.
- [x] Absolute pressure and pressure difference use separate public types.
- [x] Generic unchecked `Quantity` construction is rejected.
- [x] Current public domain fields use typed quantities.
- [x] SI/display conversions support deterministic serialization and round trips.
- [x] Local Ruff, mypy and pytest gates pass.
- [x] State-spec discriminated union (TP/PH/PQ) implemented with legacy compat.
- [x] Structured fouling resistance (FoulingSource + FoulingResistanceSpec).
- [x] Hard physical invariants enforced (T>0K, P>0Pa, area>=0, mass_flow>0).
- [x] Strict public input base model (extra='forbid' on all public models).
- [x] Unit constraints exposed in JSON/OpenAPI schema metadata.
- [x] Integration and compatibility regression tests added (21 integration tests total).
- [x] Round-1 review findings resolved.
- [x] Round-2 review findings resolved (canonical fouling, state helpers, schema_version, backend required).
- [ ] GitHub CI, including pip-audit, passes.

## Validation completed locally

- Ruff: passed.
- mypy: passed (26 source files, zero errors).
- pytest: 106 passed (85 unit + 21 integration/regression tests).
- Unit-module coverage: above 90%.
- pip-audit: passed.
- pip-audit: deferred to GitHub CI because the local runtime could not resolve pypi.org.

## Out of scope

- fluid property calculations;
- heat-balance or specification-closure solvers;
- exchanger heat-transfer or pressure-drop correlations;
- material, cost or standards-provider logic;
- two-phase calculation implementation.
