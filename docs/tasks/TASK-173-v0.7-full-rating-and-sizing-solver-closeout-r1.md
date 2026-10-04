# TASK173 v0.7 full Rating and Sizing solver closeout R1

```ini
TASK_ID=STAGE3_TASK173_FULL_RATING_AND_SIZING_SOLVER_CLOSEOUT_R1
MODE=TASK173_FULL_CAPABILITY_CLOSEOUT_IMPLEMENT_IF_AUTHORIZED_ELSE_FAIL_CLOSED
RESULT=BLOCKED_TASK173_FULL_SIZING_AUTHORITY_INCOMPLETE
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
AUTHORIZED_SOURCE_HEAD=355df02f55107cdae4902ec825eae7648b2f76d8
PREDECESSOR_EVIDENCE_CANONICAL_HASH=9bdca85bcad6f897bb9de1f144082d34e2c2fe7c7883a4d9b8b9645983d12308
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_FOR_TASK173_SIZING_AUTHORITY_CLOSURE
STOP=true
EVIDENCE_CANONICAL_HASH=ca6b37c400b1e15dbe0cbf5e15e45ce38303178952c35955caabc91070ed43f4
```

## Decision

The accepted v0.7 reference-case Rating is complete and remains frozen. It is
not a multi-candidate Sizing result. This closeout does not implement Sizing:
the reviewed authority needed to bind candidate-specific TASK171/TASK172/
TASK174 work, a generalized TASK173 candidate Rating request, actual v0.7
Sizing requirements, and a v0.7 ranking policy is absent. The missing items
are authority boundaries, not permission to generalize from the current
reference case or to silently reuse a v0.6 policy identity.

The frozen Rating receipt records `Task173SuccessResult`, `VALIDATED`, request
hash `77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed`,
result hash `fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b`,
and the matching result ID. Its accepted mesh is n=32 with n=64 headroom and
exact deterministic replay. The Rating source files are unchanged from the
accepted production execution. No thermal solve or production mesh was rerun
for this authority audit.

## Same-task implementation and authority audit

“Authority available” below means authority sufficient for the stated v0.7
capability, not merely that a related implementation or narrower reviewed
authority exists. v0.6 reuse is marked explicitly where the user authorized
reuse of semantics only.

