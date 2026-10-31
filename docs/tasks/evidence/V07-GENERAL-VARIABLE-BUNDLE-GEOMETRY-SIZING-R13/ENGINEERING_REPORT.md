# Engineering Report — mvp-variable-bundle-r13

Generated: 2026-10-22T06:44:32.977475+00:00

## Executive summary

- Workflow status: **PARTIAL_RATING_ACCEPTED**
- Experimental ranking: **EXPERIMENTAL_RANKING_AVAILABLE**
- Production design approved: **false** (experimental MVP)

## Design conditions

- Target duty: 9500 W
- Max tube Δp: 1150 Pa
- Max shell Δp: 1180 Pa
- Tube side (HOT): 299.70 K @ 12.000000 kg/s
- Shell side (COLD): 298.15 K @ 20.000000 kg/s

## Candidate generation (Task168)

- Preflight status: VALID
- Candidates enumerated: 64
- Distinct geometries: 16

## Multi-candidate experimental rating

- `ce66b1a2-1f75-5901-bd7f-6a9ee5cd3cfe`: rating **NUMERIC_VALID**, structure **ADMITTED**, Task174 **VALIDATED**, constraints **PRELIMINARY_CONSTRAINT_FAILED**, duty 32328.8461907676175 W
  - Nominal area proxy: 56.196652307781537694350 m² (NOMINAL_TUBE_OUTER_AREA_PROXY)
- `a409a550-4d1d-5b71-b3f5-0f1b665e2fe5`: rating **NUMERIC_VALID**, structure **ADMITTED**, Task174 **VALIDATED**, constraints **PRELIMINARY_CONSTRAINT_SATISFIED**, duty 32528.427903428549 W
  - Nominal area proxy: 60.505660791445297773150 m² (NOMINAL_TUBE_OUTER_AREA_PROXY)
- Comparison: **EXPERIMENTAL_COMPARISON_AVAILABLE**; Ranking: **EXPERIMENTAL_RANKING_AVAILABLE**; Conditional preference: **PREFERENCE_AVAILABLE**
- Conditional preferred (experimental): `a409a550-4d1d-5b71-b3f5-0f1b665e2fe5`
- Pareto frontier: `['a409a550-4d1d-5b71-b3f5-0f1b665e2fe5']`
- Hydraulic scope: **HYDRAULIC_REFERENCE_MODEL_PREVIEW**
- Task168 preflight dispositions in `candidates` are enumeration-only; see per-candidate STRUCTURAL_STATUS / RATING_STATUS above for rated paths.

## Experimental mesh rating (native Task173)

- n=None: duty 32328.8461907676175 W, energy residual 4.0E-10 W, terminal residual 6.6676E-9 K, Task172 evals 4375, wall 255.835 s
- n=None: duty 32528.427903428549 W, energy residual 2.11E-10 W, terminal residual 5.31757E-9 K, Task172 evals 4419, wall 249.635 s

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

R13: variable shell ID drives Task021 tube count; Task172 not C3-bound.

