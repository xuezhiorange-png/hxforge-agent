# Engineering Report — mvp-tube-hot-shell-cold-r9

Generated: 2026-10-21T10:49:13.523237+00:00

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
- Candidates enumerated: 1
- Distinct geometries: 1

## Experimental constraint preview

- Capacity preview: **MEETS_TARGET**
- Δp preview: **WITHIN_LIMITS**
- Duty constraint: SATISFIED
- Tube Δp constraint: SATISFIED
- Shell Δp constraint: SATISFIED
- Task174 hydraulic status: EVALUATED
- Production design eligible: **false**

## Experimental mesh rating (native Task173)

- n=1: duty 38387.018185484473 W, energy residual 2.0E-10 W, terminal residual 7.74694E-9 K, Task172 evals 4396, wall 250.37 s

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

R9: new CLI E2E case — tube inlet 299.70 K, shell 298.15 K.

