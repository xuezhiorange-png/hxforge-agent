# TASK-172 v0.7 Continuous-Reference Oracle Precision Independent Review R1

**Task:** `TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_INDEPENDENT_REVIEW_R1`

**PR:** #277, OPEN_DRAFT

**Authorized predecessor:** `0af454f0c9850de22b3d70f2006e5e3c4d1e1075`

**Reviewed candidate:** R100 `CONTINUOUS_REFERENCE_ORACLE_PRECISION_CANDIDATE_COMPLETED`

**Review result:** `PASS`

**Effective lifecycle:** `REVIEWED_AUTHORITY`

## Decision

The independent replay reproduces the frozen R100 numerical candidate for M01–M06 in Python 3.11.15 and 3.12.13. Separate NumPy `leggauss` and SciPy `roots_legendre` implementations agree through orders 128, 256, 512, and 1024. The effective reviewed quadrature order is 1024, but the canonical reference producer is set to `scipy.special.roots_legendre(1024)` because the official NumPy 2.4 documentation says its results have only been tested through degree 100 and warns that higher degrees may be problematic. This is an append-only review overlay; R100's original NumPy results and producer record are unchanged.

R99's M05 64-ULP gate remains a historical failure. The independent replay reproduces its frozen values exactly and does not alter or reinterpret that rule. The R100 effective precision policy remains distinct.

The effective uncertainty classification is narrowed to **measured empirical numerical-reference uncertainty envelope**. `U_Q` is not a formal true-error bound. In particular, the maximum Brent/TOMS748 difference observed at 257 fixed support coordinates, multiplied by normalized length one, is not proven to bound the integral over all support coordinates. R100's word “conservative” is therefore not accepted as a strict upper-bound claim. The envelope remains usable only with this empirical qualification and must continue to be propagated, without being relabeled as a proven bound.

R100 states that the `1e-3` separation factor was fixed before its runs. Repository history does not independently prove pre-registration: the R100 document, runner, results, and evidence first appear together in commit `0af454f0c9850de22b3d70f2006e5e3c4d1e1075`. This review did not retune any precision limit or separation factor; the author assertion is recorded as such, not as independently proven repository history.

## Independent source and implementation review

