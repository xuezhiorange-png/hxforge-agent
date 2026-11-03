# Engineering Report — mvp-tube-hot-shell-cold-r4

Generated: 2026-10-20T17:20:09.537037+00:00

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

R4: tube_side=hot equipment stream, shell_side=cold equipment stream; C3 reference geometry; unified positive-duty cell + n=1 mesh evidence.

