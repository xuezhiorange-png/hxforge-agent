# TASK-006 — Heat-balance and specification closure

**Status:** DONE  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-002, TASK-003, TASK-005  
**GitHub Issue:** #13  
**Branch:** `codex/task-006-heat-balance`  
**Draft PR:** #14

## Objective

Resolve valid combinations of duty, flow and inlet/outlet states while enforcing energy conservation, phase consistency and temperature feasibility.

## Current engineering status

TASK-006 is **DONE**. All 18 review rounds have been resolved. CI is green on Python 3.11 and 3.12 (943 passed, 1 skipped). Independent technical approval recorded in GitHub Review ID 4549628395. GitHub APPROVE event was unavailable because the connected identity owns the PR.

Authoritative reviews:

- `docs/reviews/TASK-006-engineering-review-01.md`
- `docs/reviews/TASK-006-engineering-review-02.md`

## In scope

- Single-phase sensible heat for v0.1.
- Known-duty, known-outlet and mixed specification modes.
- Hot/cold energy residual and tolerance.
- Terminal-temperature, minimum-approach and temperature-cross checks.
- Property-provider evaluation and deterministic unknown-outlet solution.
- Explicit unsupported response for phase change.
- Structured warnings, blockers and run failures.
- Deterministic result hashing and provenance serialization.

## Explicitly out of scope

- LMTD and epsilon-NTU.
- Heat-transfer coefficients or new engineering correlations.
- Pressure-drop calculations.
- Geometry sizing, rating, candidate generation or optimization.
- Two-phase heat balance.
- Database, API and report implementation.
- TASK-007 scope.

## Required engineering contracts

### Specification closure

Supported and unsupported combinations must be explicitly enumerated. Under-specified and over-specified combinations must return stable structured results rather than relying on exception-message parsing.

### Energy convention

- Heat duty is positive from hot stream to cold stream.
- `Q_hot = m_hot × (h_hot,in − h_hot,out)`.
- `Q_cold = m_cold × (h_cold,out − h_cold,in)`.
- Residual and acceptance basis must be explicit and dimensionally consistent.
- Approved non-zero-duty solutions require relative imbalance below `0.001`.
- Zero/near-zero duty requires an explicit absolute tolerance in watts.

### Property and phase safety

- Use the existing `PropertyProvider`; no fixed-Cp assumptions in public services.
- Record actual provider calls, including failures.
- Do not substitute synthetic residuals for invalid thermodynamic states.
- Reject saturated states, unsupported phases and incompatible inlet/outlet phase-family transitions.

### Temperature feasibility

- v0.1 supports explicitly declared counterflow only.
- Terminal pairs must follow counterflow topology.
- Non-positive terminal approach and true temperature cross are blockers.
- Near-zero positive approach may be a warning under an explicit tolerance policy.

### Result and failure contracts

- `solve_heat_balance()` must not leak private solver exceptions.
- Structural errors return `BLOCKED`; numerical convergence failures return `FAILED` with `RunFailure`.
- Blocked/failed results must not contain fabricated thermodynamic states or fabricated property calls.
- Public models are deeply immutable and recursively finite.

### Determinism and provenance

- Result hash covers complete request, provider, solver, result, messages and failure identity.
- Provenance uses real domain identities where available and must not invent case-revision lineage.
- Node IDs and JSON serialization are deterministic for the same canonical calculation.

## Expected files

- `src/hexagent/core/heat_balance.py`
- `src/hexagent/domain/thermal_service.py`
- `tests/unit/test_heat_balance.py`
- `tests/integration/test_heat_balance_property_provider.py`
- `tests/golden/heat_balance/*.json`
- `docs/HEAT_BALANCE.md`

## Acceptance criteria

- [ ] Supported specification combinations are enumerated and validated.
- [ ] Under-/over-specification returns structured blockers.
- [ ] Public API does not leak private solver exceptions.
- [ ] Relative and absolute energy acceptance are dimensionally explicit.
- [ ] Impossible temperatures and non-positive terminal approaches are blocked.
- [ ] Phase-change and invalid iterative states cannot be accepted.
- [ ] Zero-duty specifications cannot be silently overwritten.
- [ ] Result models are deeply immutable and recursively finite.
- [ ] Result hashes are complete and deterministic.
- [ ] Provenance contains no invented case-revision identity.
- [ ] Flow arrangement is explicit at the domain-service boundary.
- [ ] Existing and new tests remain green on Python 3.11 and 3.12.

## Quality gates

- Ruff and Ruff format.
- Repository-wide mypy.
- Complete pytest suite.
- pip-audit.
- Python 3.11 and 3.12 CI.

## Review history

| Round | Head | CI Run | Decision | Date |
|-------|------|--------|----------|------|
| Review-01 | `1919098` | #125 | CHANGES REQUIRED | 2026-06-22 |
| Review-02 | `858acc3` | #125 | CHANGES REQUIRED | 2026-06-22 |
| Review-03 | `fffe610` | #128 | CHANGES REQUIRED | 2026-06-22 |
| Review-04 | `a389108` | #128 | CHANGES REQUIRED | 2026-06-22 |
| Review-05 | `796e10c` | #131 | CHANGES REQUIRED | 2026-06-22 |
| Review-06 | `b9a04c4` | #131 | CHANGES REQUIRED | 2026-06-22 |
| Review-07 | `a3a2fe8` | #14 | CHANGES REQUIRED | 2026-06-22 |
| Review-08 | `4c0ea24` | #14 | CHANGES REQUIRED | 2026-06-22 |
| Review-09 | `7745663` | #14 | IN_PROGRESS | 2026-06-22 |
| Review-10 | `3b5eada` | #14 | IN_PROGRESS | 2026-06-22 |
| Review-11 | `7d106cb` | #14 | IN_PROGRESS | 2026-06-22 |
| Review-12 | `0b58f1b` | #14 | IN_PROGRESS | 2026-06-22 |
| Review-13 | `0fd3e90` | #14 | CHANGES REQUIRED | 2026-06-22 |
| Review-14 | `3beaeb1` | #14 | CHANGES REQUIRED | 2026-06-23 |
| Review-15 | `602fda4` | 27994422952 | CHANGES REQUIRED | 2026-06-23 |
| Review-16 | `8cc210d` | 27995704383 | CHANGES REQUIRED | 2026-06-23 |
| Review-17 | `d93646e` | 27997396995 | CHANGES REQUIRED | 2026-06-23 |
| Review-18 | `b793ee0` | 27998540720 | APPROVED | 2026-06-23 |

Review-12 implementation commit: `0b58f1b11bf7e0401c7193f4d28b46f95bdd5c63`
Implementation CI: `27974294657`
Review-13 implementation commit: `0fd3e90a06d6f132d961502614ceb45674d90770`
Review-13 CI: `27991527536`
Review-14 implementation commit: `3812123d2b01373e1d78d0231ad1057c9016cd05`
Review-14 CI: `27993236972`
Review-15 implementation commit: `602fda4cadf10521247c780319cab09ab60e7102`
Review-15 CI: `27994422952`
Review-16 implementation commit: `b9574bbc639494f76d7f011b841960c6c34d2bcc`
Review-16 CI: `27995620330`
Review-17 implementation commit: `cb69a8507fe3849b6c674ef853ae9b04b5205032`
Review-17 CI: `27997396995`
Review-18 implementation commit: `ae424e86853489fc06f1bdadbf0d907b65354e58`
Review-18 CI: `27998095729`

Independent technical approval recorded in GitHub Review ID 4549628395.
GitHub APPROVE event was unavailable because the connected identity owns the PR.
