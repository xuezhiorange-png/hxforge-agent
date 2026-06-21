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
- `tests/integration/test_api.py`
- `tests/integration/test_task002_round3.py`
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
- [x] State-spec discriminated union (TP/PH/PQ) is implemented with legacy TP compatibility.
- [x] Structured fouling resistance is the canonical required public field.
- [x] Hard physical invariants are enforced.
- [x] Strict public input models reject unknown fields.
- [x] Unit constraints are exposed in JSON/OpenAPI schema metadata.
- [x] Canonical TP payloads pass validation and the double-pipe endpoint boundary.
- [x] Unsupported state schema versions are rejected.
- [x] `fluid.backend` is required.
- [x] Missing fouling resistance returns API 422 and is listed as schema-required.
- [x] Round-1 review findings are resolved.
- [x] Round-2 review findings are resolved.
- [x] Round-3 schema-required fouling findings are implemented.
- [ ] Latest GitHub CI, including pip-audit, passes after Round-3 commits.
- [ ] Final engineering review is complete.

## Validation record

- Local Ruff: passed.
- Local mypy: passed for 26 source files.
- Local pytest: 108 passed (85 unit and 23 integration/regression tests).
- Local missing-fouling API behavior: 422.
- Local `StreamSpec` schema includes `fouling_resistance` in `required`.
- GitHub CI: pending for the Round-3 connector commits.

## Out of scope

- fluid property calculations;
- heat-balance or specification-closure solvers;
- exchanger heat-transfer or pressure-drop correlations;
- material, cost or standards-provider logic;
- two-phase calculation implementation.
