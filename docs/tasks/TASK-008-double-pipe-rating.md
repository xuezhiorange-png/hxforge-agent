# TASK-008 — Double-pipe rating solver

**Status:** READY  
**Milestone:** M2  
**Priority:** P0  
**Depends on:** TASK-005, TASK-006, TASK-007

## Objective

Given a fixed, manufacturable double-pipe geometry, calculate thermal performance, outlet states, overall coefficient and both-side pressure drops with convergence and traceability.

## In scope

- Counterflow single-phase service.
- Inner tube, annulus, wall and fouling resistance.
- Temperature-dependent property iteration.
- Fixed-area rating and duty-limited outlet calculation.
- Straight-pipe and configured local losses.
- Velocity and preliminary erosion warnings.

## Expected files

- `src/hexagent/exchangers/double_pipe/models.py`
- `src/hexagent/exchangers/double_pipe/rating.py`
- `src/hexagent/exchangers/double_pipe/geometry.py`
- `tests/unit/test_double_pipe_rating.py`
- `tests/golden/double_pipe/rating/*.json`

## Acceptance criteria

- [ ] Energy imbalance below 0.1% for Golden cases.
- [ ] Iteration convergence and failure state are explicit.
- [ ] Total resistance components reconcile with calculated U.
- [ ] Pressure-drop components sum to totals.
- [ ] All correlation and property calls are present in provenance.
- [ ] Unsupported phase change is blocked.

## Test plan

At least three published/internal cases, clean versus fouled, low/high flow, excessive pressure drop, non-convergence and physical trend tests.
