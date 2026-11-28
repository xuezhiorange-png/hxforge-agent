# V08-03 Task173 enthalpy authority recovery (prototype closeout)

**BVP route:** `STOP` — no Block Gauss–Seidel extension.

## Isolated experiment (this task)

1. **Trace** (`enthalpy_precision_trace_v08.py`) — per-cell Decimal face enthalpies, q/m prediction error, P-H roundtrip delta, shell cold-inlet vs authority enthalpy, terminal residuals.
2. **Authority audit** (`enthalpy_authority_experiment_v08.py`) — at each cell-mid enthalpy, production `_state_from_enthalpy` must stay consistent with authority input; otherwise dual-track would **BLOCK** (no fake energy closure).
3. **Validation** — reuse isolated outer shooting only (no new solver, no production `src` edits).

## Decisions

- **A — ENTHALPY_AUTHORITY_RECOVERED:** N4 passes original Task172, terminal, energy, and authority audit.
- **B — NUMERICAL_REPRESENTATION_INSUFFICIENT:** otherwise; pursue `TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION` as a **separate** production architecture change (not authorized in this task).

## Next architecture work

- Decimal authoritative enthalpy propagation vs CoolProp property snapshots
- P-H vs Decimal precision at outer boundary
- Unchanged Task172 / C-ULP / terminal tolerances until contract review

## Closeout (frozen case `9277ebb8-…`, geometry `1d5cfed5…`)

**NUMERICAL_DECISION=B — NUMERICAL_REPRESENTATION_INSUFFICIENT**

| Field | Result |
| --- | --- |
| ISOLATED_N1 / N2 / N4 | ACCEPTED / ACCEPTED / BLOCKED |
| N4 outer | `PRECISION_FLOOR` (`BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED`) |
| N4 Task172 / terminal | BLOCKED / BLOCKED |
| N4 duty | ~395277 W (energy balance PASS vs experimental floor) |
| Shell cold-inlet face − authority | ~−13173 J/kg |
| Per-face q/m propagation residual (max cum.) | ~2.3×10⁻¹⁰ J/kg |
| Authority vs `_state_from_enthalpy` | BLOCKED (`_Stage3Failure` all tube cells; inlet face gap) |
| Defect attribution (heuristic) | `local_q_root_or_other` (not sole CoolProp/Decimal roundtrip) |

Authority split experiment **does not** recover original N4 acceptance without contract change. Next step is separate engineering acceptance / numerical representation review (`ENGINEERING_ACCEPTANCE=BLOCKED`).