# TASK-172 v0.7 Continuous-Reference Oracle Precision Qualification R1

**Task:** TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_QUALIFICATION_R1

**PR:** #277, open draft

**Authorized predecessor:** bc940cb8abe74ec33c56935a2a2a0b60ff628c8a

**Result:** CONTINUOUS_REFERENCE_ORACLE_PRECISION_CANDIDATE_COMPLETED

**Lifecycle:** proposed; independent authority review pending

## Decision

R99 remains a valid fail-closed mesh-study result. Its M05 predicate failed because the frozen 64 × ulp(Q512) check is only a final-result representational spacing heuristic; it does not quantify the compound continuous-reference pipeline of property evaluations, a local scalar nonlinear root at each quadrature node, quadrature multiplication, and floating-point reduction. This review does not claim that a 64-ULP check is invalid in every context. It is insufficient as the total numerical-uncertainty measure for this oracle.

A frozen project reference-precision policy was evaluated without changing the R95 fixtures, R95 mesh sequences, R98 overlay, or mesh thresholds. Two independent quadrature families were compared, the local Brent oracle was cross-checked against TOMS748, reduction and canonical-serialization effects were measured, and the entire six-fixture qualification was repeated in locked Python 3.11 and 3.12 environments. Every fixture passed in both runtimes.

The resulting policy is a proposed authority candidate, not a reviewed authority. It does not close the mesh-convergence blocker or select any mesh threshold.

## Frozen precision policy

The policy is classified as PROJECT_REFERENCE_PRECISION_POLICY; the separation factor was fixed before these numerical runs and was not tuned from their results.

- Duty-reference separation from the smallest frozen mesh threshold: 1e-3.
- For M01–M04 and M06: U_Q / (abs(Q_ref) - U_Q) <= 1e-8, with a required positive denominator.
- For near-zero M05: U_Q <= 1e-8 W.
- Wall-extrema reference stability remains 1e-8 K, compared at 257 and 513 sample points.
- Q_ref is the order-1024 Gauss-Legendre result. Simpson and TOMS748 are independent validation methods, not averaged into the reference.
- U_Q = U_GL + U_SIMPSON + U_CROSS + U_ROOT_INTEGRATED + U_REDUCTION.
- U_Q is a measured conservative numerical-reference uncertainty envelope, not a formal true-error theorem. It must be propagated into later mesh-oracle error bounds.

U_GL is the maximum of the 256–512 and 512–1024 Gauss disagreements. U_SIMPSON is the maximum of the 512–1024 and 1024–2048 composite-Simpson disagreements. U_CROSS is the absolute difference between Gauss-1024 and Simpson-2048. U_ROOT_INTEGRATED is the maximum observed Brent/TOMS748 heat-rate difference on 257 fixed support coordinates; because normalized support length is one, that pointwise maximum is used conservatively as its integrated contribution. U_REDUCTION is the maximum observed difference between math.fsum and ordinary summation or between the original and canonical-serialization-round-tripped contributions.

## Six-fixture qualification

The table reports the reference and measured uncertainty for both locked runtimes. The relative metric is used for M01–M04/M06; M05 uses its absolute-watt limit.

| Fixture | Q_ref (W) | U_Q, Python 3.11 (W) | U_Q, Python 3.12 (W) | Metric, Python 3.11 / 3.12 | Limit | Result |
|---|---:|---:|---:|---:|---:|---|
| M01 | 17.05145358632239 | 2.2662760557068395e-11 | 2.262723342028039e-11 | 1.3290808576740443e-12 / 1.326997332266181e-12 | 1e-8 relative | PASS |
| M02 | 18.597879246107475 | 8.039791055125534e-12 | 8.004263918337529e-12 | 4.3229612090377093e-13 / 4.303858419779912e-13 | 1e-8 relative | PASS |
| M03 | 13.187854026392502 | 5.7909232964448165e-12 | 5.778488798569015e-12 | 4.391103575197404e-13 / 4.381674825189307e-13 | 1e-8 relative | PASS |
| M04 | 16.941719921100418 | 9.64206492426456e-12 | 9.620748642191757e-12 | 5.691314086866197e-13 / 5.678731962871643e-13 | 1e-8 relative | PASS |
| M05 | 0.22222342205523007 | 7.722877892746283e-12 | 7.722378292385201e-12 | 7.722877892746283e-12 W / 7.722378292385201e-12 W | 1e-8 W absolute | PASS |
| M06 | 13.526962848693813 | 4.8618886694384855e-12 | 4.835243316847482e-12 | 3.5942204645810094e-13 / 3.574522508070693e-13 | 1e-8 relative | PASS |

