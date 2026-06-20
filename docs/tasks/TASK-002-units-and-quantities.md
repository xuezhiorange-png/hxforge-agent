# TASK-002 — Unit-safe quantity model

**Status:** READY  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001

## Objective

Implement strict quantity parsing and SI normalization, including correct treatment of absolute temperatures and temperature differences.

## In scope

- Pydantic quantity schema and Pint adapter.
- Allowed units by physical dimension.
- SI normalization and display-unit conversion.
- Absolute temperature versus delta-temperature semantics.
- Serialization, validation errors and round-trip behavior.

## Expected files

- `src/hexagent/core/units.py`
- `src/hexagent/domain/quantities.py`
- `tests/unit/test_units.py`
- `docs/UNITS.md`

## Acceptance criteria

- [ ] Invalid dimensions are rejected with structured errors.
- [ ] Celsius/Fahrenheit absolute temperatures convert correctly.
- [ ] Temperature differences do not receive absolute-temperature offsets.
- [ ] Mass flow, pressure, duty, area and fouling resistance are covered.
- [ ] Public calculation functions do not accept undocumented unitless values.

## Test plan

Use parameterized and property-based tests for conversions, round trips, offset temperatures, extreme values and dimension mismatches.