| Item | Implemented | Reviewed authority available for v0.7 scope | Case-bound only | Source and authority / reason |
| --- | --- | --- | --- | --- |
| A. Public Rating request/result | true | true, reference Rating only | true | `src/hexagent/exchangers/shell_tube/task173_integrated_rating/models.py`; accepted production receipt `docs/tasks/TASK-172-v0.7-stage3-production-mesh-reexecution-after-replay-correction-r4.md`; current public mode is `RATING_FIXED_GEOMETRY`, with the frozen reference request/result identities above. |
| B. Public Sizing request/result | false | false | true | Same `models.py` and `__init__.py`: only fixed-geometry Rating request/result are exported; success explicitly records `sizing_execution_status=NOT_APPLICABLE_CURRENT_REFERENCE_CASE`. No public Sizing request/result exists. |
| C. Manufacturable candidate enumeration | true | true, reusable semantics only | false | `docs/tasks/TASK-168-manufacturable-candidate-generation-and-sizing.md`; `TASK168_AUTHORITY_ISSUE_263`, `task168.v1`. This is v0.6 candidate-space authority and is reusable here only for the semantics explicitly allowed by this task; it does not authorize v0.7 thermal evaluation or final Rating. |
| D. Candidate-specific TASK020/021/022/024 materialization | true | true, reusable producer/materialization semantics only | false | TASK168 §§ request boundary and exact evaluation state machine, same document above. Candidate-selected geometry is materialized through native producers in its authorized v0.6 chain. This does not bind candidate-specific v0.7 thermal/hydraulic results. |
| E. Candidate-specific TASK171 topology materialization | true for the accepted reference geometry | false for candidate-generalized materialization | true | `src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/native.py`; R4 authority and R5 review: `docs/tasks/TASK-170-v0.7-task171-entry-authority-r4.md`, `docs/tasks/TASK-170-v0.7-final-review-receipt-r5.md`; R119-D/E receipts. R4 reviews a narrow topology/interface; R119-D/E explicitly review one case-bound native geometry identity, not a generated candidate-space mapping. |
| F. Candidate-specific TASK172 local thermal closure | true for the accepted reference case | false | true | `src/hexagent/exchangers/shell_tube/task172_local_runtime/models.py`; `Task172LocalRequest` fixes reference case/revision, profile and hashes, 12/20 kg/s, clean surfaces and the accepted geometry identity. Reviewed dogbox overlay `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, hash `9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b`, changes only fail-only numerical path; it does not generalize the admitted thermal/property domain. |
| G. Candidate-specific TASK174 hydraulic closure | false (orchestrator exists; closure remains blocked) | false | true | `src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration/models.py`; Stage-2 result `STAGE2_PARTIAL_TASK172_COMPLETE_TASK174_BLOCKED`, evidence canonical hash `9d8c3b068c9704684eea13b072062dff0256911c1f80885145d9b7fc449bf771`. Request pins case/revision, topology/result, mesh, ownership and TASK020 hashes; receipt identifies three unresolved hydraulic authority scopes. |
| H. Full TASK173 Rating | true for the accepted reference case | true, reference Rating only | true | `src/hexagent/exchangers/shell_tube/task173_integrated_rating/models.py` and `service.py`; production receipt above. It runs the full approved reference-case mesh and replay, not every Sizing candidate. |
| I. Hard duty constraint | true in TASK168 v0.6 | false for v0.7 Sizing | false | TASK168 `Task168RequirementAuthority` and constraint stage; no reviewed v0.7 candidate requirement binds a required duty and exact acceptance predicate. The Rating reference case computes duty and does not supply a candidate-selection duty requirement. |
| J. Maximum tube DP constraint | true in TASK168 v0.6; full v0.7 chain unavailable | false | false | TASK168 v0.6 constraint machinery exists, but TASK174 v0.7 candidate hydraulic closure is incomplete and no v0.7 Sizing request binds a source-authorized maximum. |
| K. Maximum shell DP constraint | true in TASK168 v0.6; full v0.7 chain unavailable | false | false | Same as J; Task174 Stage-2 blocker includes incomplete Bell physical-event allocation/aggregation and pressure coupling. No zero-fill or inferred DP is authorized. |
| L. Required screening constraints | partial producer implementation; no complete v0.7 required set | false | false | TASK167 screening is consumed by TASK168 v0.6; TASK174 FIV is explicitly `DIAGNOSTIC_SCREENING_ONLY`. TASK170 scope-source freeze §15 says mandatory missing screens block recommendation, but does not provide this candidate request's specific required-screen authority. |
| M. PASS/WARN/BLOCKED retention | true in TASK168 v0.6 | true, reusable status semantics only | false | TASK168 status semantics and retained candidate records; reusable semantics are expressly permitted, but do not imply v0.7 candidate evaluation completion. |
| N. Deterministic ranking | true in TASK169 v0.6 | false for v0.7 policy identity | false | `docs/tasks/TASK-169-selection-integration-golden-release-acceptance.md` § Ranking authority. Existing identity is `HXFORGE-V06-TASK169-RANKING-POLICY`, canonical hash `142d58764a886a658bc24d1734b2be900843baa62c28dba849926b10a1f2fdc8`. TASK170 requires versioned policy identity; no reviewed v0.7 transfer is present. |
| O. Recommendation and alternatives | true in TASK169 v0.6 | false for v0.7 policy identity | false | TASK169 selection result has recommendation, alternatives, exclusions and reason traces under its v0.6 policy. No reviewed v0.7 authority permits applying that exact policy identity to full v0.7 Rating outputs. |
| P. Canonical identity and replay | true for individual TASK168/169 and reference TASK173 products; false for full v0.7 Sizing | false for full v0.7 Sizing | mixed | TASK168/TASK169 implement subsystem identities; TASK173 replays the fixed Rating request/result. No Sizing request, candidate-space-to-Rating result, ranking-policy binding and Sizing result identity/replay contract is materialized under a reviewed v0.7 authority. |
| Q. Complete v0.7 Sizing provenance | false | false | true for current integrated Rating chain | Existing component provenance is present, but no acyclic candidate→native geometry→TASK171→candidate TASK172/TASK174→TASK173 Rating→constraints→v0.7 policy→selection/result chain exists. TASK170 release gate 15 defines the required provenance boundary; the present reference-case chain is not a candidate Sizing chain. |

## Complete authority-gap ledger

| Blocker | Missing authority | Current case-bound source | Why it cannot transfer | Affected component | Minimum authority needed | Existing reusable components |
| --- | --- | --- | --- | --- | --- | --- |
| `GAP_CANDIDATE_BOUND_TASK171` | Reviewed candidate-specific TASK171 topology/ownership binding for each admitted generated geometry, including the native geometry-to-physical interval/event and state mapping | R4 reviewed entry profile; R119-D/E accepted one effective Variant-A reference Definition and exact native TASK020/021/022/024/025 identities. R119-D evidence hash `7a76c7cc118c88a5ef7d1e40add66915e6b93190bfae15a31aee4687ab01e1af`. | R4 approves a constrained topology/interface and explicitly does not itself materialize an executable API or full GAP-SEG closure. R119-D/E explicitly label the accepted result case-bound; its exact geometry/event evidence cannot stand in for other candidate dimensions or physical ownership. | TASK171 candidate topology and TASK173 candidate binding | Owner/reviewer-approved candidate geometry binding and native TASK171 materialization semantics for the supported topology domain, with candidate-specific exact IDs/hashes and fail-closed exclusions. | R4 topology interface IDs `V07-T171-TOPOLOGY-R4-V1`, `V07-T171-CELL-COMPARTMENT-R4-V1`, `V07-T171-CONSERVATION-R4-V1`; TASK168 candidate-native producer materialization may be reused for its stated semantics. |
| `GAP_CANDIDATE_BOUND_TASK172` | Candidate-bound v0.7 fluid/property, wall/material, local-state and numerical admission for changed geometries/operating requirements | `Task172LocalRequest` in `src/hexagent/exchangers/shell_tube/task172_local_runtime/models.py`; Stage-1 case bundle; R3 dogbox authority hash `9a226f98...`. | Request/schema and validators pin reference case/revision, property profile, accepted R94/R98 hashes, geometry, mass flows, fouling and temperature/pressure domain. R3 only amends solver path after a specific replay-valid residual blocker; it does not authorize changed candidate geometry or requirements. | Candidate-local thermal closure and all candidate Rating outputs | Reviewed candidate-bound thermal/property/material/domain authority identifying admissible geometry and operating inputs, then numerical profile application without broadening R98 or the reviewed solver controls. | Existing reference-case TASK172 runtime and R3 fail-only overlay, only inside current bound scope. |
| `GAP_CANDIDATE_BOUND_TASK174` | Complete candidate-specific tube/shell hydraulic closure and operability authority | `src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration/models.py`; Stage-2 closeout / blocker evidence hash `5a201e438e9f380a726f6a8fe9c9bf01474b0a1785497ebd950679e9b722b5af`. | Request literals bind the reference case/revision, topology/result, structural mesh, ownership and TASK020 configuration. The reviewed Stage-2 result says closure=false and identifies missing component/exclusion coverage, physical-event-to-Bell-region allocation/aggregation, and pressure-state coupling. | Candidate DP, required hydraulic screening, hard tube/shell DP limits | Reviewed authority and executable candidate-bound producer chain for all applicable tube components and physical absences, shell event allocation/aggregation, pressure/property state coupling, and required operability outputs. | Existing typed Task174 orchestration boundary and its fail-closed component checks; no missing DP is to be zero-filled. |
| `GAP_TASK173_CANDIDATE_GENERALIZED_RATING` | Reviewed authority for a candidate-bound full v0.7 Rating request/result mode | `src/hexagent/exchangers/shell_tube/task173_integrated_rating/models.py`; TASK170 R5 says `TASK173_ENTRY_AUTHORITY_COMPLETE=false`; current success result labels sizing not applicable. | Current request `case_revision_id` is a `Literal` for the reference case and `case_mode` is only `RATING_FIXED_GEOMETRY`; the request consumes the case-bound Task174 result. The successful reference solve is not a review of arbitrary candidate inputs. | Per-candidate full mesh Rating, request/result identity and replay | Explicitly reviewed v0.7 Sizing/Rating candidate mode and bindings to each newly materialized upstream identity, preserving existing reference Rating identity. | Existing public `validate_request` and its frozen exact reference result; do not weaken it into a loose union. |
| `GAP_V07_SIZING_REQUIREMENT_AUTHORITY` | Source-bound v0.7 Sizing requirement identity and numeric constraints | TASK170 scope-source freeze §§16,18,21–22; current reference Rating request/evidence. | TASK170 defines responsibility/gates and says G05 needs approved project inputs/limits and independent expected classifications; it does not supply this Sizing request's required duty, DP maxima, thermal and screening requirements, allowed dimension sets or requirement hash. The reference Rating has no candidate selection requirement. | Sizing request admission, hard duty/DP/screen predicates, recommendability | Reviewed v0.7 requirement authority binding case/revision, streams/states/flows, required duty, maximum tube and shell DP, mandatory screening, allowed candidate families/dimension authorities, resource limits and exact predicates. | TASK168 v0.6 requirement-authority semantics may inform structure only; no bare numbers or anonymous defaults. |
| `GAP_V07_SIZING_RANKING_POLICY` | Reviewed v0.7 objective/weights/scales/WARN penalty/tie-break/Top-N policy identity | TASK169 § Ranking authority; TASK170 scope-source freeze §§18,21 and task170 R5 review. | TASK169's production identity is specifically `HXFORGE-V06-TASK169-RANKING-POLICY`; TASK170 says policy identity is required and G05 requires exact ranking/reason trace, but provides no v0.7 policy values or explicit authority transfer. Reusing v0.6 would silently carry a different versioned policy into v0.7. | Deterministic ranking, recommendation, alternatives, final result identity | Owner-approved and independently reviewed v0.7 policy identity/hash freezing objective metrics/directions/weights/scales, Decimal arithmetic, WARN penalty, tie-break, Top-N and reason trace. | TASK169 implementation mechanics and trace schema are reusable only after an explicit reviewed v0.7 policy binding; its v0.6 policy ID/hash is not transferable by inference. |

These gaps are independently sufficient to prevent Branch A. The ledger is
the complete current closeout disposition; it does not create separate child
tasks or propose a technical implementation sequence. No authority was
generalized from the reference case, no score/weight/limit was invented, and
TASK168's v0.6 thermal closure is not treated as a final v0.7 Rating.

## Frozen state and boundary

```ini
REFERENCE_RATING_REQUEST_HASH=77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed
REFERENCE_RATING_RESULT_HASH=fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
REFERENCE_RATING_RESULT_ID=urn:hxforge:task173:fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
REFERENCE_RATING_IDENTITY_PRESERVED=true
TASK173_SIZING_PUBLIC_MODE_PRESENT=false
TASK168_ENUMERATION_REUSED=false
TASK168_V06_THERMAL_RESULT_USED_AS_V07_FINAL_RATING=false
CANDIDATE_BOUND_TASK171_AUTHORITY_AVAILABLE=false
CANDIDATE_BOUND_TASK172_AUTHORITY_AVAILABLE=false
CANDIDATE_BOUND_TASK174_AUTHORITY_AVAILABLE=false
CANDIDATE_GENERALIZED_TASK173_RATING_AUTHORITY_AVAILABLE=false
V07_SIZING_REQUIREMENT_AUTHORITY_AVAILABLE=false
V07_SIZING_RANKING_POLICY_AUTHORITY_AVAILABLE=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILE_CHANGED=false
WORKFLOWS_CHANGED=false
PRODUCTION_MESH_REEXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
```

`TASK168_ENUMERATION_REUSED=false` means no enumeration was executed or
materialized in this blocked closeout; its reviewed reusable semantics remain
available as described above. Existing TASK168 results are not promoted as
v0.7 candidate Ratings.

PR #283 remains OPEN / Draft. The next state is owner direction on the listed
authority gaps; no technical child gate, Sizing implementation, production
mesh, TASK175 acceptance, Ready action or Merge action is performed here.

## Validation

Focused TASK171/TASK172/TASK173/TASK174/TASK168/TASK169 checks passed (221
passed, 2 skipped). The full shell-tube suite and HTTP/API suite passed in a
combined run (2,293 passed, 4 skipped); the standalone HTTP/API run passed all
21 tests. Ruff, formatting (777 files), CI-scope mypy (450 source files),
manifest D==M (259/259), pip-audit, `uv lock --check`, locked all-extras sync
(71 packages), `git diff --check`, and changed-evidence duplicate-key audit
passed. `urllib3==2.8.0` and `requests==2.34.2` remain locked; `uv.lock` and
`pyproject.toml` are unchanged. Pip-audit reports no known vulnerabilities;
the unpublished local package is not available on PyPI and is skipped.
