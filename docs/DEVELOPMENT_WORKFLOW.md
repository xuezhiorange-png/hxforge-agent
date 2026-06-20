# HXForge Development Workflow

## 1. Purpose

This document defines how a coding agent or engineer executes work in HXForge. The repository uses task-driven development: one task card, one short-lived branch, one focused pull request.

## 2. Required reading order

Before coding, read:

1. `AGENTS.md`
2. `docs/MASTER_DEVELOPMENT_SPEC.md`
3. `docs/TASK_BACKLOG.md`
4. the selected file under `docs/tasks/`
5. any relevant ADR and engineering references

## 3. Branch and commit convention

- Branch: `codex/task-<id>-<short-name>` or `feat/task-<id>-<short-name>`
- Commit: Conventional Commits, for example `feat(units): add SI quantity normalization`
- Pull request: one task unless the task card explicitly allows a grouped bootstrap change
- Main branch: protected; no direct feature pushes

## 4. Mandatory pre-coding response

The coding tool must state:

- task ID and objective;
- assumptions and unresolved engineering questions;
- files expected to change;
- implementation sequence;
- test plan;
- risks, especially any numerical or standards-related risk.

Do not start by generating code without this response.

## 5. Implementation rules

1. Engineering equations are deterministic functions, never LLM-generated values.
2. Public inputs carry units; calculations use SI internally.
3. Correlations require ID, source, version, validity envelope and uncertainty.
4. Unsupported scope returns a structured error or `NOT_IMPLEMENTED`.
5. No silent extrapolation, convergence suppression or fallback constants.
6. Property, standards, cost and vendor data use injectable providers.
7. Tests are added before or together with calculation changes.
8. Golden-case changes require an explicit numerical explanation.
9. Licensed standards, REFPROP files, confidential catalogs and customer data stay outside Git.
10. Reports must preserve warnings and provenance; narrative must not hide them.

## 6. Definition of Ready

A task is ready when:

- scope and non-goals are explicit;
- dependencies are complete;
- engineering sources are identified or source collection is itself the task;
- inputs and outputs are defined;
- acceptance criteria are measurable;
- test cases and tolerances are specified;
- no unresolved product decision blocks implementation.

## 7. Definition of Done

A task is done when:

- acceptance criteria pass;
- Ruff, mypy and pytest pass;
- unit, boundary, invalid-input and regression tests exist;
- provenance and warnings are serialized where applicable;
- documentation and examples are updated;
- API changes are versioned or backward-compatible;
- the PR explains assumptions, numerical changes and residual risks;
- no temporary, generated, licensed or confidential files are committed.

## 8. Review sequence

1. Software review: architecture, typing, API and maintainability.
2. Engineering review: equations, applicability, units and physical behavior.
3. Regression review: benchmark and Golden-case differences.
4. Product review: workflow, output completeness and user-facing warnings.

## 9. Task completion response

The coding tool must report:

- changed files;
- implemented behavior;
- test commands and results;
- numerical validation results;
- assumptions and limitations;
- any deferred item;
- recommended next task ID.
