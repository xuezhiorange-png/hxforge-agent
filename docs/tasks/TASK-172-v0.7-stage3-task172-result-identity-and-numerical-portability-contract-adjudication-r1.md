# TASK172 result identity and numerical portability contract adjudication R1

TASK_ID=STAGE3_TASK172_RESULT_IDENTITY_AND_NUMERICAL_PORTABILITY_CONTRACT_ADJUDICATION_R1
MODE=AUTHORITY_CONTRACT_ADJUDICATION_ONLY
RESULT=PASS_PLATFORM_NATIVE_IDENTITY_CONTRACT
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
SOURCE_HEAD=8d8666826f222f052270ec7fa5d2e8111c853969

## Decision

The reviewed contract requires deterministic direct initialization and exact replay of a reviewed profile within a fixed execution environment. It does not require byte-identical TASK172 results across every supported operating system, Python, SciPy, or native-library build.

TASK172 result hashes are canonical hashes of the actual result projection bound to the request hash. That projection deliberately includes provider snapshot identities and native numerical/solver outputs, but does not include a platform fingerprint. The most accurate existing scope is therefore PLATFORM_NATIVE_RESULT_IDENTITY: exact content identity for the result produced in an environment, not a global cross-platform identity and not an explicitly environment-qualified ID.

The observed 0/68 macOS-to-Linux exact result-hash match is not, by itself, an authority violation. Exact same-environment replay remains required. Cross-platform portability is semantic: identical engineering request/authority identity, valid result and original R98 acceptance in each environment, consistent physical direction/order/domain/correlation guards, and a separately frozen numerical-output envelope. The observed deltas below are characterization, not new tolerances.

This resolves the identity-contract question only. DOGBOX_AUTHORITY_ACCEPTED=false; no fallback was implemented, no solver or production mesh was run, and no TASK175 work was performed.

R94_SOLVER_PROFILE_HASH=81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec
R98_OVERLAY_HASH=54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78
R98_C_ROUND=1.0

## Authority trace

1. Stage-1 numerical authority bundle, section D1, reuses R94 and records DETERMINISM_REQUIREMENT=DETERMINISTIC_DIRECT_INITIALIZATION_AND_REPLAYABLE_REVIEWED_PROFILE. The bundle classifies this as reused reviewed authority. It does not say all platforms must emit byte-identical results. See TASK-172-v0.7-stage1-pre-runtime-authority-bundle-r1.md:80-83 and evidence/TASK-172-stage1-pre-runtime-authority-bundle-r1.json:594-600.
2. The supplied independent Stage-1 review accepts the reviewed authority bundle and authorizes entry to Stage 2. It is not a new solver execution and adds no cross-platform exact-hash clause. See TASK-172-v0.7-stage1-pre-runtime-authority-independent-review-r1.md:7-13 and evidence/TASK-172-stage1-independent-review-r1.json.
3. Stage-2 defines a strict TASK172 request and a canonical valid result or typed blocker; support, mesh, cell, and wall identities replay deterministically. That is request/result replay language, not a global OS/Python hash guarantee. See TASK-172-v0.7-stage2-task172-runtime-and-task174-hydraulics-r1.md:14-20.
4. R94 controls and R98 residual acceptance remain separately frozen. Their exact hashes are recorded below. No conclusion here changes R94 controls, R98 equations/bounds, or C_round.
5. The R92A fixed-fixture portability record reports same selected-output matrix hashes across its tested Python runtimes and describes those as observations on a fixed fixture matrix, not universal engineering bounds. It is evidence of a tested profile, not a global cross-OS result identity mandate. See TASK-172-v0.7-quantitative-numerical-profile-coverage-and-roundoff-robustness-r92a.md:31-41, 80-95.
6. The accepted Stage-3 R2 n=2 portability correction explicitly records HISTORICAL_N2_CLASSIFICATION_PORTABLE=false: the same trial was BLOCKED_RESIDUAL_ACCEPTANCE locally and a valid Task172LocalResult on Linux 3.11/3.12. Only residual-acceptance versus valid classification is characterized as environment-sensitive; other blockers remain fail-closed. See TASK-172-v0.7-stage3-task172-numerical-hole-tolerant-cell-root-resolution-r1.md:14-20.
7. The TMAX adjudication accepts identical CoolProp version, reference state, T/P, phase, and query type while retaining slightly different provider-output enthalpy and property snapshot hash. It explicitly says TP provider output is retained and may differ from frozen H_MAX. Consequently cross-platform property-snapshot hash equality is not required. See TASK-172-v0.7-stage3-tmax-tp-output-boundary-portability-adjudication-r1.md:5-13, 23-29, 35-42.
8. The runtime request projection binds engineering inputs, support/topology, property profile, R94/R98 hashes, and authority hashes. The result projection includes provider snapshot identities, solved values, transport outputs, residuals, and solver trace; the result ID is the result hash. See task172_local_runtime/service.py:116-184, 187-209, 761-842, 244-252.
9. TASK173 verifies the actual Task172 result hash and support/cell/wall identities on consumption. On successful admission it reruns the accepted mesh in the same execution and compares mesh hash, face IDs, and local Task172 result hashes. This is exact in-execution replay, not a cross-platform hash comparison. See task173_integrated_rating/service.py:1265-1282 and 2553-2572. The pinned hash in task173_integrated_rating/replay.py:52, 218-250 protects one serialized Stage-2 native reference payload and its replay; it is not a requirement that every live result hash match across platforms.