For M05, the preserved R99 values were reproduced exactly: Gauss-128 0.2222234220550436 W, Gauss-256 0.22222342205515927 W, and Gauss-512 0.22222342205526033 W. The historical 64-ULP criterion remains 1.7763568394002505e-15 W; the 256–512 difference is 1.0105805081650487e-13 W (56.890625 times that criterion), so the historical gate still fails. Under the new compound policy, M05 has:

| Quantity | Value |
|---|---:|
| Gauss-1024 Q_ref | 0.22222342205523007 W |
| Simpson-512 | 0.22222342205521967 W |
| Simpson-1024 | 0.2222234220552501 W |
| Simpson-2048 | 0.22222342205524148 W |
| U_GL | 1.0105805081650487e-13 W |
| U_SIMPSON | 3.044786645034492e-14 W |
| U_CROSS | 1.1407541578023483e-14 W |
| U_ROOT_INTEGRATED | 7.579464833540328e-12 W |
| U_REDUCTION | 4.996003610813204e-16 W |
| U_Q | 7.722877892746283e-12 W |
| Absolute qualification limit | 1e-8 W |

Thus R99’s historical gate remains a faithful record while the new effective reference policy resolves the sole precision predicate with an explicitly propagated uncertainty envelope.

## Independent numerical checks

- Gauss-Legendre orders 128, 256, 512, and 1024 used deterministic leggauss nodes and math.fsum.
- Composite Simpson used a separately implemented uniform [0,1] partition at 512, 1024, and 2048 subintervals. It did not consume Gauss results.
- Every fixture was checked at 257 fixed xi values using frozen Brent brackets and independent TOMS748 roots. All TOMS748 roots converged; the largest observed heat-rate difference was 1.901057089526148e-11 W (M01), the largest inner-wall difference was 3.410605131648481e-13 K, and the largest outer-wall difference was 1.7053025658242404e-13 K.
- The largest 257-to-513 wall-extrema sampling difference across all fixtures was 5.684341886080802e-14 K (M03), below the frozen 1e-8 K criterion.
- math.fsum versus ordinary-sum differences were measured on every quadrature contribution vector. Canonical float serialization round-tripped every tested contribution exactly; observed serialization-induced total difference was zero.
- Fixture-scoped exact-binary64 (T,P) memoization was used only to avoid repeated deterministic property evaluations. It did not interpolate, average, round, or reuse a state across fixtures.

## Runtime reproducibility

The complete six-fixture qualification was run twice in each locked environment. The two Python 3.11 worker outputs were byte-identical (SHA-256 68316f95b2041b5c761cb71b0801d4194069364bc8e822e589f736c486a887c2); the two Python 3.12 outputs were byte-identical (SHA-256 b03aa9d7cd355d41e8157f02050c4d4be9704880b58d57053f4ea83f4c2d36d7).

| Runtime | NumPy | SciPy | CoolProp | Platform |
|---|---|---|---|---|
| Python 3.11.15 | 2.4.6 | 1.17.1 | 8.0.0 | macOS 27.2 arm64 |
| Python 3.12.13 | 2.5.0 | 1.18.0 | 8.0.0 | macOS 27.2 arm64 |

All six Q_ref values and U_GL, U_SIMPSON, U_CROSS, and U_ROOT_INTEGRATED values were exactly equal across these two runtimes. The observed differences were confined to U_REDUCTION and therefore the corresponding U_Q: at most 3.552713678800501e-14 W. Exact cross-runtime equality was not required.

## Scope and disposition

No mesh threshold sensitivity, full mesh matrix rerun, mesh status decision, resource-cap selection, TASK173 solve, or TASK174 solve was performed. The 1e-2, 1e-3, 1e-4, and 1e-5 mesh threshold grid remains unchanged. R95 inputs, M01–M06 fixture definitions, primary/secondary sequences, and the reviewed R98 C_round=1.0 overlay remain immutable.

The continuous-reference precision policy is recorded as PROPOSED_AUTHORITY_REVIEW_PENDING. It does not remove MESH-CONVERGENCE-QUALIFICATION; the effective blocker count remains 1, and TASK172 entry authority remains incomplete. The sole next gate is independent review of this precision-policy candidate.

The structured evidence and full per-runtime result matrices are linked from the append-only R100 registry extension. Exact-final-head CI is recorded in the final task receipt; no Ready or Merge is authorized.
