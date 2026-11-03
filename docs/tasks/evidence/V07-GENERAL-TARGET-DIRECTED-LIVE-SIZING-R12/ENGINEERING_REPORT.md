# Engineering Report — mvp-target-directed-r12

Generated: 2026-10-21T15:59:26.300573+00:00

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
- Candidates enumerated: 35
- Distinct geometries: 35

## Multi-candidate experimental rating

- `f288aa61-0725-5942-a4fa-d5e16e1cd706`: rating **NUMERIC_VALID**, structure **ADMITTED**, Task174 **VALIDATED**, constraints **PRELIMINARY_CONSTRAINT_SATISFIED**, duty 29882.751196130037 W
  - Nominal area proxy: 45.424131098622137497350 m² (NOMINAL_TUBE_OUTER_AREA_PROXY)
- `071b9c82-f24a-53dd-b03b-a267f5f8d3c3`: rating **NUMERIC_VALID**, structure **ADMITTED**, Task174 **VALIDATED**, constraints **PRELIMINARY_CONSTRAINT_SATISFIED**, duty 32561.768761137928 W
  - Nominal area proxy: 52.994819615059160413575 m² (NOMINAL_TUBE_OUTER_AREA_PROXY)
- Comparison: **EXPERIMENTAL_COMPARISON_AVAILABLE**; Ranking: **EXPERIMENTAL_RANKING_AVAILABLE**; Conditional preference: **PREFERENCE_AVAILABLE**
- Conditional preferred (experimental): `f288aa61-0725-5942-a4fa-d5e16e1cd706`
- Pareto frontier: `['f288aa61-0725-5942-a4fa-d5e16e1cd706', '071b9c82-f24a-53dd-b03b-a267f5f8d3c3']`
- Hydraulic scope: **HYDRAULIC_REFERENCE_MODEL_PREVIEW**
- Task168 preflight dispositions in `candidates` are enumeration-only; see per-candidate STRUCTURAL_STATUS / RATING_STATUS above for rated paths.

## Experimental mesh rating (native Task173)

- n=None: duty 29882.751196130037 W, energy residual 2.4E-10 W, terminal residual 5.2227E-9 K, Task172 evals 4079, wall 212.775 s
- n=None: duty 32561.768761137928 W, energy residual 7.2E-11 W, terminal residual 2.39445E-9 K, Task172 evals 5182, wall 285.459 s

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

R12: area-prioritized search; exclude R10 baseline geometries from new live n=1 ratings.

