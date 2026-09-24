# TASK-172 v0.7 Mesh-Convergence Final Qualification R1

Task: `TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_FINAL_R1`
PR: #277 (`OPEN_DRAFT`)
Authorized predecessor: `a651c9ad92e391f203f79440b1855405a0d2a46f`
Result: `PASS_MESH_CONVERGENCE_QUALIFICATION`

## Decision

The frozen six-fixture mesh matrix satisfies the R95 convergence contract when
replayed with the R98 `C_round=1.0` overlay and R102 SciPy GL1024 references and
empirical uncertainty envelopes. Both locked Python runtimes classify all six
fixtures and both mesh sequences identically. The frozen mesh blocker is
therefore closed for this qualification scope; TASK172 entry authority is
complete, but no implementation or downstream solve is authorized by this
receipt.

## Frozen inputs and execution

No fixture, mesh sequence, threshold, reference, or precision policy was
redefined. The R95 input-matrix canonical hash is
`b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8`. The
primary sequence is `[1,2,4,8,16,32,64,128]` cells; the secondary alignment
sequence is `[3,6,12,24,48,96]`. The three threshold axes each retain
`[1e-2,1e-3,1e-4,1e-5]`, producing all 64 tuples. The frozen resource-cap grid
is `[32,64,128,256]` cells.

Each runtime executed all 84 fixture/sequence/level combinations and all 2,664
local cell solves, then repeated those 2,664 mesh solves. All required local
solves were accepted. The eight frozen invalid-mesh/resource failure fixtures
also emitted their expected typed outcomes and did not leave an authoritative
partial result.

| Runtime | Python | NumPy | SciPy | CoolProp | Replay projection hash |
|---|---:|---:|---:|---:|---|
| Python 3.11 | 3.11.15 | 2.4.6 | 1.17.1 | 8.0.0 | `02cab25b9ac3a3c63f0a3a0c88a48788f8086a70e45d71e7f38ca264e76fa36e` |
| Python 3.12 | 3.12.13 | 2.5.0 | 1.18.0 | 8.0.0 | `02cab25b9ac3a3c63f0a3a0c88a48788f8086a70e45d71e7f38ca264e76fa36e` |

For both runtimes, first and repeated mesh projections were byte-identical and
had the same canonical hash. The two runtimes produced the same threshold
classification, selected threshold tuple, selected resource cap, and overall
qualification result.

## Reference and uncertainty handling

The canonical producer remains `SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024`; NumPy
`leggauss` is not used as the effective reference. Each mesh comparison uses
the R102 `Q_ref` and `U_Q`. For non-near-zero fixtures the reference-aware
comparison propagates the envelope into the numerator and uses
`abs(Q_ref)-U_Q` as the lower reference magnitude. M05 uses absolute watts and
does not divide by its small duty. The envelope remains
`MEASURED_EMPIRICAL_NUMERICAL_REFERENCE_UNCERTAINTY_ENVELOPE`, not a formal
true-error bound or proven global upper bound.

| Fixture | Canonical Q (W) | U_Q Python 3.11 (W) | U_Q Python 3.12 (W) |
|---|---:|---:|---:|
| M01 | 17.051453586322395 | 2.2669865984425996e-11 | 2.2648549702353193e-11 |
| M02 | 18.597879246107482 | 8.054001909840736e-12 | 8.029132914089132e-12 |
| M03 | 13.187854026392497 | 5.801581437481218e-12 | 5.785594225926616e-12 |
| M04 | 16.94171992110042 | 9.64561763794336e-12 | 9.620748642191757e-12 |
| M05 | 0.22222342205523007 | 7.722877892746283e-12 | 7.722378292385201e-12 |
| M06 | 13.526962848693817 | 4.870770453635487e-12 | 4.844125101044483e-12 |

R102 continuous wall extrema were stable under the frozen 257/513-point check.
The mesh acceptance uses the frozen wall-extrema quantities and their
reference/solver precision floors, not duty alone.

## Threshold and sequence adjudication

The complete 64-tuple sensitivity matrix has 12 feasible tuples and exactly
one componentwise-loosest feasible tuple. The unchanged frozen selection rule
therefore selects duty-relative `0.01`, near-zero duty absolute `0.01 W`, and
wall-extrema absolute `0.01 K`. Among the frozen resource caps, 32 and 64 cells
do not provide the required 128-cell headroom; 128 is the smallest cap that
does, and 256 also supports it. The cap is a resource policy, not proof of
convergence. The componentwise-looser feasibility audit has no violations.

