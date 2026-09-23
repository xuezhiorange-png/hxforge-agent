# TASK-172 v0.7 Mesh-Convergence Qualification R2

**Task:** `TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R2`
**PR:** #277, open draft
**Authorized predecessor:** `fe9377cc1ea67370572b95338e54e861eda8a870`
**Result:** `BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2`

## Decision

The R95 mesh study was resumed with its exact frozen input and the reviewed R98 residual-scale overlay (`C_round=1.0`). The former M01/PRIMARY/N=8 blocking cell now passes. The R2 run nevertheless stops at M05 because the frozen continuous duty oracle fails its existing 64-ULP Gauss-reference stability check. No threshold, R95 oracle rule, fixture formula, mesh sequence, or solver setting was changed.

The sole blocking predicate is:

```text
FROZEN_GAUSS_REFERENCE_STABILITY_PASS_FOR_M05=false
```

This prevents a complete six-fixture matrix, threshold sensitivity, precision-floor qualification, and mesh candidate selection. The mesh-convergence canonical blocker remains open.

## Frozen inputs and repaired prior cell

The exact R95 input matrix was replayed with canonical hash `b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8`. Fixture formulas, total areas, primary and secondary sequences, threshold grid, oracle plan, failure fixtures, and topology semantics are unchanged. The R98 overlay was consumed as reviewed: `C_round=1.0`; the R94 base profile and all other solver settings remain unchanged.

The former M01/PRIMARY/N=8 cell at exact interval `[1/4,3/8]` passed with `r_i=2.0605739337042905e-13 W`, bound `3.398902209176952e-13 W`, ratio `0.6062469017616311`, 4 function evaluations, and 16 residual callbacks.

R95's global hot/cold range test rejects M05 because its two temperature ranges overlap. R2 checked the frozen explicit `hot_side=TUBE` role pointwise at the same 4097 physical coordinates instead: the minimum tube-minus-shell temperature difference is `0.008600000000001273 K`, with no local role crossover. This test-only role audit did not change the fixture, assign roles from temperature, or modify R95.

## Blocking independent-reference evidence

For M05, the frozen R95 oracle produced the following signed-duty integrations:

| Gauss-Legendre order | `Q_ref` (W) |
|---:|---:|
| 128 | 0.2222234220550436 |
| 256 | 0.22222342205515927 |
| 512 | 0.22222342205526033 |

The frozen 256-to-512 difference is `1.0105805081650487e-13 W`. Its frozen criterion is `64 × ulp(Q512) = 1.7763568394002505e-15 W`; the observed difference is `56.890625` times that criterion. The 128-to-256 difference is `1.1565748359032568e-13 W` (`65.109375` criterion units). Thus the failure is the prescribed reference-stability gate, not a mesh-threshold comparison.

The frozen 257/513 extrema sampling returned identical endpoint extrema for all four wall metrics, so the extrema sampling check itself passed. It does not compensate for the failed duty quadrature check.

The 3.11.15 environment (NumPy 2.4.6, SciPy 1.17.1, CoolProp 8.0.0) and 3.12.13 environment (NumPy 2.5.0, SciPy 1.18.0, CoolProp 8.0.0) independently reproduced the same three duty values, differences, and failing 64-ULP check. This is a dual-runtime replay of the blocking oracle observation only, not a complete dual-runtime mesh-matrix replay.

The first full R2 worker run completed M01–M04 for both frozen sequences (1776 accepted local cell solves) and then stopped while constructing M05's continuous reference, before any M05 or M06 mesh-cell solve. The exception prevented a durable complete-matrix artifact. The six-fixture matrix is therefore incomplete; no convergence metrics, threshold tuple, resource cap, or precision-floor authority is selected.

## Preserved boundary

- R95 input and R98 overlay remain unchanged; R1–R98 historical payloads remain immutable.
- The frozen threshold grid and both mesh sequences were not expanded or retuned.
- No 256-cell result was synthesized, and no Richardson extrapolation or GCI was used.
- Failure-taxonomy fixtures pass; failures remain non-authoritative.
- No production code, production rating, real case, TASK173/TASK174 solve, dependency, lockfile, Ready, or Merge was created or authorized.

## Blocker ledger

`MESH-CONVERGENCE-QUALIFICATION` remains the sole parent blocker. The candidate lifecycle is `NONE`; `MESH_CONVERGENCE_CANONICAL_BLOCKER_REMOVED=false`; the effective remaining TASK172 entry blocker count remains 1. No next gate is implied.

Exact hashes, runtime observations, and validation outcomes are in the linked structured evidence and results artifacts.
