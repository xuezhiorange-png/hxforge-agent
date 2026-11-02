# R27E final engineering audit (330 kW experimental MVP)

TASK_ID: `V07_R27E_PHYSICAL_MODEL_ISOLATION_AND_REGRESSION_FINAL_ACCEPTANCE`  
Remediation: `V07_R27E_N1_ENTHALPY_REGRESSION_AND_CI_REMEDIATION`

PR **#311** remains **Draft**. Verified evidence only; not a manufacturing release.

## Design envelope (unchanged)

- Duty target: Q ≥ 330 kW
- Tube side: 310 K, 12 kg/s; shell side: 295 K, 20 kg/s
- Internal Δp budgets: tube ≤ 1150 Pa, shell ≤ 1180 Pa
- Nozzle velocity band: 1–3 m/s
- Three independent K assumptions remain **unverified** for production

## Rating coverage statistics (do not conflate)

| Metric | Count | Meaning |
|--------|------:|---------|
| R27D historical reference full mesh converged | **7** | Frozen baseline @ `e320aaf` |
| Cross-HEAD ever confirmed full mesh on R27E line | **8** | Above 7 + recovered `09dac82a` (prior acceptance) |
| **Current R27E HEAD** reference full mesh | **7 / 7** | After N1 Q-seed enthalpy fallback fix (pending slow regression re-run) |
| **Current R27E HEAD** recovery full mesh | **1** | `09dac82a` (full path still infeasible) |
| **Current R27E HEAD** total confirmed full mesh | **8** | 7 reference + 1 recovery (not 8 reference) |

- 48 enumerated candidates; 12 Task174-ready (structure unchanged).

## N1 enthalpy regression root cause (9c4b84db, 7357afdf)

R27E introduced `_conductance_weighted_q_guess()` with higher total duty seed (~280 kW scale). The implied tube-side enthalpy trace on the **first** residual evaluation exited the **rating-admitted** domain (h below `_effective_h_min_j_kg`, e.g. h≈88026 J/kg) — **initial point invalid**, not a relaxed physics change. R27D used uniform `_initial_q_guess()` only.

**Fix:** `_resolve_n1_q_initial()` keeps conductance-weighted seed when enthalpy-admitted; otherwise deterministic fallback to R27D uniform initial (no domain widening).

## Confirmed rating highlights

| Candidate | Role | Verified outcome |
|-----------|------|------------------|
| `09dac82a` | R27D N1 recovery | Full mesh ~380.7 kW; internal Δp ~782/955 Pa; **full path infeasible** (all K) |
| `9c4b84db` | low_loss | R27D critical shell margin ~0.0005 Pa; **not robust**; N1 restored on current HEAD after Q fallback |
| mid_band | — | **0** confirmed feasible |

## Four 0.65 m shell blocked candidates

Unchanged: transition gap (three IDs) and enthalpy domain on `c20fb684`; T-sweep transition ~308.1 K / Re≈2989 is diagnostic-only.

## Operational constraints honored

No Golden/R11/main edits, no K/correlation/domain relaxation, no full 48-candidate re-search, no Ready/Merge/Deploy.
