# Executable Task Cards

Each file in this directory is a self-contained instruction package for a coding tool or engineer.

## Current task sequence

| Order | Task | Purpose |
|---:|---|---|
| 0 | [TASK-000](TASK-000-project-bootstrap.md) | Bootstrap repository, CI and engineering boundaries |
| 1 | [TASK-001](TASK-001-engineering-baseline.md) | Freeze scope, terminology and assumptions |
| 2 | [TASK-002](TASK-002-units-and-quantities.md) | Define unit-safe input and SI semantics |
| 3 | [TASK-003](TASK-003-property-service.md) | Build the fluid-property contract and CoolProp provider |
| 4 | [TASK-004](TASK-004-correlation-registry.md) | Register equations, evidence and applicability |
| 5 | [TASK-005](TASK-005-provenance-and-errors.md) | Build traceability, warnings and result hashing |
| 6 | [TASK-006](TASK-006-heat-balance.md) | Solve specification closure and energy balance |
| 7 | [TASK-007](TASK-007-double-pipe-correlations.md) | Implement validated single-phase tube/annulus models |
| 8 | [TASK-008](TASK-008-double-pipe-rating.md) | Rate a fixed double-pipe geometry |
| 9 | [TASK-009](TASK-009-double-pipe-sizing.md) | Enumerate and optimize manufacturable candidates |
| 10 | [TASK-010](TASK-010-report-and-api.md) | Expose results and generate a traceable report |

Use [TASK_TEMPLATE.md](TASK_TEMPLATE.md) for new task cards.

## Status convention

- `DONE`: merged and validated.
- `IN_PROGRESS`: assigned or represented by an open PR.
- `READY`: dependencies and acceptance criteria are complete.
- `BLOCKED`: a named dependency or decision is missing.
- `PLANNED`: not yet refined to Definition of Ready.

## Rules for coding agents

- Work on one task card at a time.
- Do not silently expand scope.
- Stop with a structured blocker when an engineering source or product decision is missing.
- Do not substitute a plausible equation for an approved equation.
- Include the task ID in branch names, commits and pull requests.