## Result-hash projection and sensitivity

The canonical result hash is SHA-256 over the schema version, request hash, and closed result projection. The result ID is urn:hxforge:task172:<result_hash>. The projection does not include an OS/Python/SciPy identity field. Therefore identical projection bytes can share an ID across platforms; different native outputs naturally produce different IDs.

The result projection helper omits schema_version, status, request_hash, result_hash, result_id, warnings, and blockers from its inner field map; schema_version and request_hash are bound by the outer hash object. This does not weaken same-environment result/hash replay or the typed-valid-result contract.

| Projection fields | Classification | Cross-platform expectation |
| --- | --- | --- |
| case/revision, topology and TASK171 identities, ownership/definition hashes, support/segment/mesh/subdivision/tube-cell/shell-cell/wall-interface identities, bulk T, engineering profile and authority hashes, material/wall/cylindrical/correlation IDs | ENGINEERING_INPUT_IDENTITY | Exact for the same canonical request and frozen authority chain |
| Four tube/shell bulk and wall property snapshot identities | NATIVE_PROVIDER_OUTPUT_IDENTITY | Must replay in the producing environment; exact cross-platform equality is not required by the adjudicated property precedent |
| signed q, inner/outer wall T, both HTCs, three thermal resistances, three-residual vector, Re/Pr values, shell J_mu | NUMERICAL_SOLUTION_OR_PROVIDER_OUTPUT | Must satisfy the same physical and unchanged R98 contract in each environment; exact bits are not a pre-existing cross-platform requirement |
| solver status, nfev, residual callback count | SOLVER_TRACE_OUTPUT | Replay exactly in a fixed environment; trace equality across solver/library environments is not required |
| request hash, R94/R98 hashes, property-profile ID/hash, model/correlation/wall authority IDs and hashes | EXPECTED_CANONICAL_INVARIANT | Exact when the engineering request and authority inputs are the same |

The hash-sensitive platform-dependent fields are therefore the four snapshot identities; q and wall temperatures; HTCs; resistances; residuals; Re/Pr/J_mu; solver status, nfev, and callback count. The numerical profile and authority identifiers themselves remain invariant. A changed native output is not normalized, rounded, clipped, or removed from provenance.

## 68-request field comparison

The local comparison fixture has 68 unique request hashes (18 stored in the characterization fixture plus 50 in the fresh n=8/n=16 fixture); the exact-head Linux CI report has the same 68 unique hashes. Request hash equality binds the canonical physical request, support projection, topology, property profile, and engineering authority projection. Derived support identities therefore replay from the same inputs, although the local fixture does not separately retain every derived support ID as a comparison column.

