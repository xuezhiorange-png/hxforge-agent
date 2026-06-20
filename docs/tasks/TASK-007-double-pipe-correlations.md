# TASK-007 — Double-pipe thermal-hydraulic correlations

**Status:** READY  
**Milestone:** M2  
**Priority:** P0  
**Depends on:** TASK-003, TASK-004, TASK-006

## Objective

Implement validated single-phase circular-tube and annulus heat-transfer and pressure-drop models used by double-pipe rating.

## In scope

- Laminar, transitional policy and turbulent regimes.
- Circular tube and concentric annulus geometry.
- Reynolds, Prandtl, Nusselt, friction factor and local losses.
- Wall-viscosity correction where supported by approved sources.
- Range checks and uncertainty metadata.

## Expected files

- `src/hexagent/correlations/internal_flow.py`
- `src/hexagent/correlations/annulus_flow.py`
- `src/hexagent/correlations/friction.py`
- registry catalog entries
- `tests/unit/test_internal_flow.py`
- `tests/unit/test_annulus_flow.py`

## Acceptance criteria

- [ ] Every model is registered with source and validity range.
- [ ] Laminar/turbulent behavior and transitional policy are explicit.
- [ ] Pressure drop increases with flow for controlled test cases.
- [ ] Heat-transfer trends are physically consistent.
- [ ] Out-of-range states warn or reject according to policy.

## Test plan

Published examples, boundary Reynolds numbers, roughness limits, viscosity variation and physical monotonicity tests.
