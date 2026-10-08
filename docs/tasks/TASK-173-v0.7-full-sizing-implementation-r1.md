# TASK173 v0.7 Full Sizing Implementation R1 — final continuation disposition

```text
TASK_ID=STAGE3_TASK173_FULL_SIZING_IMPLEMENTATION_R1
RESULT=BLOCKED_TASK173_FULL_SIZING_IMPLEMENTATION
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
AUTHORIZED_SOURCE_HEAD=b1f89c9df9c06ee7d7f513cfad7f0ba8f65e0768
FINAL_HEAD=b1f89c9df9c06ee7d7f513cfad7f0ba8f65e0768
ATTEMPT_COUNT=4
ATTEMPT_1_RESULT=BLOCKED_IMPLEMENTATION_VALIDATION_INCOMPLETE
ATTEMPT_1_FULL_CANDIDATE_RATING_COUNT=0
ATTEMPT_2_RESULT=BLOCKED_C3_DOMAIN_VALIDATION_FIXTURE
ATTEMPT_2_FULL_CANDIDATE_RATING_COUNT=0
ATTEMPT_2_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
ATTEMPT_2_STRUCTURALLY_VALID_CANDIDATE_COUNT=2
ATTEMPT_2_C3_BLOCKED_CANDIDATE_COUNT=2
ATTEMPT_2_BLOCKER=BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE
TASK174_AUTHORITY_IDENTITY_WIRING_FIXED=true
ATTEMPT_3_PREFLIGHT=BLOCKED_CANDIDATE_BAFFLE_GEOMETRY
ATTEMPT_3_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
ATTEMPT_3_BLOCKER_STAGE=ATTEMPT_3_CANDIDATE_NATIVE_TASK024_PREFLIGHT
ATTEMPT_3_BLOCKER_CODE=BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY
FIRST_NEW_BLOCKER_STAGE=ATTEMPT_4_CANDIDATE_RATING_CELL_ROOT
FIRST_NEW_BLOCKER_CODE=PRECISION_FLOOR_UNRESOLVED
FIRST_NEW_BLOCKER_DETAILS=Candidate A exact-request diagnostic replay failed at mesh n=1 with CELL_ROOT_PRECISION_FLOOR_REACHED; q bracket endpoints were 12234.634520032956 and 12234.634520032958 W after 3279 Task172 local evaluations and zero numerical holes.
COMMIT_CREATED=false
PUSH_PERFORMED=false
EXACT_HEAD_CI_RUN=false
```

## Outcome

The separate v0.7 Sizing API, candidate-native producer adapters, candidate
Rating sibling, ledger/ranking models, provenance construction, and focused
contract tests were developed locally. This is not a PASS: the mandatory public
production-path proof did not establish that two candidates reach full v0.7
Rating. No Sizing implementation completion is claimed.

The R2 authority package remains the sole authority basis:

```text
AUTHORITY_PACKAGE_ID=V07-T173-SIZING-AUTHORITY-PACKAGE-R2
AUTHORITY_PACKAGE_HASH=750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9
INDEPENDENT_REVIEW_EVIDENCE_HASH=7e9ec9acb507cc8d731a5079c881540187bb2068c4c6c39f139b4190b7bd5a3c
EFFECTIVE_AUTHORITY_LIFECYCLE=REVIEWED_AUTHORITY
AUTHORITY_ACCEPTED=true
```

## First blocking validation result

### ATTEMPT_1 — preserved history

One public `validate_sizing_request()` execution used a fixed,
implementation-validation-only request with two predeclared tube lengths,
4.85 m and 4.90 m. Requirement values were fixed before execution at 10,000 W
required duty and 1,200 Pa maximum tube and shell pressure drops. They were
explicitly not Golden or release authority.

```text
SIZING_REQUEST_HASH=1a810a2dbb63ad11c267f400a2ee04580bb29e28aee08fff9ea8067bc7a33e7d
CANDIDATE_COUNT=2
ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
PASS_COUNT=0
WARN_COUNT=0
BLOCKED_COUNT=2
```

The 4.90 m candidate was retained as BLOCKED by native TASK024 because the
selected four-baffle, uniform 0.97 m spacing sequence requires exact closure at
4.85 m; the producer returned `CANDIDATE_GEOMETRY_INVALID` with the detail
“tube length must exactly close the selected uniform baffle spacing.” This is
the existing fail-closed producer behavior. Candidate dimensions were not
changed after observing the result.

