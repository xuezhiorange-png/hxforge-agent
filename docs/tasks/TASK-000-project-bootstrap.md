# TASK-000 — Project bootstrap

**Status:** DONE  
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

- [x] Repository installs on Python 3.11 and 3.12.
- [x] Ruff, mypy, pytest and dependency audit pass.
- [x] README links to specifications, backlog and task cards.
- [x] No temporary, licensed, confidential or generated files are committed.
- [x] Demonstration calculations are explicitly marked preliminary.
- [x] Bootstrap PR is merged into `main`.

## Test plan

Run `ruff check .`, `mypy`, `pytest --cov=hexagent` and `pip-audit` in CI.

## Deliverables

Repository scaffold, executable task system and merged PR #1.
