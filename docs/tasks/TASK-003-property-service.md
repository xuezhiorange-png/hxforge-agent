# TASK-003 — Fluid property service

**Status:** DONE  
**Milestone:** M1  
**Priority:** P0  
**Depends on:** TASK-001, TASK-002  
**GitHub Issue:** #6  
**Branch:** `codex/task-003-property-service`  
**Final approval:** `docs/reviews/TASK-003-final-approval.md`

## Objective

Provide a deterministic, injectable fluid-property service with CoolProp as the default backend and a contract suitable for future REFPROP and enterprise data.

## Acceptance criteria

- [x] Injectable property-provider protocol and typed results.
- [x] TP and PH query paths.
- [x] Pure-fluid saturation queries by pressure and temperature.
- [x] Water, Air, R134a and R717 support and regression coverage.
- [x] Explicit DEF reference-state policy and runtime mutation guard.
- [x] Required PH reference-state identity in the public schema.
- [x] Structured, strict and versioned result/error serialization.
- [x] Deterministic cache keys and cache inspection.
- [x] Explicit mixture capability boundary.
- [x] Stable public errors after explicit range checks.
- [x] Validation provenance for regression, support allowlist and unvalidated opt-in.
- [x] Rounds 1–4 engineering review resolved.
- [x] GitHub CI passes on Python 3.11 and 3.12.
- [x] Engineering review complete.

## Verification

- Reviewed code head: `44e7516e98a153623c6e28bc430ecd54439ec9f0`.
- Final approval record: `docs/reviews/TASK-003-final-approval.md`.
- Code CI run: `27905712482` — success.
- Finalization CI run: `27906055325` — success.
- Test suite: 191 passed.

## Scope boundary

This task does not add heat-balance equations, exchanger correlations, geometry selection, costing, mechanical design or downstream two-phase exchanger solvers.