The 4.85 m candidate was stopped before Rating by a local implementation defect:
the candidate TASK174 request constructor omitted required R2 package/transfer
identity fields. Those fields have since been added using the frozen R2 hashes.
The public two-candidate request was not rerun after that code correction. As a
result, there is no post-correction evidence that even one candidate completes
TASK174 and Rating, and the fixed request still contains only one candidate
whose geometry passed TASK024. The required two actual full Ratings therefore
remain unproven.

```text
ATTEMPT_1_BLOCKER_CLASS=IMPLEMENTATION_VALIDATION_INCOMPLETE
ATTEMPT_1_4_90M_0_97M=CORRECTLY_REJECTED_BY_EXACT_TASK024_SPAN_CLOSURE
ATTEMPT_1_4_85M_TASK174_BLOCKER=INITIAL_R2_AUTHORITY_IDENTITY_WIRING_OMISSION
ATTEMPT_1_ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
NO_CANDIDATE_SPACE_RETUNING_AFTER_OBSERVED_THERMAL_OUTPUT=true
```

## ATTEMPT_2 — owner-frozen validation space, before public execution

The focused native TASK174 boundary now succeeds for the structurally valid
4.85 m / 0.97 m candidate using real TASK029, TASK166, candidate TASK171, and
the non-mocked candidate TASK174 validator. The implementation correction maps
TASK166's actual `result_id` / `result_hash` evidence fields to candidate-native
TASK020/021/022/024 identities.

Before invoking the public Sizing API, the validation-only candidate space is
frozen as follows. Its source class is the R2-permitted
`OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET`; it is not a Golden, release, or
production business requirement. All attempt-1 dimensions remain fixed except
the explicitly authorized tube-length and baffle-spacing sets.

```text
VALIDATION_CANDIDATE_SPACE_AUTHORITY_ID=V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R2
VALIDATION_CANDIDATE_SPACE_AUTHORITY_HASH=062b8166181a182d1e17ca45cfac708343379d09d8ab109d7a5e475dd0c236c9
VALIDATION_CANDIDATE_SPACE_SOURCE_CLASS=OWNER_APPROVED_PROJECT_DEFINED_DISCRETE_SET
VALIDATION_CANDIDATE_SPACE_CLASSIFICATION=IMPLEMENTATION_VALIDATION_ONLY_NOT_GOLDEN_NOT_RELEASE_AUTHORITY
TUBE_LENGTH_M=4.85,4.90
TUBE_LENGTH_DISCRETE_AUTHORITY_HASH=183f41c1baf8607e29a29cce4bdf2398da32e41f1d7a2cc6f067e2d7c527b649
BAFFLE_SPACING_M=0.97,0.98
BAFFLE_SPACING_DISCRETE_AUTHORITY_HASH=34c36ee0a84d7260908acf55e0c5d68be93a4c49bcd31620aa5f011956fd7f12
BAFFLE_COUNT=4
TASK168_CANDIDATE_SPACE_HASH=8ec8117ef570399626dc28ab7bd59c4f674a86202e65ea2547d69620a79ee0d0
SIZING_REQUEST_HASH=a49f16a9f4124077996a1fc052387024b9181139d04202b13d98d0f771e8fcdf
EXPECTED_STRUCTURALLY_ADMITTED_PAIRS=(4.85,0.97),(4.90,0.98)
EXPECTED_STRUCTURALLY_BLOCKED_PAIRS=(4.85,0.98),(4.90,0.97)
REQUIRED_DUTY_W=10000
MAX_TUBE_DP_PA=1200
MAX_SHELL_DP_PA=1200
CANDIDATE_SPACE_FROZEN_BEFORE_PUBLIC_EXECUTION=true
PUBLIC_SIZING_EXECUTION_STARTED=true
```

The exact uniform-spacing closure is `tube_length = spacing × (baffle_count +
1)`, i.e. five intervals for four baffles. Thus the two cross-pairs are
preclassified as structural blockers without a thermal or hydraulic solve. No
candidate will be added, replaced, or tuned after execution starts.

### Attempt 2 public execution 1 — preserved implementation defect

The first frozen four-candidate public call completed and retained all four
records. The two cross-pairs were blocked at native TASK024 as predicted. The
two structurally valid candidates both reached the actual candidate Rating
entry, but its candidate context failed closed before numerical Rating because
`CandidateShellFlowAuthority` compared TASK166 evidence using nonexistent
geometry-specific keys instead of the producer's `result_id` / `result_hash`
keys. Consequently this call produced zero valid full v0.7 candidate Ratings.
This is an implementation wiring defect, not an authority or physics gap. The
validator now compares both producer IDs and hashes to the candidate-native
TASK031 identity; the exact same candidate space, authorities, requirement
values, and Sizing request hash are retained for the continuation call.

