# TASK172 Stage-3 TMAX TP-output boundary portability adjudication R1

## Outcome

The four Linux CI observations agree across PR-head and merge-ref, and across CPython 3.11 and 3.12. At T=300 K, P=101325 Pa, the valid liquid TP state retains CoolProp's enthalpy output of 112654.89965464505 J/kg, which is 1.879E-8 J/kg above frozen H_MAX=112654.89965462626 J/kg. Local macOS / CPython 3.14.5 returns the frozen value exactly.

The accepted authority distinguishes the coordinates: the approved property domain is expressed in T, P, and phase; TP enthalpy is provider output and is retained. H_MAX is a hard upper bound for a supplied PH/shooting enthalpy coordinate, not a universal clamp on TP output. The existing test for the exact upper endpoint requires a TP result with provider enthalpy retained, while the PH pre-backend test requires any input above H_MAX to be rejected.

At q=0, propagation is an identity transform. Requiring a new PH reconstruction of the unchanged, already-valid TP state is not physically necessary and reinterprets provider output as an independent PH coordinate. The narrow candidate correction is exact-zero identity preservation (Option D); this adjudication does not implement it.

The exposure is not mathematically limited to q=0. On the Linux observation, Q_to_enter_H_MAX = m_tube × (h_TP − H_MAX) = 2.2548E-7 W. The current downstream-face guard blocks q below this amount. For q at or above that amount but below 4.5096E-7 W, the face is within H_MAX while the cell midpoint enthalpy remains above H_MAX and is rejected as a PH reconstruction coordinate. At twice Q_to_enter_H_MAX, the midpoint reaches H_MAX. Therefore Option D is explicitly limited to exact q=0 and does not claim to resolve the small-positive-q interval.

No epsilon, clipping, dynamic H_MAX, or production behavior change is authorized or performed in this adjudication.

## Frozen contracts and source trace

- In task173_integrated_rating/service.py, _checked_thermo validates T/P/liquid/query type; its source comment says the returned enthalpy is provider output and is not a second TP coordinate to clip or bound.
- _state_from_enthalpy rejects an input below H_MIN or above H_MAX before calling state_ph. At exact H_MAX it uses the reviewed TP boundary producer and retains that output.
- tests/exchangers/shell_tube/test_task173_integrated_rating.py::test_exact_reviewed_upper_property_endpoint_uses_tp_not_clipped_ph verifies T=300 K, reference pressure, liquid phase, TP query type, and retained provider output.
- test_ph_input_above_reviewed_upper_enthalpy_is_rejected_before_backend verifies an above-H_MAX PH input is blocked without calling the provider.
- _cell_evaluation at q=0 copies the upstream TP enthalpy into the tube downstream face. The face guard compares it with H_MAX before any property call; the midpoint would also be above H_MAX if reached.

This yields the adjudicated role:

H_MAX_ROLE=PH_INPUT_COORDINATE_BOUND_ONLY
H_MAX_ALSO_BOUNDS_OUTER_SHOOTING_COORDINATE=true
H_MAX_IS_UNIVERSAL_PROVIDER_OUTPUT_BOUND=false
TP_PROVIDER_OUTPUT_ALLOWED_TO_DIFFER_FROM_FROZEN_HMAX=true
PH_INPUT_ABOVE_HMAX_REJECTED_PRE_BACKEND=true

## Platform matrix

The complete machine-readable matrix, including temperatures, pressure, phase, query type, enthalpy, H-bound deltas, snapshot hashes, q probes, and TP-to-PH diagnostic outputs, is in docs/tasks/evidence/TASK-172-stage3-tmax-tp-output-boundary-portability-adjudication-r1.json.

| Environment | Runtime | TMAX TP h (J/kg) | h − H_MAX (J/kg) | TMAX snapshot hash | TMIN TP h (J/kg) | h − H_MIN (J/kg) | TMIN snapshot hash |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| Local macOS | CPython 3.14.5, CoolProp 8.0.0 | 112654.89965462626 | 0E-11 | 4c2a817b2b9e27afb3fe1aa0e7e3eb6aa4103131789d6d644511f6636923cba6 | 104920.11980926784 | 0E-11 | e7c8a9924bbfd5edd29f40ed204748f741a106c801bcb6d0a388322233018fdf |
| PR-head py311 | CPython 3.11.16, Linux, CoolProp 8.0.0 | 112654.89965464505 | 1.879E-8 | 974e1456cc1fa3ca99e78a9ee70ee43df0273358892eb4ee1c4d2e6ee0fbb5e3 | 104920.11980935509 | 8.725E-8 | 635b1e9c4473e98d70c3cb04fe0a5f47ef48994e13bb50daaf1a2f34726aa3d6 |
| PR-head py312 | CPython 3.12.14, Linux, CoolProp 8.0.0 | 112654.89965464505 | 1.879E-8 | 974e1456cc1fa3ca99e78a9ee70ee43df0273358892eb4ee1c4d2e6ee0fbb5e3 | 104920.11980935509 | 8.725E-8 | 635b1e9c4473e98d70c3cb04fe0a5f47ef48994e13bb50daaf1a2f34726aa3d6 |
| Merge-ref py311 | CPython 3.11.16, Linux, CoolProp 8.0.0 | 112654.89965464505 | 1.879E-8 | 974e1456cc1fa3ca99e78a9ee70ee43df0273358892eb4ee1c4d2e6ee0fbb5e3 | 104920.11980935509 | 8.725E-8 | 635b1e9c4473e98d70c3cb04fe0a5f47ef48994e13bb50daaf1a2f34726aa3d6 |
| Merge-ref py312 | CPython 3.12.14, Linux, CoolProp 8.0.0 | 112654.89965464505 | 1.879E-8 | 974e1456cc1fa3ca99e78a9ee70ee43df0273358892eb4ee1c4d2e6ee0fbb5e3 | 104920.11980935509 | 8.725E-8 | 635b1e9c4473e98d70c3cb04fe0a5f47ef48994e13bb50daaf1a2f34726aa3d6 |

