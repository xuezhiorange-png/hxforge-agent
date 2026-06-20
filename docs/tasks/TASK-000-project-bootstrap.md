# TASK-000 — Project bootstrap

**Status:** IN_PROGRESS  
**Milestone:** M0  
**Priority:** P0  
**Depends on:** None

## Objective

Create a reviewable repository foundation that enforces deterministic engineering calculations, typed interfaces, automated checks and task-driven development.

## In scope

- Python `src` layout, FastAPI skeleton and domain models.
- Unit and property-provider boundaries.
- Preliminary double-pipe architecture demonstrator.
- CI, Dockerfile, templates, CODEOWNERS and documentation.
- Task backlog, workflow and executable task cards.

## Out of scope

- Production-ready heat-exchanger design.
- Detailed pressure-vessel compliance.
- Validated two-phase, CFD or FEA models.

## Acceptance criteria

- [ ] Repository installs on Python 3.11 and 3.12.
- [ ] Ruff, mypy, pytest and dependency audit pass.
- [ ] README links to specifications, backlog and task cards.
- [ ] No temporary, licensed, confidential or generated files are committed.
- [ ] Demonstration calculations are explicitly marked preliminary.
- [ ] Bootstrap PR is reviewable and mergeable.

## Test plan

Run `ruff check .`, `mypy`, `pytest --cov=hexagent` and `pip-audit` in CI.

## Deliverables

Repository scaffold and Draft PR #1.
