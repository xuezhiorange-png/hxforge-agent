# TASK-009 — Double-pipe sizing and candidate optimization

**Status:** READY  
**Milestone:** M2  
**Priority:** P0  
**Depends on:** TASK-008

## Objective

Generate standard, manufacturable double-pipe candidates and find feasible designs that meet duty, pressure-drop, velocity, length and margin constraints.

## In scope

- Approved pipe/tube geometry catalog.
- Series/parallel circuits and hairpin count.
- Discrete diameter, schedule and length enumeration.
- Hard-constraint filtering before scoring.
- Thermal margin, pumping power, area, mass and preliminary cost metrics.
- Pareto candidate output.

## Expected files

- `src/hexagent/exchangers/double_pipe/catalog.py`
- `src/hexagent/exchangers/double_pipe/sizing.py`
- `src/hexagent/optimization/candidates.py`
- `tests/unit/test_double_pipe_sizing.py`
- `tests/golden/double_pipe/sizing/*.json`

## Acceptance criteria

- [ ] Generated geometry is limited to catalog values.
- [ ] Every returned candidate passes all hard constraints.
- [ ] Infeasible cases explain the limiting constraints.
- [ ] Candidate ranking is deterministic for fixed weights.
- [ ] Pareto results preserve alternatives instead of returning one opaque optimum.

## Test plan

Feasible and infeasible duties, tight pressure-drop limits, length constraints, parallelization, deterministic ranking and duplicate-candidate elimination.