All four Linux observations are identical at the recorded precision and hash level. The merge-ref and PR-head outputs match, and Python 3.11 and 3.12 match. The local macOS output differs from Linux at both endpoints.

The TMIN scan detects an 8.725E-8 J/kg provider-output delta on Linux. It does not trigger the current lower-bound guard, which rejects values below H_MIN. This is a bounded risk observation only; H_MIN semantics are not changed or resolved here.

## q=0 and small-positive-q analysis

For q exactly zero, tube and shell propagated enthalpies equal their upstream values. Thus the thermodynamic state transform is identity, and no fresh PH inversion is physically required. Reusing the upstream thermodynamic snapshot does not mean reusing the same face identity: face context remains encoded separately.

For the Linux TMAX output:

- h_TP − H_MAX = 1.879E-8 J/kg.
- Q_to_enter_H_MAX = 12 kg/s × (h_TP − H_MAX) = 2.2548E-7 W.
- At q=0, the tube downstream face remains above H_MAX.
- At q=0.5Q, the downstream face is still above H_MAX.
- At q=Q, the downstream face reaches H_MAX, but the cell midpoint remains 9.395E-9 J/kg above H_MAX.
- At q=2Q, the midpoint reaches H_MAX.

The test-emitted would_current_precheck_block field describes only the downstream-face precheck. It is false at q=Q, but that does not mean the entire cell evaluation is admissible: the midpoint PH-coordinate guard still blocks until q reaches 2Q. Consequently:

PORTABILITY_EXPOSURE_STRICTLY_Q_ZERO_ONLY=false
OPTION_D_SCOPE=EXACT_Q_ZERO_IDENTITY_ONLY
OPTION_D_SOLVES_ALL_SMALL_POSITIVE_Q_EXPOSURE=false

## Correction-option adjudication

| Option | Authority assessment | Recommendation |
| --- | --- | --- |
| A: add epsilon to H_MAX | Arbitrary tolerance; weakens the hard PH coordinate bound and risks platform dependence. | No |
| B: clip TP output | Falsifies provider output and breaks snapshot provenance/identity. | No |
| C: derive a local H_MAX from the provider | Makes the frozen authority and canonical inputs runtime-dependent; changes identities/hashes across platforms. | No |
| D: preserve state identity for exact q=0 | Preserves the already-authorized TP state, avoids an unnecessary PH reinterpretation, leaves H_MAX and TASK172 acceptance unchanged. Does not solve the separate small-positive interval. | Yes, exact-zero scope only |

Option D preserves the upstream property snapshot and thermodynamic identity. Face identities remain distinct by their contextual coordinates/roles. TASK172 request/result and TASK173 result hashes can change deterministically when the bound local state changes from an unnecessary PH reconstruction to the existing TP state; that is identity propagation, not a change to TASK172 acceptance or physical state.

## CI and validation

Stage-1 diagnostic commit: d328642ab77e0516c11fb2a788e80de17692ecd5.

Exact-head CI run 36817909105 used that exact head and completed with 48 jobs: 31 success, 11 skipped, 6 failed, 0 cancelled. The four PR/merge Python matrix shards each exposed the intentional boundary diagnostic and the existing R3 downstream assertion. The R3 test fails before its target support because the first physical lower-endpoint q=0 evaluation blocks; the target is not reached. The lint job failed only at pip-audit, reporting three known vulnerabilities in urllib3 2.7.0 (CVE-2026-97687, CVE-2026-97688, CVE-2026-97689). Setup, checkout, runtime installation, merge-ref materialization, matrix collection, and artifact upload completed; no infrastructure failure was observed. The final gate consequently failed.

Local validation before the evidence-only closeout:

- Focused TASK173 tests: PASS.
- Full shell-tube suite: PASS.
- Ruff, format check, mypy, manifest D==M (259=259), uv lock check, and git diff check: PASS.
- pip-audit: FAIL, three reported urllib3 2.7.0 vulnerabilities (CVE-2026-97687, CVE-2026-97688, CVE-2026-97689). The project distribution heat-exchanger-design-agent==0.6.0 was skipped because it is not found on PyPI. No dependency or lockfile change is authorized.

The post-evidence-commit exact-head CI is required and its exact run identity is reported in the final task receipt; it cannot be pre-populated in the evidence commit that it validates.

## Scope and lifecycle

This is a semantic adjudication only. No production code, property constants, R3 classification, TASK172 acceptance, R98, mesh policy, dependency, lockfile, or workflow was changed. No production mesh was run; no TASK173 result or mesh admission exists; TASK175, Ready, and Merge remain false.

Adjudicated candidate:

H_MAX_ROLE=PH_INPUT_COORDINATE_BOUND_ONLY
TP_PROVIDER_OUTPUT_ALLOWED_TO_DIFFER_FROM_FROZEN_HMAX=true
ZERO_Q_STATE_IS_IDENTITY_TRANSFORM=true
ZERO_Q_SHOULD_REQUIRE_NEW_PH_RECONSTRUCTION=false
RECOMMENDED_CORRECTION_OPTION=D
NEXT_GATE=STAGE3_TMAX_ZERO_Q_STATE_IDENTITY_PORTABILITY_CORRECTION_R1

This candidate is not a production change or self-approval.