| Metric, local macOS versus exact-head Linux PR-head Python 3.11 | Result |
| --- | ---: |
| Request hash / canonical engineering request match | 68/68 |
| Exact Task172 result hash match | 0/68 |
| Four property snapshot identity fields equal | 0/272 |
| Raw local property snapshot hash comparison | UNAVAILABLE; local committed corpus stores snapshot identities, not a separate raw-hash array |
| Final candidate validation status match | 68/68 VALIDATED |
| Original R98 acceptance | 68/68 pass |
| Signed-q direction match | 68/68 |
| Physical wall ordering | 68/68 |
| Same final solver status string | 59/68 |
| Same nfev | 68/68 |
| Same callback count | 66/68 |
| Maximum absolute q delta | 3.8335201679728925e-10 W |
| Maximum relative q delta | 2.581475744081614e-13 |
| Maximum absolute inner-wall-temperature delta | 1.1368683772161603e-13 K |
| Maximum absolute outer-wall-temperature delta | 1.7053025658242404e-13 K |
| Maximum absolute residual-component delta | 1.0447820386616513e-9 W |
| HTC, Re/Pr, and J_mu delta | UNAVAILABLE; local committed 68-row fixture does not retain these fields |

Across the Linux PR-head/merge-ref Python 3.11/3.12 artifacts, the 68 final candidate result-hash vectors match exactly. The two Linux corpus rows that were baseline residual-acceptance holes use the proposed fallback; the other 66 bypass it. The local macOS corpus has 68 baseline-valid rows and bypasses fallback throughout. This is a solver-path/runtime characterization, not accepted fallback authority.

The aggregate exact-hash mismatch is BITWISE_RESULT_IDENTITY divergence. The exact request match, 68/68 valid/R98 outcomes, heat-flow direction, wall order, and tiny observed numeric deltas are SEMANTIC_PORTABILITY evidence. The observed deltas are not adopted as tolerances here.

## Six n=32 targets and historical n=16 upper endpoint

For the six fixed n=32 requests, local TRF returned residual-acceptance blockers and the test-only original-seed dogbox candidate recovered them 6/6 under unchanged R98. Linux TRF returned valid results for all six and correctly bypassed fallback. Both paths ended VALIDATED, passed the original R98 checks, had the same heat-flow sign and physical guards, and replayed their own result identities. Semantic final-outcome match is 6/6; result-hash match is 0/6. Local wall-temperature values were not retained in the committed target summary, so target-specific Twi/Two deltas are not asserted.

| Request hash | Local candidate q / F(q) W | Linux baseline q / F(q) W | Final semantic outcome |
| --- | ---: | ---: | --- |
| 91c13f7949d32d90de13f95b14b2fc521f822c13f009ea6d132f965936cbb75f | 279.6428084422918 / 12846.8783324861082 | 279.64280844231325 / 12846.87833248608675 | VALIDATED; R98 pass; same sign/order |
| 946e8d83c8052f3c1db6f8aa31793f2b0b1523f7e392a1fa9e1da675daadde85 | 278.4621115308888 / 11960.2358512375112 | 278.4621115308767 / 11960.2358512375233 | VALIDATED; R98 pass; same sign/order |
| 0b1a138aa86081e91b23d814fd9309c14ae0d8087bdff230b41ca1cf9dfb9d9a | 282.8367069664459 / -1.0836735327719 | 282.8367069664438 / -1.0836735327698 | VALIDATED; R98 pass; same sign/order |
| 5fd98bd16cf306447b5ba359f44078d4dedca27d861d5573a0cafc4eeab2d0d3 | 282.8351020677846 / 0.12406592682116 | 282.83510206779323 / 0.12406592681253 | VALIDATED; R98 pass; same sign/order |
| 3ffebffa5aaf4957cd4d743e8530885795831d29328b5a2fc63e55287d08720d | 281.7082529109981 / -281.7082529109981 | 281.70825291103137 / -281.70825291103137 | VALIDATED; R98 pass; same sign/order |
| a52cda0abab920f9fd3a853e0ba3f3fa4289c38c88768bcda054377af08b70ec | 279.2674742343681 / 1555.6336815674819 | 279.2674742343595 / 1555.6336815674905 | VALIDATED; R98 pass; same sign/order |

For the historical n=16 upper-endpoint request 22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970, local candidate F(q)=-592.2898790517881 W and Linux native F(q)=-592.2898790517623 W. Both are valid, shell-capacity-binding upper endpoints with F<0; both take the existing valid-upper shell-capacity low-side classification. N16 final physical classification matches; R3 is unchanged and its hole trigger is inapplicable when the endpoint is valid.

