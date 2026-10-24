# Engineering Report — mvp-tube-hot-shell-cold-r5

Generated: 2026-10-21T07:01:58.688758+00:00

## Executive summary

- Workflow status: **PARTIAL_RATING_ACCEPTED**
- Experimental ranking: **NOT_AVAILABLE**
- Production design approved: **false** (experimental MVP)

## Design conditions

- Target duty: 9500 W
- Max tube Δp: 1150 Pa
- Max shell Δp: 1180 Pa
- Tube side (HOT): 300.00 K @ 12.000000 kg/s
- Shell side (COLD): 298.15 K @ 20.000000 kg/s

## Candidate generation (Task168)

- Preflight status: VALID
- Candidates enumerated: 1
- Distinct geometries: 1

## Experimental mesh rating (native Task173)

- n=1: duty 45875.884128245187 W, energy residual 1.6E-10 W, terminal residual 2.4524E-9 K, Task172 evals 4580, wall 229.68 s
- n=2: duty 45868.2439988560625 W, energy residual 1.375E-10 W, terminal residual 6.11116E-9 K, Task172 evals 8055, wall 437.427 s
- n1/n2 duty delta: 7.6401293891245 W (0.01665391203745885172424227413 %), status PASS

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

R5: dynamic candidate selection, n=2 mesh + performance profile; R4 n=1 frozen for compare.

