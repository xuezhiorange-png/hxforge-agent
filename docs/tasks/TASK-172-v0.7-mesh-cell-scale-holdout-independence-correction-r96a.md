# TASK-172 v0.7 Mesh-Cell-Scale Holdout Independence Correction R96A

**Task:** `TASK172_V0_7_MESH_CELL_SCALE_HOLDOUT_INDEPENDENCE_CORRECTION_R96A`
**Result:** `CORRECTED_NON_DYADIC_HOLDOUT_FROZEN`
**Predecessor:** `328cec44fe37299346da3ccda97c35fd06dfa1cb`

## Decision

R96's P1 candidate and its numerical results are preserved. This correction
addresses only the future non-dyadic review holdout: a normalized field-by-field
audit confirmed that its original K04 exactly duplicated R94 H05 and original
K05 exactly duplicated R94 H04. The original holdout remains immutable and is
explicitly rejected for independent-review execution. It was not executed.

K04 and K05 are replaced in a new R96A holdout input. K01-K03 remain unchanged.
The corrected five-case matrix has no exact base-parameter duplicate among
R94 H01-H08 or R95 M01-M06. R95 temperature inputs are support-dependent
profiles; comparison uses each complete profile identity, not a selected
midpoint value. Numeric scalar fields and resistance fractions are compared by
numeric value, with fractions matched by named role rather than JSON key order
or text formatting. The complete pairwise matrix is in the structured evidence.

## Preserved R96 candidate

The selected candidate remains `P1_ACCEPTANCE_EXTENSION`, `C_round=1.0`,
`xtol=1e-12`, with selected-profile canonical hash
`029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6`.
R96's H01-H08 dyadic training results and the R95 M01/N=8 diagnostic remain
unchanged. This correction performs static artifact/hash replay only; it does
not rerun the 72 training cases or the R95 diagnostic.

## Corrected frozen holdout

K01-K03 retain their prior definitions. K04 is now the `TUBE_C3_ONLY` fixture
with tube/shell bulk temperatures 299.58/298.92 K, pressure 101325 Pa,
Reynolds number 8500, base resistance 0.064 K/W, and tube/wall/shell resistance
fractions 0.22/0.18/0.60. K05 is now the `DUAL_ACTIVE_NEGATIVE_Q` fixture with
tube/shell bulk temperatures 298.68/299.72 K, pressure 100000 Pa, Reynolds
number 220000, base resistance 0.062 K/W, and fractions 0.48/0.32/0.20.
Both are numerical-method fixtures only, not engineering authority.

The corrected holdout retains exact fractions `1/3`, `1/6`, `1/12`, `1/24`,
`1/48`, and `1/96`, for 30 future cases. It is frozen and not executed;
property-backend and solver calls are false. Independent review is required
before execution. The corrected holdout canonical hash is
`5efc368eedee738d507fbf15bf592539d4c68b8017b4d254b6cc4c27ccfbd3e0` and the
corrected base-case matrix canonical hash is
`8bfa38ae0c28a047000782b2dc484ddf62797ccbf6d55faa1034f8ddc2fa06d0`.

## Preserved boundaries

- R1-R96 historical documents, evidence, and registry extensions are immutable.
- R96 remains `PROPOSED_AUTHORITY_REVIEW_PENDING`; no lifecycle promotion occurs.
- The numerical parent blocker remains closed; `MESH-CONVERGENCE-QUALIFICATION`
  remains the sole parent blocker (count 1).
- Mesh qualification resume remains unauthorized. No numerical experiment,
  mesh study, threshold sensitivity, property-backend call, or solver call was
  performed.
- No production code, dependencies, lockfiles, Ready, or Merge were changed or
  authorized.

## Artifacts and validation

The corrected holdout input, correction evidence, this document, and the
append-only `r97_extension` are hash-linked in the authority registry. The R96
original holdout is retained unchanged as historical evidence of the rejected
design. Validation includes predecessor/PR checks, R96 static replay, original
contamination confirmation, normalized pairwise duplicate audit, corrected
holdout hash/freeze checks, historical immutability, exact diff allowlist,
JSON/canonical-hash checks, `git diff --check`, and manifest validation.
Exact-final-head CI is recorded in the final receipt; this correction does not
authorize holdout execution or the subsequent independent-review gate.
