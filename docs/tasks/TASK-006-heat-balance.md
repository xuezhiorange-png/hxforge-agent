# TASK-006 — Heat-balance and specification closure

**Status:** READY  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-002, TASK-003, TASK-005

## Objective

Resolve valid combinations of duty, flow and inlet/outlet states while enforcing energy conservation, phase consistency and temperature feasibility.

## In scope

- Single-phase sensible heat for v0.1.
- Known-duty, known-outlet and mixed specification modes.
- Hot/cold energy residual and tolerance.
- Terminal-temperature and temperature-cross checks.
- Property iteration at representative or segmented states.
- Explicit unsupported response for phase change.

## Expected files

- `src/hexagent/core/heat_balance.py`
- `src/hexagent/domain/thermal_service.py`
- `tests/unit/test_heat_balance.py`
- `tests/golden/heat_balance/*.json`

## Acceptance criteria

- [ ] All supported specification combinations are enumerated and validated.
- [ ] Under- and over-specified cases return actionable errors.
- [ ] Energy imbalance is below 0.1% for approved cases.
- [ ] Impossible outlet temperatures are rejected.
- [ ] Phase-change cases return an explicit unsupported status in v0.1.

## Test plan

Liquid-liquid, gas-liquid, one unknown outlet, known duty, inconsistent duty, zero flow, temperature cross and property failure cases.