```text
ATTEMPT_2_PUBLIC_EXECUTION_1_REQUEST_HASH=a49f16a9f4124077996a1fc052387024b9181139d04202b13d98d0f771e8fcdf
ATTEMPT_2_PUBLIC_EXECUTION_1_CANDIDATE_COUNT=4
ATTEMPT_2_PUBLIC_EXECUTION_1_ACTUAL_CANDIDATE_RATING_ENTRIES=2
ATTEMPT_2_PUBLIC_EXECUTION_1_VALID_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_2_PUBLIC_EXECUTION_1_RESULT_HASH=e6b6d0656fe3626d8f8418ae08bf940bf950794c1faa87c655dc88df71367b5c
ATTEMPT_2_PUBLIC_EXECUTION_1_BLOCKER=BLOCKED_TASK173_CANDIDATE_REQUEST_SCHEMA_INVALID
ATTEMPT_2_PUBLIC_EXECUTION_1_DIAGNOSTIC=CandidateShellFlowAuthority rejected valid candidate-native TASK031/TASK166 because its validator read the wrong TASK166 evidence keys
CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION_START=false
SECOND_PUBLIC_EXECUTION_AFTER_FIX=COMPLETED_BLOCKED_BY_CANDIDATE_TASK172_EVIDENCE_IDENTITY_WIRING
```

### Attempt 2 public execution 2 — preserved implementation defect

With the TASK166 evidence-key correction in place, the same request progressed
past `CandidateShellFlowAuthority` but failed in `CandidateThermalBinding`:
candidate TASK020/021/022/024 identities were compared against the wrong
TASK166 baffle-evidence key. This was another local identity-wiring defect,
not an authority change. The binding was corrected to compare native
`result_id`/`result_hash` values against the TASK171 candidate-native identity.
The candidate space and request remained byte-for-byte semantically frozen.
The execution's result hash was not retained in the persisted aggregate.

```text
ATTEMPT_2_PUBLIC_EXECUTION_2_REQUEST_HASH=a49f16a9f4124077996a1fc052387024b9181139d04202b13d98d0f771e8fcdf
ATTEMPT_2_PUBLIC_EXECUTION_2_CANDIDATE_COUNT=4
ATTEMPT_2_PUBLIC_EXECUTION_2_ACTUAL_CANDIDATE_RATING_ENTRIES=2
ATTEMPT_2_PUBLIC_EXECUTION_2_VALID_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_2_PUBLIC_EXECUTION_2_BLOCKER=BLOCKED_TASK173_CANDIDATE_REQUEST_SCHEMA_INVALID
ATTEMPT_2_PUBLIC_EXECUTION_2_DIAGNOSTIC=CandidateThermalBinding read the wrong TASK166 baffle-evidence identity key
ATTEMPT_2_PUBLIC_EXECUTION_2_RESULT_HASH=UNAVAILABLE_NOT_RETAINED
```

### Attempt 2 public execution 3 — genuine candidate applicability blocker

The third public execution used the unchanged four-candidate Cartesian space
after the candidate TASK172 mesh identity binding was corrected. All four
records were retained. Structural classification matched the frozen exact
TASK024 predictions: `(4.85, 0.97)` and `(4.90, 0.98)` were admitted, while
`(4.85, 0.98)` and `(4.90, 0.97)` were blocked by exact uniform-spacing span
closure.

Both admitted candidates reached the real candidate Rating entry, but each
Task172 call returned `BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE`, wrapped by the
Rating path as `BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE`. The existing
production guard at `task172_local_runtime/service.py` rejects a non-turbulent
tube regime before C3 evaluation. Under the reviewed R2 thermal-domain
contract, correlation applicability failure must block; this is not an
implementation-wiring defect and does not authorize changing the C3 domain.
Neither candidate produced a valid full v0.7 Rating result. The task therefore
stops here without replacing or adding candidates.

