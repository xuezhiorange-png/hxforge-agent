# V08-03 numerical acceptance contract review

## Evidence snapshot (frozen `9277ebb8…`, 330 kW context VALID)

| Bucket | Magnitude | Role |
| --- | --- | --- |
| Cell face q/m propagation (cumulative) | ~2.29×10⁻¹⁰ J/kg | Cannot explain N4 block |
| Shell inlet terminal residual h | ~4.76×10⁻⁵ J/kg | Exceeds production `allowed_h` (~cp×10⁻⁸ + ULP) |
| TP→PH @ 295 K (Water mapping) | PASS, ΔH/ΔT recorded | Property path credible at inlet |
| Isolated N1/N2 | ACCEPTED | Mesh coarse levels close |
| N4 outer | PRECISION_FLOOR | Shooting plateau, not face propagation |
| Production Task173 | BLOCKED | Full rating chain |

## Contract limits (production, unchanged)

- `TERMINAL_TOLERANCE_K = 1×10⁻⁸ K` (`models.py`).
- Terminal pass: `0 ≤ residual_T ≤ TERMINAL_TOLERANCE_K + ulp(T)` and `0 ≤ residual_H ≤ cp·TERMINAL_TOLERANCE_K + ulp(h_cold)` (`service._terminal_tolerance_pass`).
- Task172 local gates: separate C-ULP three-residual contract (not replaced by energy balance).

## Decision **B**

Original Task173 terminal enthalpy gate plus N4 outer precision floor cannot be met for this candidate under **current** binary64 outer shooting and production property/state identity, without an **authorized** contract review.

**Not causal:** decimal face enthalpy propagation at ~10⁻¹⁰ J/kg (orders below terminal residual).

**Required next step (no prototype tolerance edits):** formal numerical acceptance rule review with independent error budget and engineering sign-off. Path A remains available only after a scoped production representation fix with reproducible N4 ACCEPTED + terminal PASS evidence.

## Engineering acceptance

Remains **BLOCKED** (nozzle velocities unresolved, second hydraulic geometry missing, production Task173 not VALIDATED).