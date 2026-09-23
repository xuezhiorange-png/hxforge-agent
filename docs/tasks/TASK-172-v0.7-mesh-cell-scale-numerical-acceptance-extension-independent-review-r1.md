# TASK-172 v0.7 Mesh-Cell-Scale Numerical Acceptance Extension Independent Review R1

**Task:** `TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_INDEPENDENT_REVIEW_R1`
**Result:** `REVIEWED_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION`
**PR:** #277, open draft
**Authorized predecessor:** `1d98b6a990d564f546214fd2f5801b91990dd955`

## Independent decision

The frozen R96 candidate P1 was independently replayed, the R97 corrected
holdout and duplicate audit were hash-checked and recomputed, and the exact
30-case holdout was executed without changing any solver or acceptance
parameter. All 30 cases passed on both Python runtimes (60 accepted executions).
The same-runtime replay was deterministic, and the numeric solutions were
exactly equal across the tested Python 3.11 and 3.12 environments.

This supports an append-only reviewed overlay for the mesh-cell-scale
applicability of `C_round=1.0`. It does not revise R94, R95, R96, or R97, does
not establish a mesh termination threshold, and does not close
`MESH-CONVERGENCE-QUALIFICATION`.

## Frozen candidate and review basis

The unchanged P1 profile has canonical hash
`029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6`:

- TRF, linear loss; `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`;
- 2-point Jacobian, `diff_step=1e-5`, initialization-derived `x_scale`;
- `max_nfev=6`, residual callback cap 24;
- residual scale `abs(q_ts_seed)`, `C_round=1.0`;
- `tr_solver=exact`, empty `tr_options`, `f_scale=1.0`, no Jacobian sparsity.

The R96/R97 replay independently confirmed the 72-case P1 training matrix,
the frozen R95 M01, N=8 diagnostic, the corrected holdout identity, and the
70-entry K01–K05 by R94/R95 prior-case duplicate matrix. The corrected holdout
has no exact prior base-case duplicates. P1 remains the preselected candidate:
P0 passed training but failed the required R95 diagnostic; P1 passed both;
P2 and P3 failed that diagnostic. No candidate selection was rerun.

## Holdout execution

The unchanged corrected input is R96A's five cases K01–K05 crossed with exact
fractions `1/3`, `1/6`, `1/12`, `1/24`, `1/48`, and `1/96`. The 30 unique
cases were executed twice in each runtime. The exact scale oracle used the
independently solved f=1 reference for each K case and the frozen identities
`q_hc,f=f*q_hc,1`, `Twi,f=Twi,1`, and `Two,f=Two,1`. Representative scalar
validation-oracle replays at `1/3`, `1/24`, and `1/96` passed for all five
cases on both runtimes; the scalar reduction remains validation-only.

| Runtime | Python / NumPy / SciPy / CoolProp | Holdout | Max residual/bound ratio | Max q oracle error | Max wall-temperature error | Max nfev / callbacks | Resource cap hits |
|---|---|---:|---:|---:|---:|---:|---:|
| Primary | 3.11.15 / 2.4.6 / 1.17.1 / 8.0.0 | 30/30 | 0.4112537026595884 | 5.799805080641818e-13 W | 5.684341886080802e-14 K | 4 / 16 | 0 |
| Secondary | 3.12.13 / 2.5.0 / 1.18.0 / 8.0.0 | 30/30 | 0.4112537026595884 | 5.799805080641818e-13 W | 5.684341886080802e-14 K | 4 / 16 | 0 |

The frozen caps are 6 function evaluations and 24 residual callbacks, leaving
headroom of 2 and 8, respectively. The nearest-rank p95 residual/bound ratio
was 0.4112537026595884. No new margin threshold was introduced. All 30
cross-runtime numeric solutions matched exactly; this was observed, not added
as a pass requirement.

K03 remained a nonzero near-zero solve (`ΔT=0.0004 K`; at scale `1/3`,
`q_hc=0.0017094017193872945 W`). K05 retained signed negative heat flow (at
scale `1/3`, `q_hc=-5.594392508000921 W`); no absolute-value substitution or
nonnegative clamp was used. No zero-duty branch was invoked.

## Effective lifecycle and boundaries

The R96 P1 overlay is now `REVIEWED_AUTHORITY` for the tested mesh-cell-scale
residual-acceptance applicability, with `EFFECTIVE_MESH_CELL_SCALE_C_ROUND=1.0`.
R94's base profile and historical records remain unchanged. The R95 mesh
qualification resume is authorized for a separate R2 gate, but R95 was not
rerun here. That next gate must replay the exact R95 frozen input matrix
`b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8`.

The mesh-convergence canonical blocker remains open; the effective parent
blocker count remains 1 and TASK172 entry authority is incomplete. No mesh
threshold was selected; no refinement/mesh study, R95 rerun, TASK173/174 solve,
production implementation, Ready, or Merge was performed or authorized.

## Evidence and validation

The structured evidence and complete per-case runtime matrices are in the
linked evidence JSON and results JSON. The test-only runner is pinned by SHA-256
in the registry extension. R1–R97 historical payloads are unchanged. Static
replay, holdout identity/independence, numerical acceptance, deterministic
replay, dual-runtime replay, formatting, and repository validation are recorded
in the evidence. Exact-final-head CI is recorded in the final task receipt.

**Next gate:** `AUTHORIZE_TASK172_MESH_CONVERGENCE_QUALIFICATION_R2_ONLY`