```text
ATTEMPT_2_PUBLIC_EXECUTION_COUNT=3
ATTEMPT_2_PUBLIC_EXECUTION_3_REQUEST_HASH=a49f16a9f4124077996a1fc052387024b9181139d04202b13d98d0f771e8fcdf
ATTEMPT_2_PUBLIC_EXECUTION_3_RESULT_HASH=de74c4102e3c70c3c585c13372b6175700eab9a226eb96d7f2c7422e2024d896
ATTEMPT_2_PUBLIC_EXECUTION_3_RESULT_ID=urn:hxforge:task173-sizing:de74c4102e3c70c3c585c13372b6175700eab9a226eb96d7f2c7422e2024d896
ATTEMPT_2_PUBLIC_EXECUTION_3_REQUEST_HASH_REPLAY=PASS
ATTEMPT_2_PUBLIC_EXECUTION_3_RESULT_HASH_REPLAY=PASS
ATTEMPT_2_PUBLIC_EXECUTION_3_RESULT_ID_BINDS_HASH=true
TOTAL_CANDIDATE_COUNT=4
STRUCTURALLY_ADMITTED_COUNT=2
STRUCTURALLY_BLOCKED_COUNT=2
ACTUAL_CANDIDATE_RATING_ENTRIES=2
ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
PASS_COUNT=0
WARN_COUNT=0
BLOCKED_COUNT=4
RECOMMENDABLE_COUNT=0
SELECTION_STATUS=NO_RECOMMENDABLE_CANDIDATE
VALIDATION_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
```

Final candidate ledger:

| Candidate | Frozen geometry | Outcome | Candidate Rating identity |
|---|---|---|---|
| `4070a34b-80b4-50fa-9630-5278bf9fe08d` / `65622a77…f7a52ee` | 4.85 m / 0.97 m / 4 baffles | structurally admitted; blocked `BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE` | request `72c540a7e4609275e249aa2f1f596151e146e3268ca62741306352de409d9713`; no valid result hash |
| `6f024633-3e2d-5ead-9ba6-3b196962cc75` / `d9e53e4f…d2ad8ed7e0` | 4.85 m / 0.98 m / 4 baffles | blocked at TASK024 exact span closure | not invoked |
| `fe5d4466-e184-534a-bfab-f0b6ed8fb536` / `49937f3b…7aae43ec5` | 4.90 m / 0.97 m / 4 baffles | blocked at TASK024 exact span closure | not invoked |
| `65ebeebb-06bc-5bcb-aacb-403f466afc87` / `3e4bc24e…55a8120` | 4.90 m / 0.98 m / 4 baffles | structurally admitted; blocked `BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE` | request `0c6e4935a7df7568daf71fd86be0492dc19cc41bbdf224935ecf5aacd57025dd`; no valid result hash |

## ATTEMPT_3 — reference-bound baffle-cut candidate preflight

Attempt 3 froze exactly two implementation-validation-only candidates before
any public Sizing execution. Only baffle cut varies; tube-side cross-section
and service dimensions are reference-bound. Requirement values remain the
previously frozen 10,000 W duty and 1,200 Pa tube/shell DP limits. This fixture
is not Golden, release, or production business authority.

```text
ATTEMPT_3_VALIDATION_SPACE_ID=V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R3
ATTEMPT_3_VALIDATION_SPACE_HASH=3b13b986984b2f10bd997be7a2b9be8696ab50da0fab8ed9fc69381ed58d1f50
ATTEMPT_3_BAFFLE_CUT_VALUES=0.25,0.30
ATTEMPT_3_BAFFLE_CUT_DISCRETE_AUTHORITY_HASH=528634ff9aebf445d961b542f0ee1aa67f31a56b34b07bb4147ff407d7646ea6
ATTEMPT_3_TASK168_CANDIDATE_SPACE_HASH=254ad24be6da9eeb6b964f5784641d16af72da30730614f363c0695a4fe7a453
ATTEMPT_3_SIZING_REQUEST_HASH=818406998f10dd112506f07351f9a2782191eb4dbc68dbaaee983e7ece4bb5fc
ATTEMPT_3_REQUIREMENT_AUTHORITY_HASH=3de2831cd4ebac24f0b5e1cdeb16558ebab5b38a73891891c396d925c8ff06a2
ATTEMPT_3_CANDIDATE_COUNT=2
ATTEMPT_3_OBSERVED_TASK024_VALID_COUNT=1
ATTEMPT_3_PREFLIGHT=BLOCKED
ATTEMPT_3_CANDIDATE_SPACE_FROZEN=true
ATTEMPT_3_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
PERFORMANCE_OUTPUT_USED_TO_SELECT_CANDIDATES=false
C3_APPLICABILITY_USED_TO_SELECT_VALIDATION_FIXTURE=true
POST_RESULT_PERFORMANCE_TUNING=false
```

