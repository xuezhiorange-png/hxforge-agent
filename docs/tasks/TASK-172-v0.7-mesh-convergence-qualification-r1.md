# TASK-172 v0.7 Mesh-Convergence Qualification R1

**Task:** `TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R1`

**PR:** #277, open draft

**Authorized predecessor:** `18a0ded2c33671d2b8c342505aeaa766ff419c47`

**Result:** `BLOCKED_MESH_CONVERGENCE_QUALIFICATION`

## Decision

The quantitative mesh profile is **not qualified**. The frozen R94 local TRF profile terminates successfully for the first failing refined cell, but its independent physical-residual acceptance check rejects that cell. Since every mesh observable depends on accepted local constitutive states, no threshold, resource cap, discretization indicator, or convergence candidate can be selected from this incomplete matrix.

The sole blocking predicate is:

```text
FROZEN_R94_LOCAL_RESIDUAL_ACCEPTANCE_PASS_FOR_EACH_MESH_CELL=false
```

No R94 solver parameter, roundoff bound, fixture input, or threshold was retuned. The result does not invalidate the R94 reviewed numerical profile generally; it records that the frozen profile's accepted residual envelope did not cover this required refined-cell trial.

## Frozen scope and identities

The PR was `OPEN_DRAFT` at the authorized predecessor. The experiment input matrix was frozen before numerical execution with canonical hash:

```text
b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8
```

It binds six synthetic single-support fixtures, primary counts `1,2,4,8,16,32,64,128`, secondary alignment counts `3,6,12,24,48,96`, exact rational cell bounds, fixture formulas, the R94 profile, threshold test grid, quadrature/extrema oracle plan, and upstream artifact hashes. No real case is required or created.

R94 was replayed unchanged: TRF/linear loss, `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`, 2-point Jacobian, `diff_step=1e-5`, initialization-derived variable scale, `max_nfev=6`, callback cap 24, and `C_round=0.5`.

TASK171 physical-support identity remains distinct from numerical-cell identity. The refinement construction uses exact rational bisection within each support, creates no training physical events, and preserves support identity. Across six fixtures and both sequences, 12 structural geometry audits confirmed exact area conservation and parallel wall-resistance partitioning. The base mesh is explicit; no production reconstruction operator is created.

## First blocking trial

The first rejected local solve is fixture `M01`, primary sequence, `N=8`, cell `xi=[1/4,3/8]`, fraction `1/8`. It is a synthetic tube-hot, dual-active case, not an engineering case.

| Quantity | Observed |
|---|---:|
| TRF termination | success, status 3 (`xtol` satisfied) |
| Function evaluations / callbacks | 4 / 16 |
| `r_i` | `2.0605739337042905e-13 W` |
| `r_i` candidate roundoff bound | `1.699451104588476e-13 W` |
| `abs(r_i)/bound` | `1.2124938035232622` |
| `r_w` / bound | `-3.3173463975799677e-13 W` / `5.929811771063023e-13 W` |
| `r_o` / bound | `2.0472512574087887e-13 W` / `1.185817589901431e-12 W` |
| Wall-state domain | valid |
| R94 residual acceptance | **reject** |

The same-cell diagnostic was replayed under Python 3.11.15 and 3.12.13 with the locked NumPy 2.4.6, SciPy 1.17.1, and CoolProp 8.0.0 versions. Both produced the same diagnostic canonical hash, `3f0608628c841fbff21b224e14b2846e7872cc13ac2251b59434b2b3d6daeea4`. An auxiliary Python 3.14.5 / SciPy 1.18.0 run reached the same failure; it is not treated as the supported-runtime replay.

The frozen continuous reference for M01 completed before the failing mesh cell: Gauss-Legendre orders 128/256/512 and independently refined wall-extrema samples passed their declared reference-stability checks. This is only a partial oracle observation; it does not qualify the six-fixture training matrix.

Before interpreting the blocked mesh result, the runner also executed all eight failure-path fixtures and captured the typed exceptions from their validators: physical-event crossing, coverage gap, overlap, cross-support mapping, nonfinite observable, insufficient refinement depth, precision-floor ambiguity, and resource-cap exhaustion without convergence. All observed codes matched the expected fail-closed outcomes.

## What remains unbound

Because a required local mesh state failed acceptance, the run has no complete mesh-result matrix and did not execute threshold sensitivity. Accordingly, all of the following remain unbound: duty and near-zero duty acceptance thresholds, wall-extrema threshold, precision-floor policy, first-converged-mesh rule, resource cap, and quantitative discretization-error interface. The proposed successive-refinement indicators remain a design shape only, not an accepted estimator.

The runner records the failure as `MESH_NOT_CONVERGED`; the last computed iterate is diagnostic only. It creates no authoritative convergence result. The existing TASK172 blocker ledger remains at one item, `MESH-CONVERGENCE-QUALIFICATION`, and TASK172 entry authority remains incomplete.

## Boundaries preserved

- TASK172 scope remains local constitutive-field and already-authorized physical-support aggregation only; TASK173 boundary solving and TASK174 hydraulics were not run.
- No mesh threshold, convergence order, Richardson extrapolation, GCI, or mesh-independence claim was selected.
- R94, TASK171, and historical R1–R94 payloads are unchanged.
- No production code, production calculation path, dependency, or lockfile changed.
- No real case, production mesh, TASK173/TASK174 solver, Ready, or Merge was created or authorized.

The exact failure data, input matrix, hashes, and validation status are recorded in the linked structured evidence and results artifacts. The candidate remains blocked; no downstream gate is implied.