The official [NumPy 2.4 `leggauss` documentation](https://numpy.org/doc/2.4/reference/generated/numpy.polynomial.legendre.leggauss.html) describes the Gauss–Legendre exactness rule, but limits its testing statement to degree 100 and warns about higher degrees. The official [SciPy 1.18 `roots_legendre` documentation](https://docs.scipy.org/doc/scipy-1.18.0/reference/generated/scipy.special.roots_legendre.html) describes roots of the degree-`n` Legendre polynomial and exactness through degree `2n-1`. The independent test used separately generated arrays from each API; no nodes or weights were shared.

Across both runtime environments, all generated nodes, weights, and contributions were finite. Maximum NumPy/SciPy node difference was `1.1102230246251565e-16`; maximum weight difference was `6.391392135592783e-14`; maximum weight-sum deviation from two was `4.440892098500626e-16`. Maximum Q disagreement across all fixtures/runtimes was `3.552713678800501e-15 W` at order 128, `1.7763568394002505e-14 W` at order 256, `1.0658141036401503e-14 W` at order 512, and `7.105427357601002e-15 W` at order 1024. Symmetry checks were exact in the recorded binary64 outputs. Each order's observed Q difference was within that fixture/runtime's R100 empirical `U_Q` envelope.

Adjudication: `ACCEPT_GAUSS1024_BUT_CANONICAL_PRODUCER_SHOULD_USE_SCIPY_ROOTS_LEGENDRE`. The order-1024 result is accepted for this scoped reference candidate with independent cross-check; NumPy `leggauss(1024)` is not selected as the canonical producer.

## Uncertainty semantics

All five components are observed discrepancies, not formal bounds:

- `U_GL`: maximum observed disagreement between the selected Gauss orders 256/512 and 512/1024.
- `U_SIMPSON`: maximum observed disagreement between the selected composite-Simpson orders 512/1024 and 1024/2048.
- `U_CROSS`: observed Gauss-1024 versus Simpson-2048 discrepancy.
- `U_ROOT_INTEGRATED`: maximum observed Brent/TOMS748 heat-rate difference on 257 fixed coordinates, multiplied by normalized support length one. A finite-grid maximum is not a proven global maximum or integral upper bound.
- `U_REDUCTION`: observed ordinary-sum versus `math.fsum` discrepancy and serialization-roundtrip contribution discrepancy.

Their sum is a **measured empirical numerical-reference uncertainty envelope**, not a formal true-error bound and not a mathematically proven conservative envelope over unsampled support. Canonical wording for future references is: “Measured empirical numerical-reference uncertainty envelope from the stated quadrature, sampled root-method, and floating-point reduction comparisons; not a formal true-error bound or a proven global upper bound.” Reference-uncertainty propagation remains required with this limitation attached.

## Independent numerical replay

For every fixture, R100's NumPy Gauss results at 128/256/512/1024, Simpson results at 512/1024/2048, root-method comparison, wall-extrema comparison at 257/513, reduction terms, and `U_Q` were independently recomputed and matched the corresponding locked-runtime R100 values exactly. SciPy quadrature was computed separately at all four orders. The full machine-readable per-fixture/per-order records are in the linked results artifact.

| Fixture | NumPy GL-1024 Q (W) | SciPy GL-1024 Q (W) | Absolute cross-implementation difference (W) |
|---|---:|---:|---:|
| M01 | 17.05145358632239 | 17.051453586322395 | 7.105427357601002e-15 |
| M02 | 18.597879246107475 | 18.597879246107482 | 7.105427357601002e-15 |
| M03 | 13.187854026392502 | 13.187854026392497 | 5.329070518200751e-15 |
| M04 | 16.941719921100418 | 16.94171992110042 | 3.552713678800501e-15 |
| M05 | 0.22222342205523007 | 0.22222342205523007 | 0 |
| M06 | 13.526962848693813 | 13.526962848693817 | 3.552713678800501e-15 |

M05 again gives R99's exact historical values: GL128 `0.2222234220550436`, GL256 `0.22222342205515927`, and GL512 `0.22222342205526033`. The 256–512 difference remains `1.0105805081650487e-13 W`, versus the unchanged 64-ULP criterion `1.7763568394002505e-15 W`; the historical gate still fails by a factor of `56.890625`. GL1024 remains `0.22222342205523007 W`. R99 is preserved; the R100 precision policy remains a separate candidate.

Across the two runtimes, all six Q references and Gauss/Simpson/root comparison components matched R100. The maximum observed cross-runtime `U_Q` difference was `3.552713678800501e-14 W`, confined to reduction behavior. The new replay matched each runtime's R100 record exactly. R100's existing first/repeat worker files were also byte-compared in the review environment: Python 3.11 SHA-256 `68316f95b2041b5c761cb71b0801d4194069364bc8e822e589f736c486a887c2`; Python 3.12 SHA-256 `b03aa9d7cd355d41e8157f02050c4d4be9704880b58d57053f4ea83f4c2d36d7`.

The maximum observed 257-point Brent/TOMS748 differences were `1.901057089526148e-11 W` in heat rate, `3.410605131648481e-13 K` in inner-wall temperature, and `1.7053025658242404e-13 K` in outer-wall temperature. The largest 257/513 wall-extrema difference was `5.684341886080802e-14 K`. Canonical serialization round-tripped the tested float contributions exactly; `math.fsum`/ordinary-sum differences remain recorded per runtime.

## Lifecycle, blockers, and scope

The precision candidate is independently accepted as `REVIEWED_AUTHORITY` with the implementation and uncertainty qualifications above. R100 is not edited. R99 remains a valid historical blocked result. Reference-uncertainty propagation remains required.

No mesh study, mesh-threshold sensitivity, full mesh matrix rerun, mesh adjudication, TASK173/TASK174 solve, production code change, TASK172 implementation, Ready action, or Merge action occurred. The sole remaining blocker is still `MESH-CONVERGENCE-QUALIFICATION`; blocker count remains one, and TASK172 entry authority remains incomplete. This review does not establish mesh convergence.

The append-only R101 evidence, detailed replay results, test-only runner, and registry extension are linked by hashes in the authority registry. Exact-final-head CI is recorded in the final receipt; no later step is authorized by this review.
