# Engineering Report — mvp-multi-candidate-r10

Generated: 2026-10-21T13:44:10.985640+00:00

## Executive summary

- Workflow status: **PARTIAL_RATING_ACCEPTED**
- Experimental ranking: **NOT_AVAILABLE**
- Production design approved: **false** (experimental MVP)

## Design conditions

- Target duty: 9500 W
- Max tube Δp: 1150 Pa
- Max shell Δp: 1180 Pa
- Tube side (HOT): 299.70 K @ 12.000000 kg/s
- Shell side (COLD): 298.15 K @ 20.000000 kg/s

## Candidate generation (Task168)

- Preflight status: VALID
- Candidates enumerated: 4
- Distinct geometries: 4

## Multi-candidate experimental rating

- `5a73903d-3325-5604-be3b-ba5950299893`: mesh **NUMERIC_VALID**, duty 38387.018185484473 W, wall 226.229 s
- `f8b7482a-aa9f-5afc-8f0e-16f79caec9ee`: mesh **NUMERIC_VALID**, duty 38571.727035218992 W, wall 210.909 s
- Comparison: **EXPERIMENTAL_COMPARISON_AVAILABLE**; Ranking: **EXPERIMENTAL_RANKING_AVAILABLE**
- Preferred (experimental): `f8b7482a-aa9f-5afc-8f0e-16f79caec9ee`
- Hydraulic scope: **HYDRAULIC_REFERENCE_MODEL_PREVIEW**

## Experimental mesh rating (native Task173)

- n=None: duty 38387.018185484473 W, energy residual 2.0E-10 W, terminal residual 7.74694E-9 K, Task172 evals 4396, wall 226.229 s
- n=None: duty 38571.727035218992 W, energy residual 3.2E-10 W, terminal residual 5.54653E-9 K, Task172 evals 4220, wall 210.909 s

## Engineering warnings

- EXPERIMENTAL_MVP — not production design approval.
- FIV numeric limits not verified (FIV_NUMERIC_LIMIT_AUTHORITY=MISSING).
- R2A production certificate authority not verified for this workflow.
- Task167 configuration rule pack approval not claimed.

## Model applicability

- PURE_ORDINARY_WATER single-phase
- FIXED_TUBESHEET E-shell one shell pass
- Service envelope: Tube 12 kg/s, shell 20 kg/s, 298.15–300 K, 100–101325 Pa

## Notes

R10: two tube lengths at shared baffle spacing; 299.70 K tube / 298.15 K shell.

