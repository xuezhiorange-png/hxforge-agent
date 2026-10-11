# AGENTS.md

This repository contains engineering calculation software. Treat every numerical result as safety-relevant.

## Mandatory workflow

1. Read `docs/MASTER_DEVELOPMENT_SPEC.md`.
2. For Cursor Cloud runs: read `docs/CURSOR_CLOUD_PERSISTENCE.md`, append `docs/HXFORGE_RESULT_INDEX.jsonl` after push, return the delivery block in §六.
3. Work from one GitHub Issue.
4. State the files, assumptions and test plan before editing.
5. Add or update tests before changing an engineering equation.
6. Run all quality gates before requesting review.
7. Never change golden results without an explicit explanation.

## Engineering constraints

- Do not calculate engineering results with an LLM.
- Do not invent correlations, constants, material limits, standard clauses or vendor data.
- Do not silently extrapolate.
- Do not use unitless public inputs.
- Do not suppress convergence, phase, property or applicability errors.
- Do not claim code compliance unless a licensed rule pack has completed and an authorized engineer has reviewed the result.
- Every correlation must have an ID, source, version, validity envelope and uncertainty.
- Every public result must include warnings and provenance.

## Coding constraints

- Python public APIs require type hints.
- Prefer pure functions in the engineering kernel.
- Keep I/O outside correlations and solvers.
- Use dependency injection for property, cost and standards providers.
- No network calls inside deterministic calculations.
- Avoid global mutable state.
- Return structured errors.
- Keep backward-compatible schemas or version the API.
