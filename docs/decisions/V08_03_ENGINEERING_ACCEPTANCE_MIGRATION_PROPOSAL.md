# V08-03 engineering acceptance migration proposal (not authorized)

Status: **proposal only** — `PRODUCTION_CONTRACT_CHANGE_AUTHORIZED=false`.

## Dual-layer architecture

| Layer | Scope | This repository |
| --- | --- | --- |
| **L1 Production numerical** | Task172 C-ULP (three residuals, ratio ≤ 1), Task173 terminal T/H (`TERMINAL_TOLERANCE_K` + cp·scale + ULP), mesh identity, production `validate_candidate_rating` | **Unchanged** — no tolerance edits in V08-03 |
| **L2 Engineering physical** | Duty ≥ target, dP envelopes, energy plausibility, mesh N1/N2/N4 posture, property TP→PH audit, wall order, negative controls | Prototype evaluators under `prototypes/v08_thermal_rating/engineering_*` |

## Proposed contract fields (for future authorized change only)

1. **Documented error budget block** on rating results (provenance), not wider gates by default:
   - `task172_max_culp_ratio` vs ceiling `1.0`
   - `task173_terminal_residual_h_j_kg` vs `allowed_h` from `_terminal_tolerance_pass`
   - `mesh_level_gates` N1/N2/N4
   - `outer_shooting_status` (e.g. PRECISION_FLOOR)
2. **Optional engineering endorsement flag** — distinct from `NUMERIC_VALID`; requires explicit engineer role; never auto-set from L2 prototype.

## Derivation (not back-solved from current failure)

- Task173 enthalpy allowance: `cp_inlet * 1e-8 K + ulp(h)` — **do not** set allowance to `4.76e-5 J/kg`.
- Task172: per-cell bounds from production `_eval_trial`; no single merged tolerance.

## Positive / negative examples

- **Positive (frozen 330 kW):** N1/N2 ACCEPTED, duty ~395 kW, dP within envelope, terminal h residual ~5% above production `allowed_h`, propagation ~1e-10 J/kg.
- **Negative:** +15% duty imbalance or inverted wall order → L2 evaluator BLOCKED (see `run_negative_controls`).

## V07 Golden

No golden changes until authorized contract version bump and engineer sign-off.

## Risks

- Misreading L2 PASS as production VALIDATED — **forbidden** (`ENGINEERING_ACCEPTANCE` stays BLOCKED).
- Nozzle velocities unresolved; second hydraulic geometry not admitted.

## Rollback

Do not ship tolerance changes; retain L1-only production path.