Candidate A (`0.25`) has ID/hash
`742ddd39-f1ed-505f-8f25-4c23fe8a5929` /
`221d0b99f88e45d9df05f5f917b4f3687a43b51ad19343553f3fe2e5ffa36ef0`.
Its candidate-native TASK020/021/022 chain materialized, but TASK024 returned
`BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY` for 13 tube-hole/cut-boundary
intersections, minimum margin `-0.002292728463 m`; no TASK024 geometry result
was produced. Candidate B (`0.30`), ID/hash
`8da2db3a-1980-546c-a610-19735808aee3` /
`cd05f5bc5310e714e2043de2cefeb027cdf8b4191a099bf0a3bff541f7b9f873`, passed
TASK024 with result ID/hash
`55defa13-aa75-5fc1-bed5-298e157e794f` /
`1147bb329ce5f89b3cec80a418b39619b18cae28bee588bb1e3abfdfd1df7c3c`.
No invalid cut was rounded, snapped, or repaired.

Both preflight paths independently materialized TASK025 tube-side geometry:
ID `0.01575 m`, total parallel flow area `0.0492914415 m²`, 253 physical
tubes, one pass, and 12 kg/s. At 300 K and 101325 Pa, the actual property
provider and candidate-native geometry produced `Re=4491.2103`, `Pr=5.8559`,
`TURBULENT`, correlation `tube_turbulent_gnielinski` for both candidates.
Thus C3 preflight passed 2/2; this was not a Rating result. The unchanged TASK024
geometry guard is the first blocker, so the public Sizing API was not invoked,
no candidate Rating or candidate production mesh ran, and the count of valid
full v0.7 candidate Ratings remains zero.

```text
CANDIDATE_TUBE_GEOMETRY_PARITY_DEFECT=false
CANDIDATE_A_TASK024=BLOCKED_BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY
CANDIDATE_A_INTERSECTION_COUNT=13
CANDIDATE_A_MINIMUM_INTERSECTION_MARGIN_M=-0.002292728463
CANDIDATE_B_TASK024=VALID
C3_PREFLIGHT_PASS_COUNT=2
PUBLIC_SIZING_EXECUTION_STARTED=false
CANDIDATE_RATING_EXECUTED=false
ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_3_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
```

The separately authorized reference Rating replay recovery is still running
in the captured process/session and has not returned a result. It is not being
restarted; reference result identity remains unverified until that one call
returns.

## Checks completed

- Ruff format and lint on changed sizing/rating/TASK172/TASK174 code and the
  new sizing test module: PASS.
- Focused regressions for TASK168, TASK172, TASK173 Rating, TASK173 Sizing, and
  TASK174: PASS.
- New Sizing contract tests: strict request/authority-bound request identity,
  resource fail-closed behavior, unsupported-topology retention, deterministic
  ranking trace, and canonical result replay.
- The focused Rating regression module passed. The required full authoritative
  reference Rating replay recovery was launched once after code stabilization,
  following an exact frozen request-hash precheck. It remains active in captured
  session 44691; no final output has yet been captured. It has not been
  restarted, preserving the one-run limit.
- Full shell-tube, HTTP/API, mypy, manifest, pip-audit, locked sync, full matrix,
  commit, push, and exact-head CI: NOT RUN.

Existing reference identities remain the frozen target; this attempt did not
establish a completed full replay:

```text
REFERENCE_RATING_REQUEST_HASH=77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed
REFERENCE_RATING_RESULT_HASH=fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
REFERENCE_RATING_FULL_REPLAY=RUNNING_CAPTURED_SESSION_44691_NOT_COMPLETED
REFERENCE_RATING_IDENTITY_PRESERVED=NOT_ESTABLISHED
REFERENCE_RATING_REPLAY_RESTARTED=false
```

## Change and stop boundary

Changes remain local and uncommitted. Pre-existing handoff files remain
untouched. No TASK175 work, authority amendment, dependency/lock/workflow
change, Ready action, or Merge action was performed. The one authorized
reference Rating replay remains active and has not yielded a captured
completion; its final identity is unverified.
The implementation remains local and uncommitted. Full post-PASS validation,
commit, push, and CI were not performed because the mandatory multi-candidate
Rating condition failed. The next state is owner direction for the candidate
TASK024 native geometry blocker; no new authority or implementation task is
created.

```text
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_TASK173_SIZING_IMPLEMENTATION_BLOCKER
NEXT_GATE_EXECUTED=false
STOP=true
```

## ATTEMPT_4 — pre-Rating structural qualification protocol frozen

Attempt 3 remains immutable: two cuts passed C3 preflight, but cut `0.25`
was rejected by native TASK024 with 13 cut-boundary intersections and cut
`0.30` was the only TASK024-valid candidate. Public Sizing did not start.
This was correct structural rejection, not a TASK024 defect.

