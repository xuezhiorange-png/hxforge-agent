# TASK-172 v0.7 Continuous-Reference Oracle SciPy Canonical Envelope Binding Correction R1

Task: `TASK172_CONTINUOUS_REFERENCE_ORACLE_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION_R1`
PR: #277, OPEN_DRAFT
Authorized predecessor: `566d85d88bdc44c2cc7cb67789690878c669ef0f`
Result: `PASS_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION`

## Decision

R101's reviewed implementation choice is now consistent with the effective
precision reference and its complete uncertainty envelope. For each frozen
fixture and locked runtime, `Q_REF_CANONICAL_W` is the integral evaluated with
`scipy.special.roots_legendre(1024)`. The effective `U_GL_CANONICAL`,
`U_CROSS_CANONICAL`, `U_REDUCTION_CANONICAL`, and `U_Q_CANONICAL` are rebuilt
from SciPy-generated Gauss contributions plus the frozen composite-Simpson
contributions. NumPy `leggauss` remains historical / independent cross-check
evidence only; it contributes no effective canonical quantity.

The bound components are:

```text
U_GL_CANONICAL = max(|Q_SciPy256 - Q_SciPy512|,
                     |Q_SciPy512 - Q_SciPy1024|)
U_SIMPSON = max(|Q_Simpson512 - Q_Simpson1024|,
                |Q_Simpson1024 - Q_Simpson2048|)
U_CROSS_CANONICAL = |Q_SciPy1024 - Q_Simpson2048|
U_ROOT_INTEGRATED_EMPIRICAL = 257-point sampled Brent/TOMS748 maximum × 1
U_REDUCTION_CANONICAL = max observed fsum/ordinary-sum and
                        original-fsum/serialized-roundtrip-fsum discrepancies
U_Q_CANONICAL = U_GL_CANONICAL + U_SIMPSON + U_CROSS_CANONICAL
                + U_ROOT_INTEGRATED_EMPIRICAL + U_REDUCTION_CANONICAL
```

The root-method component remains a finite-sample empirical discrepancy, not
a proven global integral bound. The entire uncertainty quantity is a measured
empirical numerical-reference uncertainty envelope, not a formal true-error
bound; propagation remains required and must preserve that limitation.

## Qualification replay

Frozen R95/R99 support definitions and the R101-tested callbacks were replayed
under Python 3.11.15 / SciPy 1.17.1 and Python 3.12.13 / SciPy 1.18.0. CoolProp
was 8.0.0 in both runtimes. For M01–M04 and M06, the unchanged criterion is
`U_Q_CANONICAL / (abs(Q_REF_CANONICAL) - U_Q_CANONICAL) <= 1e-8`, with a
positive denominator. For near-zero M05, the unchanged criterion is
`U_Q_CANONICAL <= 1e-8 W`.

| Fixture | Q reference (W), both runtimes | U_Q Python 3.11 (W) | U_Q Python 3.12 (W) | Result |
|---|---:|---:|---:|---|
| M01 | 17.051453586322395 | 2.2669865984425996e-11 | 2.2648549702353193e-11 | PASS / PASS |
| M02 | 18.597879246107482 | 8.054001909840736e-12 | 8.029132914089132e-12 | PASS / PASS |
| M03 | 13.187854026392497 | 5.801581437481218e-12 | 5.785594225926616e-12 | PASS / PASS |
| M04 | 16.94171992110042 | 9.64561763794336e-12 | 9.620748642191757e-12 | PASS / PASS |
| M05 | 0.22222342205523007 | 7.722877892746283e-12 | 7.722378292385201e-12 | PASS / PASS |
| M06 | 13.526962848693817 | 4.870770453635487e-12 | 4.844125101044483e-12 | PASS / PASS |

The detailed results record all SciPy orders, Simpson orders, per-series
contribution-vector hashes and reductions, root comparisons, component values,
denominator/metric, and runtime provenance.

## Historical and policy boundaries

R99's historical M05 values remain exactly `GL128=0.2222234220550436`,
`GL256=0.22222342205515927`, and `GL512=0.22222342205526033`; its 64-ULP gate
still fails. R100 and R101 artifacts and all prior registry extensions remain
unchanged. The R100 thresholds, including the `1e-3` oracle-to-mesh separation
factor, were not retuned. The author assertion that the policy was pre-run
remains recorded, while independent repository proof of pre-registration
remains false.

This append-only consistency correction preserves R101's
`REVIEWED_AUTHORITY` lifecycle; it creates no separate self-approved
authority. The only remaining TASK172 blocker is still
`MESH-CONVERGENCE-QUALIFICATION` (count 1). No mesh study, threshold sensitivity,
full mesh-matrix rerun, production-code change, TASK172 implementation, TASK173
or TASK174 solve, Ready, or Merge was performed or authorized.

## Validation and artifacts

The structured evidence binds the frozen predecessor, R100/R101 artifact and
extension hashes, dual-runtime workers, canonical results, and this document.
Exact-final-head CI is recorded in the final receipt. The detailed result
artifact classifies all uncertainty as empirical and keeps the historical R99
failure intact.
