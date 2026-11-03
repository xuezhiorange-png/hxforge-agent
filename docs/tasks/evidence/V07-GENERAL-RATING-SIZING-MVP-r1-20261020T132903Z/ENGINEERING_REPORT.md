# Engineering Report — mvp-district-heating-water-water-r1

Generated: 2026-10-20T13:29:05.037724+00:00

## Executive summary

- Workflow status: **PARTIAL_RATING_BUDGET**
- Experimental ranking: **NOT_AVAILABLE**
- Production design approved: **false** (experimental MVP)

## Design conditions

- Target duty: 9500 W
- Max tube Δp: 1150 Pa
- Max shell Δp: 1180 Pa
- Cold side: 299.15 K @ 12.000000 kg/s
- Hot side: 298.65 K @ 20.000000 kg/s

## Candidate generation (Task168)

- Preflight status: VALID
- Candidates enumerated: 3
- Distinct geometries: 3

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

New MVP case: 9.5 kW duty (not 10 kW validation default), three tube lengths at 0.8 m shell. Candidate IDs/hashes are generated live via Task168 (not R22 pins).