Before running Attempt 4 qualification, the fixture-construction protocol was
frozen. It evaluates every cut in Decimal ascending order, retains every
qualification outcome, and selects the first two cuts satisfying all
pre-Rating predicates. This policy is implementation-validation-only and is
not Golden, release, or business sizing authority.

```text
ATTEMPT_COUNT=4
ATTEMPT_3_RESULT=BLOCKED_STRUCTURAL_VALIDATION_FIXTURE
ATTEMPT_3_C3_PREFLIGHT_PASS_COUNT=2
ATTEMPT_3_CANDIDATE_A_CUT=0.25
ATTEMPT_3_CANDIDATE_A_TASK024=BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY
ATTEMPT_3_CANDIDATE_A_INTERSECTION_COUNT=13
ATTEMPT_3_CANDIDATE_B_CUT=0.30
ATTEMPT_3_CANDIDATE_B_TASK024=VALID
ATTEMPT_3_PUBLIC_SIZING_EXECUTION_STARTED=false
ATTEMPT_3_ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_3_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
ATTEMPT_4_QUALIFICATION_POLICY_ID=V07-T173-SIZING-IMPLEMENTATION-STRUCTURAL-QUALIFICATION-R1
ATTEMPT_4_QUALIFICATION_POLICY_HASH=2db2372815fbc7295fde129508def1ef794aa55b44a1226c1188312e63e0a887
ATTEMPT_4_QUALIFICATION_POOL_SIZE=31
ATTEMPT_4_POOL=0.200..0.350_STEP_0.005
PERFORMANCE_OUTPUT_USED_FOR_FIXTURE_SELECTION=false
ATTEMPT_4_QUALIFICATION_STATUS=PASS_16_QUALIFIED
ATTEMPT_4_QUALIFIED_CUT_COUNT=16
ATTEMPT_4_QUALIFIED_CUT_1=0.215
ATTEMPT_4_QUALIFIED_CUT_2=0.220
ATTEMPT_4_QUALIFICATION_LEDGER_HASH=aeac45600d17c811b4e873e4d3bf3a3085a1741ad1888837641b993cfa19980c
ATTEMPT_4_VALIDATION_SPACE_ID=V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R4
ATTEMPT_4_VALIDATION_SPACE_HASH=dd78fe36ceaa2b7e49d7c7264e07c3ba02a286114876b982f7a1b74cf91b9c01
ATTEMPT_4_SIZING_REQUEST_HASH=0d1964be99e5445605c602b20f4befeef0e16442128b21f55e615d14fc6b6f2b
ATTEMPT_4_CANDIDATE_SPACE_FROZEN=true
ATTEMPT_4_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
ATTEMPT_4_PUBLIC_SIZING_INVOCATION_COUNT=2
ATTEMPT_4_FIRST_PUBLIC_BLOCKER=SSPD_UNSUPPORTED_BAFFLE_CUT
TASK174_LEGACY_TASK034_WIRING_FIXED=true
ATTEMPT_4_CORRECTED_SIZING_RESULT_HASH=cffd3bb5d28500b78f1752a111cbccec5241deda893fe1c8d1257f2529d7c4ce
ATTEMPT_4_SIZING_REQUEST_HASH_REPLAY=PASS
ATTEMPT_4_SIZING_RESULT_HASH_REPLAY=PASS
ATTEMPT_4_CANDIDATE_COUNT=2
ATTEMPT_4_CANDIDATE_A_CUT=0.215
ATTEMPT_4_CANDIDATE_A_RATING_REQUEST_HASH=77ba78058f7e2f0d0befcc4fc1042fe179a79aadddc009666e4748ad00101334
ATTEMPT_4_CANDIDATE_A_RATING_BLOCKER=PRECISION_FLOOR_UNRESOLVED
ATTEMPT_4_CANDIDATE_A_FAILED_MESH_N=1
ATTEMPT_4_CANDIDATE_A_CELL_ROOT_Q_BRACKET_W=12234.634520032956..12234.634520032958
ATTEMPT_4_CANDIDATE_A_TASK172_EVALUATIONS=3279
ATTEMPT_4_CANDIDATE_A_TASK172_HOLES=0
ATTEMPT_4_CANDIDATE_B_CUT=0.220
ATTEMPT_4_CANDIDATE_B_RATING_REQUEST_HASH=8771099ae4fdfa553d2d092e41e366fcb36b1b30f16822c9f0277b9a6394066e
ATTEMPT_4_CANDIDATE_B_RATING_BLOCKER=PRECISION_FLOOR_UNRESOLVED
ATTEMPT_4_ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_4_PUBLIC_SIZING_RESULT=BLOCKED_NO_VALID_CANDIDATE_RATING
ATTEMPT_4_REFERENCE_RATING_REPLAY_RECOVERY=RUNNING_NOT_COMPLETED_SESSION_99672
```

