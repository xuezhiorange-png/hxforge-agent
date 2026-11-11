# V08-03 Numerical Precision Architecture Decision

**TASK_ID:** `V08_03_NUMERICAL_PRECISION_ARCHITECTURE_DECISION`  
**PR:** 325 (Draft)  
**HEAD:** `52e6684ac6ede6f80834c1fe1e5829d92dfcba87`  
**ENGINEERING_ACCEPTANCE:** BLOCKED (unchanged)

## Unified best point (single production gate)

| Field | Value |
|-------|-------|
| q / Twi / Two (K) | 152845.44912345504 / 308.26850752129053 / 306.52793869715185 |
| r1 / r2 / r3 (W) | -2.2118911147117615e-09 / -7.683411240577698e-09 / -6.231130100786686e-08 |
| bound1/2/3 (W) | 2.2376192758449283e-09 / 1.0094884374834469e-08 / 2.778638714560043e-09 |
| R1 / R2 / R3 ratio | 0.9885019934307404 / 0.7611192912453429 / 22.425117983621323 |
| **MAX ratio** | **22.425117983621323** (check 22.425117983621323) |
| request_hash | `ad7dc6e2eed9472cf64129916291b116a4ba5792fa4d18c1ebdcec0b11db7fca` |
| snapshots | `{'tube_bulk': '22c0c4b5dc3d0366353bbaf9054982b615b179be02f71013cbf0b0cd7fc5b587', 'shell_bulk': 'ea433eb18151b169b6652e109fa45fc82f8a1cde5536c5bece0380750ed30ec5'}` |
| Task172 gate | BLOCKED |

Candidate label: `5b_refinement_from_bracket_root`. Evidence from one `eval_trial_residual_gate` triple only.

## Float bracket scope (scalar roots only)

- **Validity:** `True` — adjacent binary64 endpoints with opposite-sign scalar residuals.
- Does **not** prove exhaustion of all `(q,Twi,Two)` representable triples.

## Error source isolation (Cell 0, candidate e1)

| Source | r3 impact vs bound3 (ratio) |
|--------|-------------------------------|
| Arithmetic (Decimal, frozen Gi/Go/Rwall) | 0.01945144381613445 |
| Property neighbor (Twi +1 ULP) | 0.0 |

Full JSON: `/opt/cursor/artifacts/v08_03_numerical_precision_architecture_decision.json`

## Options (design only — no production change this round)

### A — Higher-precision residual kernel
Keep CoolProp interface; extend precision in Task172 `_eval_trial` accumulation (not solver).

### B — Property / state pipeline
HTC and snapshot quantization dominate; requires new property evaluation contract (not `float` swap alone).

### C — Layered acceptance re-argument
Keep physics; study whether nanowatt ULP bounds match binary64 + property uncertainty.

## Decision

**ARCHITECTURE_DECISION = C**

**RECOMMENDED_CHANGE:** Nanowatt C-ULP bounds exceed residual magnitude at verified frozen snapshots; engineered layered acceptance (ULP / energy / property uncertainty) review required

**PRODUCTION_CONTRACT_CHANGE_REQUIRED:** True

## Risks and boundary

- No ULP tolerance change, no production solver replacement, no V08-04.
- V08-03 engineering acceptance remains BLOCKED until full Rating under authorized contract.

## CI

- **#1572 root cause:** missing `test_float_lattice_bracket.py` in manifest + Ruff SIM102 (fixed).