| Fixture | Primary first accepted / headroom cells | Secondary first accepted / headroom cells | Q disagreement (W) | Max wall-extrema disagreement (K) |
|---|---:|---:|---:|---:|
| M01 | 64 / 128 | 48 / 96 | 3.300862833199858e-5 | 8.876109067159632e-4 |
| M02 | 64 / 128 | 48 / 96 | 3.598802979779603e-5 | 8.876474816474911e-4 |
| M03 | 32 / 64 | 24 / 48 | 2.024400203026744e-9 | 1.7843208798353771e-3 |
| M04 | 16 / 32 | 12 / 24 | 3.18941374743531e-4 | 1.1209873500206413e-3 |
| M05 | 32 / 64 | 24 / 48 | 1.4155343563970746e-13 | 8.424355025908881e-4 |
| M06 | 16 / 32 | 12 / 24 | 3.431174951984417e-4 | 4.320974164784275e-4 |

Every primary and secondary sequence passed its frozen two-consecutive-pair,
same-class reference-agreement, wall-extrema, and later-headroom requirements.
There was no selected-threshold classification disagreement between the two
sequences for any fixture.

Non-monotonic diagnostics were retained rather than hidden. M03 primary has a
successive-delta non-decrease at 16 cells; the 16-cell candidate was not
accepted because its wall/reference classification failed, and the selected
primary result is at 32 cells with 64-cell headroom. M03 secondary has a
reference-error reversal at 6 cells; its selected result is at 24 cells with
48-cell headroom. The frozen R95 rule does not require global monotonicity; the
later required pairs, reference agreement, wall checks, headroom, and all
threshold-sensitivity classifications pass. Full level-by-level values and
diagnostics are in the results artifact.

The reviewed R98 roundoff overlay was consumed using its frozen expression:
`effective_bound_j = R94_candidate_bound_j * (1.0 / 0.5)`. No threshold,
`C_round`, resource-cap grid, precision policy, or oracle was retuned.

## Historical boundary and status

R99 remains the historical
`BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2` result. Its M05 values remain
`GL128=0.2222234220550436`, `GL256=0.22222342205515927`, and
`GL512=0.22222342205526033`; its historical 64-ULP gate still fails. This
qualification uses R102 as the later reviewed effective reference and does not
rewrite that prior result. R1–R102 payloads and prior registry extensions are
immutable.

The mesh qualification status is `REVIEWED_AUTHORITY` for the frozen synthetic
fixture/profile scope. It removes the sole remaining TASK172 entry blocker and
sets `TASK172_ENTRY_AUTHORITY_COMPLETE=true`. This does not authorize
TASK172 implementation, TASK173/TASK174 solves, Ready, or Merge. No production
code changed; no mesh policy or precision policy was changed.

## Artifacts and validation

The machine-readable receipt and full results are linked through the append-only
`r103_extension`. The results artifact contains every mesh level, threshold
tuple, reference-aware metric, wall-extrema value, runtime, status, and replay
hash. Exact-final-head CI details are recorded in the final task receipt.

Validation includes predecessor/PR identity, R95–R102 frozen artifact replay,
R99 failure replay, full dual-runtime mesh and threshold matrices, uncertainty
propagation, R98 overlay use, cross-runtime classification, deterministic
replay, canonical hashes, historical immutability, manifest, Ruff, formatting,
mypy, diff allowlist, and `git diff --check`. A local full pytest run completed
with `6 failed, 6774 passed, 9 skipped, 70 errors` in 162.48 seconds. The six
failures were five `tests/ci/test_outcome_plugin.py::test_p04_*` node-id
expectation failures and the existing A01 test rejecting this checkout's
`/private/tmp/...` path; the 70 TASK164 release-demo setup errors observed its
dual-runtime status as `BLOCKED` in this uncommitted worktree. No tests or
production files were changed to mask these outcomes. Exact-final-head CI is
therefore required and is reported separately; this document does not call the
local full pytest run a pass.

Next gate: `AUTHORIZE_TASK172_IMPLEMENTATION_START_ONLY`. It is recorded as a
possible owner-authorized next step, not executed or authorized here.