The fixed non-cut geometry and service inputs are the Attempt 3 reference-bound
fixture (`FIXED_TUBESHEET`, E-shell `shell-1` / 0.500 m, tube OD 0.01905 m,
wall 0.00165 m, length 6.0 m, pitch 0.0254 m, one straight-through pass,
single-segmental baffles, spacing 1.2 m, count 4, thickness 0.006 m, four
BOTTOM orientations, clearances 0.003/0.001 m, tube/shell flows 12/20 kg/s,
pure water profile R2). Only `BAFFLE_CUT_FRACTION` varies in the frozen pool.
Qualification may inspect only producer validity/applicability/completeness,
identity, and C3 preflight fields; it must not use thermal or hydraulic
performance outputs to choose cuts.

At the start of Attempt 4, the prior reference Rating process was no longer
active and its former shell session could not be recovered; no complete final
request/result identity was captured. No concurrent or replacement replay has
been started. The single authorized recovery remains pending until the
implementation/qualification work is stable.

## ATTEMPT_4 — execution addendum

The 31-cut pre-Rating qualification completed with 16 qualified values. The
deterministic lowest-two rule selected `0.215` and `0.220`; the candidate
space was then frozen as R4 with no later changes. Complete per-cut outcomes
and hashes are in `attempt_4.qualification_ledger` in the machine evidence.

```text
ATTEMPT_4_QUALIFICATION_LEDGER_HASH=aeac45600d17c811b4e873e4d3bf3a3085a1741ad1888837641b993cfa19980c
ATTEMPT_4_QUALIFIED_CUT_COUNT=16
ATTEMPT_4_QUALIFIED_CUTS=0.215,0.220
ATTEMPT_4_VALIDATION_SPACE_ID=V07-T173-SIZING-IMPLEMENTATION-VALIDATION-CANDIDATE-SPACE-R4
ATTEMPT_4_VALIDATION_SPACE_HASH=dd78fe36ceaa2b7e49d7c7264e07c3ba02a286114876b982f7a1b74cf91b9c01
ATTEMPT_4_SIZING_REQUEST_HASH=0d1964be99e5445605c602b20f4befeef0e16442128b21f55e615d14fc6b6f2b
ATTEMPT_4_CANDIDATE_SPACE_FROZEN=true
ATTEMPT_4_CANDIDATE_SPACE_CHANGED_AFTER_EXECUTION=false
PERFORMANCE_OUTPUT_USED_FOR_FIXTURE_SELECTION=false
REQUIREMENT_NUMERIC_VALUES_CHANGED=false
```

The public Sizing API was invoked twice with the exact same frozen request.
Invocation 1 exposed an implementation wiring defect: the v0.7 Sizing chain
entered the legacy TASK034 baffle-cut path and returned
`SSPD_UNSUPPORTED_BAFFLE_CUT`. Within this R1 task, Sizing was corrected to
bypass only legacy TASK033/034/035/037/038 dependencies while retaining native
TASK031/TASK032/TASK166; default TASK168 behavior remains unchanged. Focused
candidate TASK174 tests with R2 identities passed. Invocation 2 used the
unchanged candidate space and completed Sizing request/result identity replay.
Both candidates were retained with typed Rating blockers. The two invocations
are reported openly because the first was needed to identify and fix the
in-scope implementation wiring defect.

Candidate A (`0.215`) reached candidate-native TASK171 and validated TASK174.
Its exact candidate Rating request was replayed once to capture diagnostics
not included in the Sizing ledger. It stopped at the first mesh level in the
reviewed cell-root precision guard:

```text
CANDIDATE_A_RATING_REQUEST_HASH=77ba78058f7e2f0d0befcc4fc1042fe179a79aadddc009666e4748ad00101334
FAILURE_CODE=PRECISION_FLOOR_UNRESOLVED
FAILED_MESH_N=1
DETAIL=CELL_ROOT_PRECISION_FLOOR_REACHED
LEFT_Q_W=12234.634520032956
RIGHT_Q_W=12234.634520032958
TASK172_LOCAL_EVALUATION_COUNT=3279
TASK172_NUMERICAL_HOLE_COUNT=0
```