## Adjudicated contract

| Candidate | Decision |
| --- | --- |
| CONTRACT_A_BITWISE_GLOBAL_IDENTITY | Reject. No pre-existing authority says this; it conflicts with retained platform-dependent TP provider output/property snapshots and is not the behavior established by current hash replay. |
| CONTRACT_B_ENVIRONMENT_LOCAL_EXACT_REPLAY | Required. Same frozen environment, same exact request and dependency/provider stack must replay the exact canonical result bytes/hash/ID. Existing tests assert this directly. |
| CONTRACT_C_ENGINEERING_SEMANTIC_PORTABILITY | Adopt as the cross-platform comparison contract. Require exact engineering request/authority identity; independently valid native Task172 results; unchanged original R98 pass; same approved physical direction, wall order, domain, property profile, and correlations; and numerical outputs inside a prospectively reviewed, explicitly declared portability envelope. Do not infer an envelope from this report's observed extrema. |
| CONTRACT_D_DUAL_IDENTITY_MODEL | Not needed or authorized now. The current native result hash already addresses exact native output content. An engineering-equivalence ID/schema would be a separate design proposal only if a downstream use case requires one. |

NATIVE_SOLVER_CLASSIFICATION_IS_ALLOWED_TO_DIFFER_BY_ENVIRONMENT=true, but only for the previously observed valid-versus-BLOCKED_RESIDUAL_ACCEPTANCE numerical boundary. It is not permission to downgrade non-residual blockers or accept blocked diagnostics.

TASK173 checks a Task172 result against its own request/result/support identity replay. Successful production admission repeats the accepted mesh and compares IDs/hashes inside that execution. No frozen cross-platform expected hash exists for every live TASK172 cell, and the mesh convergence policy compares thermal observables, not result IDs across machines. The one pinned Stage-2 reference hash protects a saved native reference payload.

PREEXISTING_DETERMINISM_REQUIREMENT=DETERMINISTIC_DIRECT_INITIALIZATION_AND_REPLAYABLE_REVIEWED_PROFILE
CROSS_PLATFORM_EXACT_RESULT_IDENTITY_PREEXISTING_REQUIREMENT=false
TASK172_RESULT_IDENTITY_SCOPE=PLATFORM_NATIVE_RESULT_IDENTITY
PROPERTY_SNAPSHOT_HASH_CROSS_PLATFORM_EXACTNESS_REQUIRED=false
NATIVE_SOLVER_CLASSIFICATION_CROSS_PLATFORM_EXACTNESS_REQUIRED=false
TASK173_REQUIRES_CROSS_PLATFORM_TASK172_RESULT_HASH_MATCH=false
CROSS_PLATFORM_HASH_DIVERGENCE_DOES_NOT_BY_ITSELF_BREAK_TASK173_CONTRACT=true
ADJUDICATED_PORTABILITY_CONTRACT=CONTRACT_B_ENVIRONMENT_LOCAL_EXACT_REPLAY_PLUS_CONTRACT_C_ENGINEERING_SEMANTIC_PORTABILITY
DOGBOX_AUTHORITY_ACCEPTED=false
CORRECTION_IMPLEMENTED=false
PRODUCTION_MESH_REEXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
NEXT_GATE=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_AUTHORITY_REASSESSMENT_UNDER_ADJUDICATED_PORTABILITY_CONTRACT_R1

## Validation and change boundary

The source head is exact and the worktree was clean at preflight. Exact-head CI run 36965219941 is for the authorized source head 8d8666826f222f052270ec7fa5d2e8111c853969: 50 jobs, 45 success, 5 skipped, 0 failed, 0 cancelled, final gate SUCCESS. Its four PR-head/merge-ref Python 3.11/3.12 producer bundles provide the matrix used above.

This adjudication adds no production, test, workflow, dependency, lockfile, R94, R98, TASK173, or registry change. The two requested evidence files are present in the local worktree but uncommitted; no commit, push, or PR metadata update was authorized or performed. The exact-head CI applies to the unchanged source head and does not include these new evidence files. This record does not promote the proposed dogbox architecture or authorize the next gate.

Machine-readable evidence: evidence/TASK-172-stage3-task172-result-identity-and-numerical-portability-contract-adjudication-r1.json.
