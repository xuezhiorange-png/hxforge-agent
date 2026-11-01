# R27E final engineering audit (330 kW experimental MVP)

TASK_ID: `V07_R27E_PHYSICAL_MODEL_ISOLATION_AND_REGRESSION_FINAL_ACCEPTANCE`

PR **#311** remains **Draft**. This document records verified evidence only; it is not a manufacturing release.

## Design envelope (unchanged)

- Duty target: Q ≥ 330 kW
- Tube side: 310 K, 12 kg/s; shell side: 295 K, 20 kg/s
- Internal Δp budgets: tube ≤ 1150 Pa, shell ≤ 1180 Pa
- Nozzle velocity band: 1–3 m/s
- Three independent K assumptions remain **unverified** for production

## Search space structure

- 48 enumerated experimental candidates (R27D cooptimization structure preserved)
- 12 Task174-ready distinct geometries
- 8 candidates with confirmed full mesh rating on R27E (7 original reference set minus two enthalpy regressions, plus recovered `09dac82a`)

## Confirmed rating highlights

| Candidate | Role | Verified outcome |
|-----------|------|------------------|
| `09dac82a` | R27D N1 non-convergence recovery | Full mesh ~380.6 kW; internal Δp ~782/955 Pa; **full path infeasible** under all three K nozzle budgets |
| `9c4b84db` | low_loss band | R27D: critical shell margin ~0.0005 Pa; **R27E: N1 enthalpy-domain block** — not a robust design |
| mid_band | — | **0** confirmed feasible solutions in current evidence |

## Regression acceptance (seven R27D reference candidates)

Authentic baseline: R27D PR #310 @ `e320aaf5840812eafe86a0e7d6fef97bf8062544`, captured in isolated worktree (`tests/fixtures/r27e_r27d_seven_reference_baseline.json`).

- **5 / 7** maintain `FULL_RATING_CONVERGED` on R27E with **zero tolerance violations** vs R27D on duty, outlets, energy, closure, and Δp.
- **2 / 7** (`9c4b84db`, `7357afdf`) **fail regression**: R27E N1 stops with `enthalpy_domain_exit` while R27D history converged — not explained as benign numeric drift; **final seven-candidate regression is FAIL**.

## Four 0.65 m shell blocked candidates

Diagnostics distinguish **Task026 temperature-sweep transition** (first transition ~308.1 K, Re ~2989 at inlet turbulent Re ~3102) from **actual grid correlation blocking** (`THERMAL_CORRELATION_UNAVAILABLE` on N1 for the 0.65 m trio). `c20fb684` retains R27D `original_r27d_blocker` enthalpy evidence; CoolProp PH probe ≠ solver admitted enthalpy domain.

## Operational constraints honored

No Golden/R11/main edits, no K or correlation changes, no full 48-candidate re-search, no Ready/Merge/Deploy.