This is distinct from the Attempt 2 C3 failure, Attempt 3 TASK024
intersection, and the initial TASK174 wiring defect. It is a fail-closed
TASK173 cell-root precision blocker under
`V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R3`; no valid candidate Rating
result was created. Candidate B (`0.220`) also returned
`PRECISION_FLOOR_UNRESOLVED` in the corrected public result. The frozen R4
space and all convergence/correlation controls remain unchanged; no further
cut was tried and no performance output was used to retune the fixture.

```text
ATTEMPT_4_PUBLIC_SIZING_INVOCATION_COUNT=2
ATTEMPT_4_PUBLIC_SIZING_RESULT_HASH=cffd3bb5d28500b78f1752a111cbccec5241deda893fe1c8d1257f2529d7c4ce
ATTEMPT_4_PUBLIC_SIZING_RESULT_ID=urn:hxforge:task173-sizing:cffd3bb5d28500b78f1752a111cbccec5241deda893fe1c8d1257f2529d7c4ce
SIZING_REQUEST_HASH_REPLAY=PASS
SIZING_RESULT_HASH_REPLAY=PASS
SIZING_RESULT_ID_BINDS_HASH=true
TOTAL_CANDIDATES=2
PASS_COUNT=0
WARN_COUNT=0
BLOCKED_COUNT=2
RECOMMENDABLE_COUNT=0
SELECTION_STATUS=NO_RECOMMENDABLE_CANDIDATE
ACTUAL_FULL_V07_CANDIDATE_RATING_COUNT=0
ATTEMPT_4_RESULT=BLOCKED_TASK173_FULL_SIZING_IMPLEMENTATION
```

The earlier reference Rating session 44691 was confirmed inactive before its
single authorized recovery started. That exact `validate_request()` replay
remains active in captured session 99672 and has not returned a final result;
its request-hash precheck is
`77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed`. No
second recovery was started. Reference result identity remains unverified
until the existing process returns a complete result.

Because the mandatory two-valid-Rating condition failed, post-PASS full-suite
validation, commit, push, and CI were not run. The implementation remains
uncommitted; no TASK175 work, Ready, or Merge action occurred.

## Post-Attempt-4 continuation: TASK174 canonical reduction parity

The parent implementation received a narrowly scoped TASK174 correction under
the original TASK173 R1 task. The root cause was
`DECIMAL_FINITE_PRECISION_REDUCTION_GROUPING_MISMATCH`: TASK174 had flattened
the four Bell region terms, while native TASK166 first forms the end-zone sum
and then adds that grouped value to crossflow and window contributions.

The correction now verifies both exact predicates under the existing
`engineering_context()`: inlet plus outlet equals TASK166 end-zone, then
central plus window plus native end-zone equals TASK166 total. No tolerance,
rounding, formula, physical event mapping, TASK166 code, or Decimal context was
changed. The exact rebound H1 validates with 19 events allocated once; its
legacy flat reduction remains `1E-47 Pa` different, while both native-grouped
replays differ by zero. The stored reference TASK174 result identity remains
`ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`.

Focused TASK174 tests pass, including the exact H1 arithmetic reproduction,
tampered end-zone and total blockers, hostile ambient Decimal context, and the
reference identity regression. This correction remains uncommitted as part of
the parent Sizing implementation; no standalone production commit was made.

## Provider-quantization enclosure qualification continuation

After the TASK174 parity fix, the original frozen TRAIN_A/B and rebound H1/H2/H3
identities completed actual candidate-native pre-Rating qualification and n=1
diagnostic trajectories. The external diagnostic wrapper exercised the
proposed provider-quantization representative and uncertainty-floor semantics
without changing production cell-root code. Eight outer-boundary trial events
passed the exact Q1–Q15 audit; no final accepted n=1 mesh cell required an
enclosure. The H2 trajectory recorded one recovered Task172 numerical hole;
no hole was promoted.

A new, unaccepted authority candidate was constructed with hash
`c95b5bf23b15a9c93b6ef47c3ad2043708bef9ae66429116855a4306f8102ab2` under
`PROPOSED_AUTHORITY_REVIEW_PENDING`. This evidence does not complete TASK173
Sizing: no full candidate Rating, public Sizing request, full reference Rating
replay, or production mesh sequence was executed. The next gate is the single
independent review of the enclosure authority candidate. Full continuation
details are recorded in
`TASK-173-v0.7-task174-native-bell-canonical-reduction-parity-and-enclosure-qualification-resume-r1.md`
and its matching machine evidence.
