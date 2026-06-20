# TASK-010 — Double-pipe API and traceable report

**Status:** READY  
**Milestone:** M2  
**Priority:** P1  
**Depends on:** TASK-005, TASK-009

## Objective

Expose validation, rating and sizing through versioned APIs and produce a standard report that preserves assumptions, warnings, alternatives and calculation traceability.

## In scope

- Case validation, rating and sizing endpoints.
- Idempotency key and run ID.
- Structured candidate response.
- HTML report and print-ready PDF adapter boundary.
- Summary, inputs, heat balance, geometry, performance, pressure drop, materials placeholder, cost placeholder, warnings and provenance appendix.

## Expected files

- `src/hexagent/api/cases.py`
- `src/hexagent/api/double_pipe.py`
- `src/hexagent/reporting/service.py`
- `src/hexagent/reporting/templates/double_pipe.html`
- `tests/integration/test_double_pipe_api.py`
- `tests/golden/reports/`

## Acceptance criteria

- [ ] API schemas are documented in OpenAPI.
- [ ] Same idempotency key and input do not create duplicate runs.
- [ ] Report values reconcile with JSON results.
- [ ] Blocking warnings are prominent and cannot be hidden by narrative.
- [ ] Preliminary/non-compliant status is displayed on every page.
- [ ] Provenance appendix identifies formula and property versions.

## Test plan

API schema, invalid inputs, deterministic response, report snapshot, warning rendering and trace-link integrity.
