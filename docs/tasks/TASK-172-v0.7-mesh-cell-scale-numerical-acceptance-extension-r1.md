# TASK-172 v0.7 Mesh-Cell-Scale Numerical Acceptance Extension R1

**Task:** `TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_R1`
**Result:** `MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_CANDIDATE_COMPLETED`
**Predecessor:** `28770ce03a1a21496cfd5b0ea4ba8e32e78328ff`

## Decision

The frozen R94 TRF solver controls reproduced the R95 M01, N=8 cell exactly.
The R95 cell is valid and solver termination succeeds, but the R94 `C_round=0.5`
residual acceptance policy rejects its inner-film residual. The same residual
policy issue remains under both predeclared tighter-`xtol` candidates. A
versioned acceptance-policy candidate with `C_round=1.0` passes the R95
diagnostic and all 72 H01-H08 dyadic scale-training cases without changing any
R94 solver control or increasing observed solver work.

This is a method-sensitivity-derived project acceptance-policy candidate, not a
formal IEEE-754 error bound and not production authority. It is
`PROPOSED_AUTHORITY_REVIEW_PENDING`. R94 and R95 remain immutable; the R95 mesh
qualification is not resumed by this gate.

## Frozen R95 diagnostic replay

The diagnostic is the already known M01 primary-sequence cell with
`N=8`, exact interval `[1/4, 3/8]`, and scale fraction `1/8`. Its local solve
has valid state-domain checks, no mesh mapping error, no property-domain error,
and no solver resource exhaustion. The TRF solver reports success/status 3,
`nfev=4`, and 16 residual callbacks. Under R94 `C_round=0.5`,
`|r_i|=2.0605739337042905e-13 W` exceeds its `1.699451104588476e-13 W`
candidate bound by `1.2124938035232622x`; the other two residuals pass.
Therefore this is an acceptance-scale applicability failure, not a mesh
threshold failure or solver termination failure.

The P0 residuals, bounds, seed, solution, status, evaluation count, and callback
count match the frozen R95 diagnostic exactly. P1 doubles the residual-specific
acceptance bounds and reduces the diagnostic's maximum ratio to
`0.6062469017616311`; it leaves the computed state and residuals unchanged.

## Exact support-scale identity

For each fixed local physical state, the scale transform is:

```text
A_i,f = f A_i,1
A_o,f = f A_o,1
R_wall,f = R_wall,1 / f
G_i,f = f G_i,1
G_wall,f = f G_wall,1
G_o,f = f G_o,1
```

With the same bulk states, pressure, Reynolds number, and admitted
correlation/property branches, the exact constitutive solution obeys:

```text
q_hc,f = f q_hc,1
T_wall_inner,f = T_wall_inner,1
T_wall_outer,f = T_wall_outer,1
```

This remains true for the active tube C3 and shell J_mu callbacks because the
exact wall temperatures are invariant under this pure area/resistance scaling.
The identity is a scale-oracle contract, not a production mesh or a physical
case.

## Experiment design and results

The input matrix was frozen before numerical execution at canonical hash
`431967d2f7cbdb78027472bbabe0ba5b7edfbb328e6c5144f9acdb7e4323f6a8`. It uses
the existing R94 H01-H08 cases at exact fractions `1, 1/2, 1/4, 1/8, 1/16,
1/32, 1/64, 1/128, 1/256`. Each of the four predeclared policies was evaluated
on all 72 cases. Eight f=1 reference solutions were independently reproduced
with the existing validation-only scalar oracle. Twelve additional scalar
oracle replays at dyadic fractions confirmed the scale identity; no production
scalar method was selected.

| Candidate | C_round | xtol | Training accepted | Max training residual/bound | Max q oracle error (W) | Max wall error (K) | Max nfev / callbacks | R95 diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| P0 frozen R94 | 0.5 | 1e-12 | 72/72 | 0.6856426949542228 | 2.9345414986892138e-12 | 5.684341886080802e-14 | 4 / 16 | fail, 1.2124938035232622 |
| P1 acceptance extension | 1.0 | 1e-12 | 72/72 | 0.3428213474771114 | 2.9345414986892138e-12 | 5.684341886080802e-14 | 4 / 16 | pass, 0.6062469017616311 |
| P2 tighter xtol | 0.5 | 1e-13 | 72/72 | 0.6856426949542228 | 2.9345414986892138e-12 | 5.684341886080802e-14 | 4 / 16 | fail, 1.2124938035232622 |
| P3 tighter xtol | 0.5 | 1e-14 | 72/72 | 0.6857280220412423 | 2.533084852984757e-12 | 5.684341886080802e-14 | 5 / 20 | fail, 1.2124938035232622 |

P95 in the table is the nearest-rank 95th percentile of the per-case maximum
residual/bound ratio. The P1 scale-training result matrix has canonical hash
`f8cdc67fd28aac5baf85ca21a3b4eb1edc02401aef522eebcf66b9c53faa00d1`.
All candidate scale matrices had finite scale-oracle errors, valid final
domains, and zero resource-cap hits. P1 has the same solver work and observed
oracle errors as P0/P2; P3 uses more evaluations and still fails the mandatory
R95 diagnostic.

The predeclared selection policy therefore selects P1: it preserves the
reviewed R94 solver controls, passes every required scale case and the known
diagnostic, and does not add solver work. `C_round=1.0` was not pre-authorized;
it was selected only from this experiment. The policy is empirical and
project-specific; it is not presented as a formal floating-point theorem.

## Versioned candidate and holdout freeze

The candidate is
`V07-T172-NUMERICAL-PROFILE-MESH-CELL-SCALE-EXTENSION-R1` with P1 settings.
All R94 solver settings remain unchanged. The effective candidate supersedes
only the residual-acceptance multiplier for mesh-cell-scale applicability;
R94's original `C_round=0.5` record is not edited. Independent authority review
is pending, so the numerical canonical blocker remains closed as previously
reviewed, while mesh-cell-scale applicability review remains pending.

A separate K01-K05 future holdout is frozen for fractions `1/3, 1/6, 1/12,
1/24, 1/48, 1/96` (30 cases total). Its canonical hash is
`9c0d41a78836a24b55d21ff76ccb88b1c83d3df291f310cb106e9c653463f60a`; its
selected-profile hash is
`029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6`. The
holdout is frozen and **was not executed**; it requires independent review
before any future run.

## Preserved boundaries

- R94, R95, and all R1-R95 historical payloads are immutable.
- No mesh threshold, termination threshold, or discretization-error estimator
  was selected. No complete R95 mesh matrix was rerun.
- `MESH-CONVERGENCE-QUALIFICATION` remains the sole parent TASK172 blocker;
  blocker count remains 1 and TASK172 entry authority remains incomplete.
- R95 mesh qualification resume is not authorized by this extension.
- No production code, engineering-calculation path, dependencies, or lockfiles
  changed. No real case, TASK173/TASK174 solve, Ready, or Merge was performed.

## Validation and artifacts

The deterministic runner was replayed on Python 3.11.15 / NumPy 2.4.6 /
SciPy 1.17.1 / CoolProp 8.0.0 and Python 3.12.13 / NumPy 2.5.0 / SciPy 1.18.0 /
CoolProp 8.0.0. Both selected-profile 72-case result matrices have the same
canonical hash; the selected Python 3.11 profile also reproduced identical
result bytes in a second same-runtime pass. The non-dyadic holdout was not
evaluated by either runtime.

Structured results, runner, holdout input, and this document are linked by the
append-only R96 registry extension. Exact-final-head CI is recorded separately
in the final receipt; its eventual result does not promote this candidate or
authorize the next gate.
