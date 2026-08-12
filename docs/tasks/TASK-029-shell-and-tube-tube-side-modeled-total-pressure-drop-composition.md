# TASK-029 Design Contract —
# Shell-and-Tube Tube-Side Modeled Total Pressure-Drop Composition,
# Reference-Plane Compatibility and Completeness Ledger
> Binding implementation design for TASK-029.
> Translates frozen Issue #173 Source Definition R4 into an implementation-ready architecture.
> Does not modify frozen engineering semantics.
## 1. Design authorization

```text
TASK_ID=TASK-029

TASK029_DESIGN_CONTRACT_FREEZE_AUTHORIZATION=
AUTHORIZE_TASK029_DESIGN_CONTRACT_FREEZE_AND_COMMIT_ONLY

SOURCE_DEFINITION_AUTHORITY=ISSUE_173
VERSION_ALLOCATION_AUTHORITY=ISSUE_167

DESIGN_BASE=
main@6dd4bfa81a330fb36eec4cb262664184657279d4

SOURCE_DEFINITION_ISSUE=173
SOURCE_DEFINITION_REVISION=R4
SOURCE_DEFINITION_FROZEN=YES
SOURCE_DEFINITION_R4_REREVIEW_RESULT=PASS

TASK029_DESIGN_CONTRACT_R4_REVIEW_RESULT=PASS

DESIGN_CONTRACT_R4_ALIGNED=true
DESIGN_CONTRACT_STATUS=FROZEN
DESIGN_CONTRACT_FROZEN=true
DESIGN_CONTRACT_FREEZE_COMPLETE=true

DESIGN_ACCEPTANCE_PASS_COUNT=26/26
IMPLEMENTATION_READINESS=PASS

REVIEW_BLOCKER_COUNT=0
MAJOR_NONBLOCKING_COUNT=0
MINOR_NONBLOCKING_COUNT=1

F_T03_TABLE_DISPOSITION=ACCEPTED_MINOR_NONBLOCKING
F_T03_TABLE_REMEDIATION_REQUIRED_BEFORE_FREEZE=false

FROZEN_BLOCKER_REGISTRY_COUNT=43
FROZEN_BLOCKER_REACHABILITY_TEST_COUNT=43
FROZEN_UNREACHABLE_BLOCKER_COUNT=0

FROZEN_TEST_ID_COUNT=117
FROZEN_UNIQUE_TEST_ID_COUNT=117

FROZEN_ORACLE_VECTOR_COUNT=8
FROZEN_ORACLE_VECTOR_VALUES_CHANGED=false
FROZEN_ORACLE_REVIEW_PASS_COUNT=8

TASK029_DESIGN_AUTHORIZED=NO
IMPLEMENTATION_AUTHORIZED=NO
BRANCH_AUTHORIZED=NO
COMMIT_AUTHORIZED=NO
PUSH_AUTHORIZED=NO
PR_AUTHORIZED=NO
TASK030_AUTHORIZED=NO

NO_STEP_IMPLIES_THE_NEXT=TRUE
```
## 2. Frozen engineering contract restatement

Issue #173 frozen semantics — restated without modification:

```text
TASK-029=
Shell-and-Tube Tube-Side Modeled Total Pressure-Drop Composition,
Reference-Plane Compatibility and Completeness Ledger

TASK029_NEW_PHYSICS_FORMULAS=FORBIDDEN
TASK029_REFERENCE_PLANE_VALIDATION=REQUIRED
TASK029_COMPLETENESS_LEDGER=REQUIRED

TASK029_PUBLIC_TOTAL_FIELD=modeled_total_tube_side_pressure_drop_pa
TASK029_FORBIDDEN_UNCONDITIONAL_TOTAL_FIELD=total_tube_side_pressure_drop_pa

TASK029_DIRECT_UPSTREAM=TASK-027,TASK-028
TASK029_ADDITIONAL_TASK_DIRECT_UPSTREAM=NONE

TASK029_NEW_PHYSICS_FORMULAS=FORBIDDEN
TASK029_DIRECT_UPSTREAM=TASK-027,TASK-028
TASK029_PUBLIC_TOTAL_FIELD=modeled_total_tube_side_pressure_drop_pa
FORBIDDEN_FIELD=total_tube_side_pressure_drop_pa
TASK027_COMPOSED_PRESSURE_FIELD=straight_tube_friction_pressure_drop_pa
TASK028_COMPOSED_PRESSURE_FIELD=component_irreversible_pressure_loss_pa
TASK029_REAPPLY_TASK028_MULTIPLICITY=false
TASK029_PRESSURE_UNIT=Pa
TASK029_PRESSURE_QUANTUM_PA=0.001
TASK029_DECIMAL_PRECISION=28
TASK029_ROUNDING_MODE=ROUND_HALF_EVEN
REFERENCE_PLANE_COMPARISON=EXACT_UTF8_IDENTITY
TASK029_COMPLETENESS_SEMANTICS=COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY
PARTIAL_MODELED_TOTAL_ALLOWED=false
ACTIVE_TUBE_COUNT_PRESSURE_MULTIPLIER=false
```

TASK-029 composes one explicitly authorized serial path. It never recomputes TASK-027 friction physics or TASK-028 local/minor-loss physics.
## 3. Exact frozen schemas

Copied from Issue #173 without semantic change.

### 3.1 `TubeSidePressurePathMemberAuthority` — 13 fields

Namespace/schema: `task029.pressure-path-member-authority.v1`

```text
1  schema_version
2  member_id
3  global_path_sequence_index
4  producer_task
5  producer_member_kind
6  producer_component_identity
7  expected_producer_component_type
8  expected_producer_authority_hash
9  expected_upstream_reference_plane
10 expected_downstream_reference_plane
11 expected_multiplicity
12 geometry_evidence_refs
13 member_authority_hash
```

Hash covers fields 1–12.

Branch rules:

```text
producer_task in {TASK-027,TASK-028}
producer_member_kind in {DISTRIBUTED_FRICTION,LOCAL_MINOR_LOSS}
global_path_sequence_index=NONNEGATIVE_INTEGER
expected_multiplicity=INTEGER_GE_1
reference_planes=NONEMPTY_DISTINCT_EXACT_STRINGS
geometry_evidence_refs=NONEMPTY_UNIQUE_TUPLE_SORTED_UTF8

TASK027:
  producer_member_kind=DISTRIBUTED_FRICTION
  producer_component_identity=STRAIGHT_TUBE_FRICTION
  expected_producer_component_type=STRAIGHT_TUBE_FRICTION
  expected_producer_authority_hash=""   # exact frozen branch sentinel
  expected_multiplicity=1

TASK028:
  producer_member_kind=LOCAL_MINOR_LOSS
  producer_component_identity == component_result.component_id
  expected_producer_component_type == component_result.component_type.value
  expected_producer_authority_hash == component_result.authority_hash
  expected_multiplicity == component_result.multiplicity
```
### 3.2 `TubeSidePressurePathExclusionAuthority` — 6 fields

Namespace/schema: `task029.pressure-path-exclusion-authority.v1`

```text
1 schema_version
2 exclusion_id
3 excluded_item_identity
4 exclusion_reason
5 evidence_refs
6 exclusion_authority_hash
```

Hash covers fields 1–5.

```text
exclusion_reason in {PHYSICALLY_ABSENT,V0_2_OUT_OF_SCOPE}
evidence_refs=NONEMPTY_UNIQUE_TUPLE_SORTED_UTF8
HIDDEN_EXCLUSION_INFERENCE=false
```

Completeness coverage:

```text
V0_2_OUT_OF_SCOPE_REQUIRED_EXCLUSIONS=(
  PASS_PARTITION,
  RETURN_HEADER,
  RETURN_BEND,
  U_BEND,
)

TASK028_IN_SCOPE_COMPONENT_TYPES=(
  ENTRANCE,
  EXIT,
  CHANNEL_HEAD,
  NOZZLE,
  CONTRACTION,
  EXPANSION,
)
```
### 3.3 `TubeSidePressurePathCompositionAuthority` — 9 fields

Namespace/schema: `task029.pressure-path-composition-authority.v1`

```text
1 schema_version
2 modeled_path_id
3 flow_direction_assertion
4 start_reference_plane
5 end_reference_plane
6 member_authorities
7 exclusion_authorities
8 geometry_evidence_refs
9 composition_authority_hash
```

Hash covers fields 1–8.

```text
flow_direction_assertion=START_TO_END
member_authorities=NONEMPTY
MEMBER_CANONICAL_ORDER=global_path_sequence_index ASC
GLOBAL_INDEX_DOMAIN=EXACT_CONTIGUOUS_ZERO_BASED_0_TO_N_MINUS_1
CALLER_MEMBER_ORDER_PERMUTATION_INVARIANT=true
EXCLUSION_CANONICAL_ORDER=exclusion_id UTF8 ASC
GEOMETRY_EVIDENCE_REF_CANONICAL_ORDER=UTF8 ASC
EXACTLY_ONE_TASK027_MEMBER=true
TASK028_COMPONENT_ONE_TO_ONE_BINDING=true
TASK028_PATH_SEQUENCE_INDEX_IS_TASK029_GLOBAL_ORDER=false
```
Canonical tuple child shapes (frozen oracle bytes; design clarification DC-002):

```text
member_authorities tuple children =
  FULL 13-field TubeSidePressurePathMemberAuthority RECORDS
  including member_authority_hash

exclusion_authorities tuple children =
  FULL 6-field TubeSidePressurePathExclusionAuthority RECORDS
  including exclusion_authority_hash
```

F_T029_DC_002_RESOLVED=true

### 3.4 `Task029Request` — 6 fields

Schema `task029.request.v1`.

```text
schema_version
profile_id
task027_success_result
task028_success_result
composition_authority
request_hash
```

Request-hash semantic projection — 9 fields:

```text
schema_version
profile_id
task027_result_hash
task028_result_hash
task025_hydraulic_authority_hash
task025_result_hash
task026_result_hash
property_snapshot_hash
composition_authority_hash
```
### 3.5 `TubeSidePressurePathLedgerMemberEvidence` — 16 fields

Namespace `task029.ledger-member-evidence.v1`.

```text
schema_version
member_id
global_path_sequence_index
producer_task
producer_result_hash
producer_member_kind
producer_component_identity
producer_component_type
producer_authority_hash
upstream_reference_plane
downstream_reference_plane
expected_multiplicity
observed_multiplicity
pressure_contribution_pa
composition_member_authority_hash
member_status
```

Success `member_status=VERIFIED`.

TASK-027 `producer_authority_hash=""` is the same explicit branch sentinel as the member authority.
### 3.6 `TubeSidePressurePathLedgerExclusionEvidence` — 7 fields

Namespace `task029.ledger-exclusion-evidence.v1`.

```text
schema_version
exclusion_id
excluded_item_identity
exclusion_reason
evidence_refs
exclusion_authority_hash
exclusion_status
```

Success `exclusion_status=VERIFIED_EXCLUSION`.
### 3.7 `TubeSidePressurePathCompletenessLedger` — 12 fields

Namespace `task029.completeness-ledger.v1`.

```text
schema_version
modeled_path_id
modeled_start_reference_plane
modeled_end_reference_plane
expected_member_count
observed_member_count
ordered_member_evidence
ordered_exclusion_evidence
path_continuity_status
identity_compatibility_status
completeness_status
ledger_hash
```

Hash covers fields 1–11.

Success statuses:

```text
path_continuity_status=CONTIGUOUS_EXACT_REFERENCE_PLANE_CHAIN
identity_compatibility_status=MATCHED
completeness_status=COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY
```
### 3.8 `Task029SuccessResult` — 18 fields

Namespace `task029.success-result.v1`.

```text
schema_version
profile_id
request_hash
result_hash
result_id
task027_result_hash
task028_result_hash
task025_hydraulic_authority_hash
task025_result_hash
task026_result_hash
property_snapshot_hash
composition_authority_hash
completeness_ledger
modeled_total_tube_side_pressure_drop_pa
warnings
blockers
deferred_capabilities
provenance
```

Hash excludes only `result_hash`,`result_id` and hashes the other 16 semantic fields in relative order.

```text
warnings=()
blockers=()
modeled_total_tube_side_pressure_drop_pa>0
```
### 3.9 `Task029BlockedResult` — 18 fields

Namespace `task029.blocked-result.v1`.

```text
schema_version
profile_id
request_hash
result_hash
result_id
task027_result_hash
task028_result_hash
task025_hydraulic_authority_hash
task025_result_hash
task026_result_hash
property_snapshot_hash
composition_authority_hash
raw_request_projection
raw_upstream_blocked_projection
warnings
blockers
deferred_capabilities
provenance
```

Missing unavailable identity strings use exact empty `STRING` payloads. `raw_upstream_blocked_projection` and `provenance` may be `NONE`.

Blocked result forbids completeness ledger, modeled total, and partial engineering.
### 3.10 `Task029RawBoundaryBlockedResult` — 6 fields

Namespace/schema `task029.raw-boundary-blocked-result.v1`.

```text
schema_version
implementation_software_version
raw_request_projection
blockers
warnings
deferred_capabilities
```
### 3.11 `FrozenTask029RawProjection` — 2 fields

Namespace `task029.raw-projection.v1`.

```text
projection_kind
canonical_bytes_hex
```

`canonical_bytes_hex` is the lowercase hex of the raw canonical bytes, never a digest.

Projection kinds: `task029.raw-request`, `task029.upstream-blocked-set`.
### 3.12 `Task029BlockerEntry` — 4 fields

Namespace `task029.blocker-entry.v1`.

```text
code
field_path
message_key
evidence_refs
```

`message_key == code`.

Deduplication key: `(code,field_path,evidence_refs)`.

Ordering: `(registry_index ASC, field_path UTF8 ASC, evidence_refs tuple lexical ASC)`.

Canonical `Task029BlockerEntry` field encoding (design clarification DC-004):

```text
BLOCKER_ENTRY_KIND_TAGS=(ENUM,STRING,STRING,TUPLE)

code          => ENUM
field_path    => STRING   # individual path, not TUPLE
message_key   => STRING
evidence_refs => TUPLE
```

Example:

```text
code=BL_T029_UPSTREAM_IDENTITY_MISMATCH
field_path=task028_success_result.property_snapshot_hash   # STRING kind
message_key=BL_T029_UPSTREAM_IDENTITY_MISMATCH
evidence_refs=(aaaaaaaa..., bbbbbbbb...)
```

F_T029_DC_004_RESOLVED=true

### 3.13 `Task029Provenance` — 5 fields

Namespace `task029.provenance.v1`.

```text
task_id
design_contract_path
implementation_software_version
input_evidence_refs
upstream_identity_hashes
```

Success upstream hash order:

```text
(
 task027_result_hash,
 task028_result_hash,
 task025_hydraulic_authority_hash,
 task025_result_hash,
 task026_result_hash,
 property_snapshot_hash,
 composition_authority_hash,
)
```
### 3.14 Warnings and deferred capabilities

```text
TASK029_WARNINGS_ALL_PATHS=()

TASK029_DEFERRED_CAPABILITIES_V1=(
 STATIC_HEAD_NOT_MODELED,
 ACCELERATION_PRESSURE_DROP_NOT_MODELED,
 COMPRESSIBLE_PATH_INTEGRATION_NOT_MODELED,
 SHELL_SIDE_PRESSURE_DROP_NOT_MODELED,
 EXCLUDED_TASK028_COMPONENT_TYPES_NOT_MODELED,
 FULL_PHYSICAL_PRESSURE_DROP_COMPLETENESS_NOT_CLAIMED,
)
```
## 4. Implementation architecture

Package: `src/hexagent/exchangers/shell_tube/tube_side_pressure_drop_composition/`

Architecture follows TASK-028 (`tube_side_local_loss/`) separation pattern: enums, models, canonical framing, identity, raw boundary/projection, validation stages, computation, result builders, and a single pipeline entry point.

```text
DESIGN_IMPLEMENTATION_FILE_COUNT=17
```

| # | Path | Ownership |
|---|------|-----------|
| 1 | `__init__.py` | Package export surface only; no business logic |
| 2 | `enums.py` | `ProducerTask`, `ProducerMemberKind`, `ExclusionReason`, `MemberStatus`, `ExclusionStatus`, path-continuity enums, `Task029BlockerCode` ordinals |
| 3 | `models.py` | Frozen dataclasses for all §3 schemas; field-order tuples; field counts |
| 4 | `canonical.py` | Namespaces, kind-tag constants, `IMPLEMENTATION_SOFTWARE_VERSION`, deferred tuple, evidence-ref sort, framing primitives |
| 5 | `decimal_identity.py` | `TASK029_DECIMAL_PRECISION=28`, `ROUND_HALF_EVEN`, `PRESSURE_QUANTUM_PA=0.001`, `task029_decimal_context()`, `normalize_negative_zero()` |
| 6 | `identity.py` | All canonicalize/compute_hash/derive_result_id functions (§12) |
| 7 | `raw_projection.py` | `FrozenTask029RawProjection`, `canonicalize_raw_value()`, `encode_raw_projection()` |
| 8 | `raw_boundary.py` | `validate_raw_boundary()`, raw S00 stages, transition to typed request |
| 9 | `upstream_replay.py` | `replay_task027_success()`, `replay_task028_success()` — production replay only |
| 10 | `blocker_registry.py` | 43-code registry, `emit_blocker()`, `collapse_blockers()`, message map |
| 11 | `path_binding.py` | Member sort, index domain, producer binding, path topology predicates (§8) |
| 12 | `completeness.py` | Exclusion partition validation, ledger exclusion evidence (§9) |
| 13 | `composition.py` | Pressure contribution extraction, quantum validation, ordered Decimal sum (§10–11) |
| 14 | `validation.py` | Typed validation scheduler T00–T12 orchestration (§7) |
| 15 | `request.py` | `Task029Request`, `build_task029_request()` |
| 16 | `result.py` | Success/blocked/raw-boundary builders, member/exclusion evidence builders |
| 17 | `pipeline.py` | `compute_task029_composition()` — sole public orchestration entry |

No additional files without a separately authorized design revision.
## 5. Upstream replay adapter design

Replay uses **production functions only**. TASK-029 must not clone or replace producer hash algorithms.

### 5.1 TASK-027 adapter (`upstream_replay.py`)

Production authority: `src/hexagent/exchangers/shell_tube/tube_side/friction_pressure_drop.py`

```text
TASK027_ACCEPTED_RESULT_TYPE=Task027SuccessResult
TASK027_ACCEPTED_SCHEMA_VERSION=task027-r1.schema.v1
TASK027_SUCCESS_FIELD_COUNT=18
```

`replay_task027_success(result: object) -> Task027ReplayEvidence | Task029BlockerEntry`:

1. Require exact `Task027SuccessResult` type (not subclass, not `Any`, not Protocol, not mapping).
2. Require `schema_version == task027-r1.schema.v1`.
3. Replay `compute_result_hash(schema_version, profile_id, request_hash, darcy_friction_factor, friction_length_m, upstream_reference_plane, downstream_reference_plane, straight_tube_friction_pressure_drop_pa, task025_hydraulic_authority_hash, task025_result_hash, task026_result_hash, property_snapshot_hash)`.
4. Replay `derive_result_id(result_hash)`.
5. Return trusted evidence: `result_hash`, `result_id`, `straight_tube_friction_pressure_drop_pa`, common identity fields.

On type failure: emit `BL_T029_UPSTREAM_TASK027_TYPE_INVALID` (T00 terminal). On hash/id failure: emit `BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID` (T02). Warnings/blockers emptiness is validated at T03, not in this adapter.

### 5.2 TASK-028 adapter (`upstream_replay.py`)

Production authority: `src/hexagent/exchangers/shell_tube/tube_side_local_loss/identity.py`

```text
TASK028_ACCEPTED_RESULT_TYPE=Task028SuccessResult
TASK028_ACCEPTED_SCHEMA_VERSION=task028.success-result.v1
TASK028_SUCCESS_FIELD_COUNT=14
TASK028_COMPONENT_RESULT_FIELD_COUNT=14
```

`replay_task028_success(result: object) -> Task028ReplayEvidence | Task029BlockerEntry`:

1. Require exact `Task028SuccessResult` type.
2. Require `schema_version == task028.success-result.v1`.
3. Require `component_results` non-empty tuple.
4. Canonicalize each production component result using TASK-028 production canonical contract.
5. Replay `compute_success_result_hash(schema_version, profile_id, request_hash, task025_hydraulic_authority_hash, task025_result_hash, task026_result_hash, property_snapshot_hash, production_canonical_component_result_records, warnings, blockers, deferred_capabilities, provenance)`.
6. Replay `compute_result_id(result_hash)`.
7. Return trusted evidence: per-component map keyed by `component_id`, `result_hash`, `result_id`, common identity fields.

Blocked/raw-blocked producer variants never enter engineering.

### 5.3 Common runtime identity fields

```text
TASK029_COMMON_RUNTIME_IDENTITY_FIELDS=(
  profile_id,
  task025_hydraulic_authority_hash,
  task025_result_hash,
  task026_result_hash,
  property_snapshot_hash,
)
```

All compare by exact string equality. `CLOSEST_MATCH=false`, `HASH_RECONCILIATION=false`, `IDENTITY_INFERENCE=false`.
## 6. Typed validation scheduler T00–T12

Frozen scheduler semantics from Issue #173:

| Stage | Name | Responsibility |
|-------|------|----------------|
| T00 | `T00_ROUTE_UPSTREAM_BLOCKED_AND_REQUIRE_EXACT_TYPES` | Route raw/typed blocked upstream; require exact success types |
| T01 | `T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS` | Validate TASK-027/TASK-028 schema versions |
| T02 | `T02_REPLAY_UPSTREAM_RESULT_HASH_AND_UUID` | Production hash and UUID replay |
| T03 | `T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS` | Require empty warnings/blockers on upstream success |
| T04 | `T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES` | Profile and common identity equality |
| T05 | `T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES` | Composition/member/exclusion authority tree and hashes |
| T06 | `T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS` | One-to-one producer-member binding |
| T07 | `T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE` | START_TO_END, multiplicity, K convention, pressure quantum |
| T08 | `T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY` | Global order, boundaries, path topology predicates |
| T09 | `T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS` | Exclusion partition and completeness proof |
| T10 | `T10_BUILD_SUCCESS_LEDGER` | Build completeness ledger (zero blockers only) |
| T11 | `T11_SUM_ORDERED_PRESSURE_CONTRIBUTIONS` | Ordered Decimal composition |
| T12 | `T12_BUILD_SUCCESS_IDENTITY` | Success result hash, UUID, provenance |

T02/T03 ownership and interaction (frozen R4):

| Stage | Blockers owned |
|-------|----------------|
| T02 `T02_REPLAY_UPSTREAM_RESULT_HASH_AND_UUID` | `BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID`, `BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID` |
| T03 `T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS` | `BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY` |

Execution order:

```text
T00 exact type validation first
T01 schema validation second
T02 identity replay only after safe exact type/schema
T03 diagnostics inspection only after safe exact type/schema
```

T03 may execute even if T02 emitted an identity blocker because `warnings` and `blockers` are structurally safe on an exact accepted typed object. Independent T02 + T03 blockers may accumulate (`EMIT_ALL_SAFE_INDEPENDENT_BLOCKERS=true`).

TASK-027 example — valid type, valid schema, valid `result_hash`, valid `result_id`, `warnings != ()`, `blockers == ()`:

```text
EMIT=BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY at task027_success_result.warnings
MUST_NOT_EMIT=BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID
MUST_NOT_EMIT=BL_T029_UPSTREAM_IDENTITY_MISMATCH
MUST_NOT_EMIT=BL_T029_UPSTREAM_TASK027_TYPE_INVALID
MUST_NOT_EMIT=BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED
```

TASK-028 `warnings != ()` may independently trigger both `BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID` (T02) and `BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY` (T03) when both predicates hold (`TASK028_WARNINGS_NONEMPTY_MAY_ACCUMULATE_WITH_IDENTITY_INVALID=true`).

T03 field paths (individual STRING values; one blocker entry per distinct `field_path`):

```text
task027_success_result.warnings
task027_success_result.blockers
task028_success_result.warnings
task028_success_result.blockers
```

Rules:

```text
T00_BLOCKED_VARIANTS=TERMINAL_BEFORE_ENGINEERING
T00_IF_BOTH_UPSTREAMS_BLOCKED=EMIT_BOTH_ROUTING_BLOCKERS_IN_REGISTRY_ORDER
TYPE_OR_SCHEMA_FAILURE=NO_IDENTITY_REPLAY_FOR_THAT_INVALID_OBJECT

EXACT_TYPE_VALIDATION_PRECEDES_SCHEMA_VALIDATION=true
EXACT_SCHEMA_VALIDATION_PRECEDES_IDENTITY_REPLAY=true
T03_SAFE_WHEN_EXACT_ACCEPTED_TYPE_SCHEMA_ESTABLISHED=true
T03_MAY_EXECUTE_EVEN_IF_T02_EMITTED_IDENTITY_BLOCKER=true
T02_T03_INDEPENDENT_BLOCKERS_MAY_ACCUMULATE=true
EMIT_ALL_SAFE_INDEPENDENT_BLOCKERS=true

T01_THROUGH_T09=ACCUMULATE_ALL_SAFE_APPLICABLE_BLOCKERS
PATH_PREDICATES=EVALUATE_ALL_INDEPENDENTLY_WHEN_MEMBER_BINDING_EXISTS
EMIT_ALL_TRUE_PATH_PREDICATES=true

ANY_BLOCKER_AFTER_T09=RETURN_BLOCKED
T10_THROUGH_T12_REQUIRE_ZERO_BLOCKERS=true
NO_PARTIAL_ENGINEERING_ON_ANY_BLOCKER=true
```

Implementation: `validation.py` owns stage functions including T03 upstream diagnostics validation; `upstream_replay.py` owns T02 production replay only; `pipeline.py` calls `run_validation_scheduler()`.

F_T029_DC_001_RESOLVED_BY_SOURCE_R4=true
RESOLUTION=BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY
ORDINAL=42
OWNER_STAGE=T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS
## 7. Path binding algorithm

Owner: `path_binding.py`. Invoked at T06 and T08.

Required sequence (12 steps):

1. Canonical-sort member authorities by `global_path_sequence_index` ASC.
2. Require contiguous zero-based domain `0..N-1`.
3. Require exactly one TASK-027 member (`producer_task=TASK-027`, `DISTRIBUTED_FRICTION`).
4. Build TASK-028 component map keyed by `component_id` from replay evidence.
5. Enforce one-to-one member/component mapping (no duplicate `member_id` or `component_id`).
6. For each TASK-028 member, compare: `component_id`, `component_type`, `authority_hash`, `expected_multiplicity`, `expected_upstream_reference_plane`, `expected_downstream_reference_plane`.
7. Bind TASK-027 straight friction segment: `producer_component_identity=STRAIGHT_TUBE_FRICTION`, `expected_producer_authority_hash=""`.
8. Build unified ordered serial member list `M0..M(n-1)` in global index order.
9. Check authority `start_reference_plane` / `end_reference_plane` against first/last member planes.
10. Evaluate topology predicates: `SELF_LOOP`, `CYCLE`, `FORK`, `JOIN`, `OVERLAPPING_PATH_SEGMENT`, `REFERENCE_PLANE_DISCONTINUITY`, `PATH_BOUNDARY_INVALID`.
11. Emit all independent safely evaluable predicates (`EMIT_ALL_TRUE_PATH_PREDICATES=true`).
12. Never infer geometric overlap beyond frozen reference-plane semantics.

Data structures:

- `OrderedMemberList`: tuple sorted by global index (deterministic traversal).
- `ComponentMap`: `dict[str, TubeSideLocalLossComponentResult]` keyed by `component_id` (O(1) lookup).
- `PlaneSequence`: list of planes `P0..Pn` from chained members (cycle/fork/join detection).
- `DirectedSegmentSet`: `set[tuple[str,str]]` of `(upstream, downstream)` pairs (overlap detection).

Reference plane identifiers are opaque exact UTF-8 strings. No trim, case fold, Unicode normalization, aliasing, or geometric inference.
## 8. Exclusion and completeness algorithm

Owner: `completeness.py`. Invoked at T09.

### 8.1 Required v0.2 exclusions (V0_2_OUT_OF_SCOPE)

```text
PASS_PARTITION
RETURN_HEADER
RETURN_BEND
U_BEND
```

Each requires exactly one exclusion authority with `exclusion_reason=V0_2_OUT_OF_SCOPE`.

### 8.2 In-scope TASK-028 component types

```text
ENTRANCE, EXIT, CHANNEL_HEAD, NOZZLE, CONTRACTION, EXPANSION
```

For each in-scope type:

- if `observed_count > 0`: a type-level `PHYSICALLY_ABSENT` exclusion for that type is **forbidden**;
- if `observed_count == 0`: exactly one `PHYSICALLY_ABSENT` exclusion for that type is **required**.

### 8.3 Algorithm

1. Validate each `TubeSidePressurePathExclusionAuthority`: schema, reason enum, non-empty sorted unique `evidence_refs`, replay `exclusion_authority_hash`.
2. Canonical-sort exclusions by `exclusion_id` UTF8 ASC.
3. Count observed TASK-028 members per `component_type` from bound producer map.
4. Verify all four `V0_2_OUT_OF_SCOPE` exclusions present with correct identities.
5. For each in-scope type, apply partition rule above.
6. Reject hidden exclusion inference; missing is never silently reclassified as excluded/zero.
7. Transform validated exclusions into `TubeSidePressurePathLedgerExclusionEvidence` with `exclusion_status=VERIFIED_EXCLUSION`.
8. Set completeness statuses only when ledger is complete within explicit modeled boundary.

Same-path proof requires: valid composition/member/exclusion hashes; producer result identity replay; common upstream identity equality; one-to-one producer-member binding; TASK-028 exact component type/authority hash binding; START_TO_END direction; exact global order; exact reference-plane chain; exact exclusion partition coverage. Numerical addability alone is never sufficient.
## 9. Multiplicity — no double multiplication

```text
TASK027_COMPOSED_PRESSURE_FIELD=straight_tube_friction_pressure_drop_pa
TASK028_COMPOSED_PRESSURE_FIELD=component_irreversible_pressure_loss_pa
TASK028_SINGLE_OCCURRENCE_FIELD_IS_EVIDENCE_ONLY=true
TASK029_REAPPLY_TASK028_MULTIPLICITY=false
TASK029_MULTIPLICITY_ENGINEERING_RECOMPUTATION=false
DOUBLE_MULTIPLICATION=FORBIDDEN
```

TASK-028 `component_irreversible_pressure_loss_pa` **already contains multiplicity**. TASK-029 must never compute `component_pressure * multiplicity`.

Exact rule in `composition.py`:

1. Validate `observed_multiplicity == expected_multiplicity` (T07).
2. Extract contribution from frozen composed pressure field only.
3. Add contribution **once** in global serial order.
4. TASK-027 observed multiplicity is exactly 1.
5. Active tube count is never a pressure-drop multiplier.

Unit/sign authority is producer schema semantics:

```text
UNIT_COMPATIBILITY_BOUND_BY_EXACT_PRODUCER_SCHEMA=true
SIGN_SEMANTICS_BOUND_BY_EXACT_PRODUCER_SCHEMA_AND_POSITIVE_VALUE_CHECK=true
loss_coefficient_convention=K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
```
## 10. Decimal composition pseudocode

Owner: `composition.py` — `sum_ordered_contributions()`.

```python
def sum_ordered_contributions(contributions: tuple[Decimal, ...]) -> Decimal:
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        total = Decimal("0")
        for contribution in contributions:  # already sorted by global_path_sequence_index
            # validate exact Decimal (not float, not str coercion)
            if not contribution.is_finite():
                raise ArithmeticFailure  # BL_T029_ARITHMETIC_FAILURE
            if contribution <= Decimal("0"):
                raise NonPositiveFailure  # BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE
            quantum = Decimal("0.001")
            if contribution.quantize(quantum, ROUND_HALF_EVEN) != contribution:
                raise QuantumMismatch  # BL_T029_PRESSURE_QUANTUM_MISMATCH
            total += contribution  # no intermediate requantization
        total = total.quantize(Decimal("0.001"), ROUND_HALF_EVEN)
    if total == Decimal("0"):
        total = Decimal("0.000")  # normalize negative zero
    return total
```

```text
TASK029_DECIMAL_PRECISION=28
TASK029_ROUNDING_MODE=ROUND_HALF_EVEN
TASK029_PRESSURE_QUANTUM_PA=0.001
INPUT_REQUANTIZATION=false
INTERMEDIATE_REQUANTIZATION=false
FINAL_TOTAL_QUANTIZATION=true
TASK029_PRESSURE_UNIT=Pa
TASK029_PRESSURE_SEMANTICS=POSITIVE_IRREVERSIBLE_MODELED_PRESSURE_LOSS_MAGNITUDE
UNIT_CONVERSION=false
SIGN_INVERSION=false
FANNING_DARCY_CONVERSION=false
```
## 11. Canonical and identity ownership functions

Owner: `identity.py` + `canonical.py`.

### 11.1 Generic framing (frozen)

```text
VALUE = U32_BE(kind_len) || kind_ascii || U64_BE(payload_len) || payload

RECORD =
  U32_BE(namespace_len) || namespace_utf8 || U32_BE(field_count)
  || repeated[ U32_BE(field_name_len) || field_name_utf8 || VALUE ]

TUPLE = U32_BE(item_count) || repeated[ U64_BE(child_frame_len) || child_frame ]

INTEGER = base-10 ASCII; no plus; no leading zero except zero
PRESSURE_DECIMAL = fixed scale 3; no exponent; no plus; negative zero normalized
SHA256 = lowercase hex
```

### 11.2 Exact kind-tag maps (frozen)

```text
MEMBER_AUTHORITY_HASH_KIND_TAGS=(STRING,STRING,INTEGER,ENUM,ENUM,STRING,ENUM,STRING,STRING,STRING,INTEGER,TUPLE)
EXCLUSION_AUTHORITY_HASH_KIND_TAGS=(STRING,STRING,STRING,ENUM,TUPLE)
COMPOSITION_AUTHORITY_HASH_KIND_TAGS=(STRING,STRING,ENUM,STRING,STRING,TUPLE,TUPLE,TUPLE)
REQUEST_HASH_KIND_TAGS=(STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING)
LEDGER_MEMBER_KIND_TAGS=(STRING,STRING,INTEGER,ENUM,STRING,ENUM,STRING,ENUM,STRING,STRING,STRING,INTEGER,INTEGER,DECIMAL,STRING,ENUM)
LEDGER_EXCLUSION_KIND_TAGS=(STRING,STRING,STRING,ENUM,TUPLE,STRING,ENUM)
LEDGER_HASH_KIND_TAGS=(STRING,STRING,STRING,STRING,INTEGER,INTEGER,TUPLE,TUPLE,ENUM,ENUM,ENUM)
SUCCESS_HASH_KIND_TAGS=(STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,RECORD,DECIMAL,TUPLE,TUPLE,TUPLE,RECORD)
BLOCKED_HASH_KIND_TAGS=(STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,STRING,RAW_PROJECTION,NONE_OR_RAW_PROJECTION,TUPLE,TUPLE,TUPLE,NONE_OR_RECORD)
PROVENANCE_KIND_TAGS=(STRING,STRING,STRING,TUPLE,TUPLE)
BLOCKER_ENTRY_KIND_TAGS=(ENUM,STRING,STRING,TUPLE)
RAW_PROJECTION_KIND_TAGS=(STRING,STRING)
RAW_BOUNDARY_BLOCKED_KIND_TAGS=(STRING,STRING,RAW_PROJECTION,TUPLE,TUPLE,TUPLE)
```

### 11.3 UUID contract

```text
RESULT_ID_NAMESPACE=a0290000-0000-5000-8000-000000000001
RESULT_ID_NAME_PREFIX=task029-result-v1::
RESULT_ID=UUIDv5(namespace,prefix+result_hash)
```

### 11.4 Fixed ownership API (`identity.py`)

| Function | Input | Output |
|----------|-------|--------|
| `canonicalize_member_authority(authority)` | `TubeSidePressurePathMemberAuthority` | `bytes` |
| `compute_member_authority_hash(authority)` | member authority | lowercase SHA-256 hex |
| `canonicalize_exclusion_authority(authority)` | exclusion authority | `bytes` |
| `compute_exclusion_authority_hash(authority)` | exclusion authority | lowercase SHA-256 hex |
| `canonicalize_composition_authority(authority)` | composition authority | `bytes` |
| `compute_composition_authority_hash(authority)` | composition authority | lowercase SHA-256 hex |
| `canonicalize_request_projection(request)` | 9-field projection | `bytes` |
| `compute_request_hash(projection)` | projection | lowercase SHA-256 hex |
| `canonicalize_ledger(ledger)` | completeness ledger | `bytes` |
| `compute_ledger_hash(ledger)` | ledger | lowercase SHA-256 hex |
| `canonicalize_success_result(result)` | success result minus self-fields | `bytes` |
| `compute_success_result_hash(result)` | success result | lowercase SHA-256 hex |
| `canonicalize_blocked_result(result)` | blocked result minus self-fields | `bytes` |
| `compute_blocked_result_hash(result)` | blocked result | lowercase SHA-256 hex |
| `canonicalize_raw_boundary_blocked(result)` | raw-boundary blocked | `bytes` |
| `compute_raw_boundary_blocked_hash(result)` | raw-boundary blocked | lowercase SHA-256 hex |
| `derive_result_id(result_hash)` | result hash | UUID string |

Hash self-exclusion: success/blocked hashes exclude `result_hash` and `result_id`.
## 12. Raw-boundary design

Owners: `raw_boundary.py`, `raw_projection.py`.

### 12.1 Closed raw value encoder

```text
RAW_NONE, RAW_BOOL, RAW_INTEGER, RAW_STRING, RAW_DECIMAL, RAW_DICT, RAW_LIST, RAW_TUPLE, RAW_UNSUPPORTED
```

Payload rules:

```text
RAW_NONE: empty
RAW_BOOL: ASCII "true" or "false"  # bool-before-int handling required
RAW_INTEGER: canonical base-10 ASCII
RAW_STRING: UTF-8
RAW_DECIMAL: exact Decimal str(value), preserving raw scale/sign
RAW_LIST/RAW_TUPLE: TUPLE-style count + length-prefixed child raw frames
RAW_DICT: insertion order preserved; U32 count + repeated[key_frame_len + raw_key_frame + value_frame_len + raw_value_frame]
RAW_UNSUPPORTED: UTF-8 type(value).__module__ + "." + type(value).__qualname__
```

Forbidden: `float_to_Decimal`, `numeric_string_to_Decimal`, generic `Mapping`, generic `Sequence`, `repr()`, `str()` fallback, custom iteration.

### 12.2 Raw validation stages

| Stage | Module | Action |
|-------|--------|--------|
| RAW_S00 | `raw_boundary.py` | Top-level must be exact `dict`; detect unknown fields; required fields present |
| RAW_S01 | `raw_projection.py` | Canonicalize each scalar with closed encoder |
| RAW_S02 | `raw_boundary.py` | Build `FrozenTask029RawProjection` with `canonical_bytes_hex` |
| RAW_S03 | `raw_boundary.py` | On failure: `build_raw_boundary_blocked_result()` (6-field contract) |
| RAW_S04 | `request.py` | On success: construct typed `Task029Request` (upstream objects must already be typed success instances supplied alongside raw authority) |

`task029.upstream-blocked-set` encodes two-key raw dict: `task027 -> None | blocked payload`, `task028 -> None | blocked payload`.
## 13. Blocker registry — 43 codes

```text
BLOCKER_REGISTRY_COUNT=43
BLOCKER_REACHABILITY_TEST_COUNT=43
UNREACHABLE_BLOCKER_COUNT=0
```

| BLOCKER_CODE | OWNER_STAGE | TRIGGER | FIELD_PATH | CAN_ACCUMULATE | TERMINAL |
|--------------|-------------|---------|------------|----------------|----------|
| `BL_T029_REQUEST_UNKNOWN_FIELD` | RAW_S00 | unknown top-level or nested field | `unexpected` | False | True |
| `BL_T029_RAW_INPUT_BOUNDARY_MALFORMED` | RAW_S00 | raw boundary structural failure | `request` | False | True |
| `BL_T029_REQUIRED_FIELD_MISSING` | RAW_S00 | required raw field absent | `request` | False | True |
| `BL_T029_UPSTREAM_TASK027_RAW_BLOCKED` | T00 | TASK-027 raw blocked upstream | `task027_success_result` | False | True |
| `BL_T029_UPSTREAM_TASK027_TYPED_BLOCKED` | T00 | TASK-027 typed blocked upstream | `task027_success_result` | False | True |
| `BL_T029_UPSTREAM_TASK028_RAW_BLOCKED` | T00 | TASK-028 raw blocked upstream | `task028_success_result` | False | True |
| `BL_T029_UPSTREAM_TASK028_TYPED_BLOCKED` | T00 | TASK-028 typed blocked upstream | `task028_success_result` | False | True |
| `BL_T029_UPSTREAM_TASK027_TYPE_INVALID` | T00 | not exact Task027SuccessResult | `task027_success_result` | False | True |
| `BL_T029_UPSTREAM_TASK028_TYPE_INVALID` | T00 | not exact Task028SuccessResult | `task028_success_result` | False | True |
| `BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED` | T01 | schema_version not in supported set | `task027_success_result.schema_version|task028_success_result.schema_version` | True | False |
| `BL_T029_UPSTREAM_IDENTITY_MISMATCH` | T04 | common identity field inequality | `task028_success_result.property_snapshot_hash` | True | False |
| `BL_T029_PROFILE_MISMATCH` | T04 | profile_id mismatch across request/upstream | `profile_id` | True | False |
| `BL_T029_FLOW_DIRECTION_MISMATCH` | T05 | flow_direction_assertion != START_TO_END | `composition_authority.flow_direction_assertion` | True | False |
| `BL_T029_COMPOSITION_AUTHORITY_MISSING` | T05 | composition_authority is None | `composition_authority` | True | False |
| `BL_T029_COMPOSITION_AUTHORITY_MALFORMED` | T05 | composition authority structural invalid | `composition_authority` | True | False |
| `BL_T029_COMPOSITION_AUTHORITY_HASH_MISMATCH` | T05 | composition_authority_hash replay mismatch | `composition_authority.composition_authority_hash` | True | False |
| `BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH` | T05 | member_authority_hash replay mismatch | `composition_authority.member_authorities[].member_authority_hash` | True | False |
| `BL_T029_REQUEST_HASH_MISMATCH` | T05 | request_hash replay mismatch | `request_hash` | True | False |
| `BL_T029_MODELED_PATH_BOUNDARY_INVALID` | T08 | start/end boundary mismatch | `composition_authority.start_reference_plane|end_reference_plane` | True | False |
| `BL_T029_EMPTY_MODELED_PATH` | T08 | member_authorities empty | `composition_authority.member_authorities` | True | False |
| `BL_T029_EXPECTED_MEMBER_MISSING` | T06 | authority member not bound to producer | `composition_authority.member_authorities[].member_id` | True | False |
| `BL_T029_UNEXPECTED_EXTRA_MEMBER` | T06 | producer member not in authority | `task028_success_result.component_results` | True | False |
| `BL_T029_DUPLICATE_MEMBER` | T06 | duplicate member_id or component_id | `composition_authority.member_authorities` | True | False |
| `BL_T029_OUT_OF_ORDER_MEMBER` | T08 | global index not contiguous zero-based | `composition_authority.member_authorities[].global_path_sequence_index` | True | False |
| `BL_T029_OVERLAPPING_PATH_SEGMENT` | T08 | duplicate directed plane pair | `composition_authority.member_authorities` | True | False |
| `BL_T029_REFERENCE_PLANE_DISCONTINUITY` | T08 | Mi.downstream != M(i+1).upstream | `composition_authority.member_authorities` | True | False |
| `BL_T029_REFERENCE_PLANE_SELF_LOOP` | T08 | upstream == downstream on member | `composition_authority.member_authorities` | True | False |
| `BL_T029_PATH_CYCLE` | T08 | repeated plane in P0..Pn | `composition_authority.member_authorities` | True | False |
| `BL_T029_PATH_FORK` | T08 | distinct members share upstream plane | `composition_authority.member_authorities` | True | False |
| `BL_T029_PATH_JOIN` | T08 | distinct members share downstream plane | `composition_authority.member_authorities` | True | False |
| `BL_T029_MULTIPLICITY_INCOMPATIBILITY` | T07 | observed != expected multiplicity | `composition_authority.member_authorities[].expected_multiplicity` | True | False |
| `BL_T029_PRODUCER_CONVENTION_MISMATCH` | T07 | loss coefficient convention mismatch | `task028_success_result.component_results` | True | False |
| `BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID` | T02 | TASK-027 hash/id replay failure | `task027_success_result.result_hash` | False | False |
| `BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID` | T02 | TASK-028 hash/id replay failure | `task028_success_result.result_hash` | False | False |
| `BL_T029_PRESSURE_CONTRIBUTION_NONFINITE` | T07 | contribution not finite Decimal | `task027_success_result.straight_tube_friction_pressure_drop_pa|component_irreversible_pressure_loss_pa` | True | False |
| `BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE` | T07 | contribution <= 0 | `task027_success_result.straight_tube_friction_pressure_drop_pa|component_irreversible_pressure_loss_pa` | True | False |
| `BL_T029_PRESSURE_QUANTUM_MISMATCH` | T07 | contribution not 0.001 Pa quantum | `task027_success_result.straight_tube_friction_pressure_drop_pa|component_irreversible_pressure_loss_pa` | True | False |
| `BL_T029_EXCLUSION_AUTHORITY_INVALID` | T09 | exclusion authority invalid/hash mismatch | `composition_authority.exclusion_authorities` | True | False |
| `BL_T029_EXCLUSION_EVIDENCE_MISSING` | T09 | required PHYSICALLY_ABSENT missing | `composition_authority.exclusion_authorities` | True | False |
| `BL_T029_COMPLETENESS_LEDGER_INCOMPLETE` | T09 | partition coverage incomplete | `composition_authority.exclusion_authorities` | True | False |
| `BL_T029_PARTIAL_RESULT_FORBIDDEN` | T09_BLOCKED_BUILD | blocked builder exposes ledger/total | `result` | False | True |
| `BL_T029_ARITHMETIC_FAILURE` | T11 | Decimal sum failure | `modeled_total_tube_side_pressure_drop_pa` | False | False |
| `BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY` | T03 | exact accepted TASK-027/TASK-028 success result has `warnings != ()` or `blockers != ()` | `task027_success_result.warnings`, `task027_success_result.blockers`, `task028_success_result.warnings`, `task028_success_result.blockers` | True | False |

Deduplication key: `(code, field_path, evidence_refs)`. `message_key == code`. Ordering: `(registry_index ASC, field_path UTF8 ASC, evidence_refs tuple lexical ASC)`.
## 14. Success and blocked result builders

Owner: `result.py`.

### 14.1 Success builder (`build_success_result`)

May run only after T09 with zero blockers.

1. Construct ordered `TubeSidePressurePathLedgerMemberEvidence` (T10).
2. Construct ordered `TubeSidePressurePathLedgerExclusionEvidence` (T10).
3. Build `TubeSidePressurePathCompletenessLedger` with frozen success statuses (T10). `Task029SuccessResult.completeness_ledger` embeds the complete verified 12-field `TubeSidePressurePathCompletenessLedger` including `ledger_hash`. The success canonical projection therefore consumes the complete ledger record required by frozen VECTOR_06.
4. Replay `compute_ledger_hash()` and verify `ledger_hash`.
5. Compose `modeled_total_tube_side_pressure_drop_pa` via `sum_ordered_contributions()` (T11).
6. Build `Task029Provenance` with `design_contract_path=docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md`.
7. Assemble `Task029SuccessResult` with `warnings=()`, `blockers=()`.
8. Compute `compute_success_result_hash()` and `derive_result_id()` (T12).

F_T029_DC_003_RESOLVED=true

### 14.2 Typed blocked builder (`build_blocked_result`)

Runs when any blocker exists after T09 (or T00 terminal upstream routing).

Never includes: completeness ledger, `modeled_total_tube_side_pressure_drop_pa`, partial engineering.

May include: `raw_request_projection`, `raw_upstream_blocked_projection` (or `NONE`), empty-string identity placeholders, `provenance=NONE`.

Enforces `BL_T029_PARTIAL_RESULT_FORBIDDEN` if builder would expose partial outputs.

### 14.3 Raw-boundary blocked builder (`build_raw_boundary_blocked_result`)

Exact frozen 6-field contract. Schema `task029.raw-boundary-blocked-result.v1`. No typed engineering fields.
## 15. Provenance

```text
design_contract_path=docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md
```

Frozen provenance fixture values (oracle §10.6):

```text
task_id=TASK-029
design_contract_path=docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md
implementation_software_version=0.2.0-dev

input_evidence_refs=(
 "github-issue:xuezhiorange-png/hxforge-agent#167",
 "github-issue:xuezhiorange-png/hxforge-agent#173",
 "git-commit:6dd4bfa81a330fb36eec4cb262664184657279d4",
)

upstream_identity_hashes=(
 2727272727272727272727272727272727272727272727272727272727272727,
 2828282828282828282828282828282828282828282828282828282828282828,
 2525252525252525252525252525252525252525252525252525252525252525,
 1515151515151515151515151515151515151515151515151515151515151515,
 2626262626262626262626262626262626262626262626262626262626262626,
 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,
 71b540bfe29373cd6056f8cf3f9098fe9d126c82b06856e158fc844a357c7553,
)
```

No filesystem, network, or database lookup at runtime.
## 16. Oracle vectors — 8 frozen external constants

```text
CANONICAL_VECTOR_COUNT=8
ORACLE_VECTOR_COUNT=8
ORACLE_VECTOR_VALUES_CHANGED=false
ORACLE_REPLAY_PASS_COUNT=8
```

R4 does not change existing oracle bytes. `Task029BlockerEntry` canonical bytes encode only `code`, `field_path`, `message_key`, and `evidence_refs`. The global blocker registry member count and ordinal table are not embedded inside existing blocker-entry vectors. Adding ordinal 42 is additive registry metadata and does not alter VECTOR_07 or VECTOR_08.

Do not recalculate. Production code under test must not generate its own expected values.

### 16.1 Common synthetic inputs

```text
PROFILE_ID=profile-001
TASK025_HYDRAULIC_AUTHORITY_HASH=2525252525252525252525252525252525252525252525252525252525252525
TASK025_RESULT_HASH=1515151515151515151515151515151515151515151515151515151515151515
TASK026_RESULT_HASH=2626262626262626262626262626262626262626262626262626262626262626
TASK027_RESULT_HASH=2727272727272727272727272727272727272727272727272727272727272727
TASK028_RESULT_HASH=2828282828282828282828282828282828282828282828282828282828282828
PROPERTY_SNAPSHOT_HASH=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
TASK028_COMPONENT_AUTHORITY_HASH=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```
### 16.2 VECTOR_01 — Member M000 hash

```text
VECTOR_01_M000_HASH_INPUT_LEN=798
VECTOR_01_M000_HASH=9fdd83ffcaed0e03cc2178023a1b2dd084bfe85a8f9396c9cf2f41059009868e
```

Test mapping: `T029_AUTH_001_MEMBER_M000_HASH_VECTOR`.
### 16.3 VECTOR_02 — Member M001 hash

```text
VECTOR_02_M001_HASH_INPUT_LEN=767
VECTOR_02_M001_HASH=e590c0a0f9a60c8088da7c8e8d8220cd274dc703da3c3daedd65de88a05c0929
```

Test mapping: `T029_AUTH_002_MEMBER_M001_HASH_VECTOR`.
### 16.4 VECTOR_03 — Composition authority hash

```text
VECTOR_03_COMPOSITION_HASH_INPUT_LEN=6840
VECTOR_03_COMPOSITION_HASH=71b540bfe29373cd6056f8cf3f9098fe9d126c82b06856e158fc844a357c7553
VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH=71b540bfe29373cd6056f8cf3f9098fe9d126c82b06856e158fc844a357c7553
```

Test mapping: `T029_AUTH_004_COMPOSITION_HASH_VECTOR`, `T029_AUTH_005_CALLER_MEMBER_ORDER_PERMUTATION`, `T029_ID_010_CALLER_PERMUTATION_REQUEST_IDENTITY`.
### 16.5 VECTOR_04 — Request hash

```text
VECTOR_04_REQUEST_HASH_INPUT_LEN=881
VECTOR_04_REQUEST_HASH=23f0d73c8e5c3dd531570723c09c2ea57b1a059213c0445c91690d5ee5c4167c
```

Test mapping: `T029_ID_001_REQUEST_HASH_VECTOR`.
### 16.6 VECTOR_05 — Ledger hash

```text
VECTOR_05_LEDGER_HASH_INPUT_LEN=7567
VECTOR_05_LEDGER_HASH=9fa0fc68a33ec81e551b0fa79557f62e3b4fdb6eb461a1d43b4cc8514f9c949c
```

Test mapping: `T029_LED_005_LEDGER_HASH_VECTOR`.
### 16.7 VECTOR_06 — Success result

```text
MODELED_TOTAL=101.504+250.000=351.504
VECTOR_06_SUCCESS_HASH_INPUT_LEN=10505
VECTOR_06_SUCCESS_RESULT_HASH=1fa5ef8a46de30132e4540be87b1b38f6098ce65aa60fb301eb85480309690d4
VECTOR_06_SUCCESS_RESULT_ID=eeaad53c-5843-52d4-9a7e-3e0c4511976f
VECTOR_06_MODELED_TOTAL=351.504
```

Test mapping: `T029_ID_002_SUCCESS_HASH_VECTOR`, `T029_ID_003_SUCCESS_UUID_VECTOR`, `T029_COMP_008_MODELED_TOTAL_351_504`, `T029_PATH_010_SAME_PHYSICAL_PATH_PROOF`, `T029_ID_009_REPEAT_RUN_IDENTITY`.
### 16.8 VECTOR_07 — Typed blocked result

```text
VECTOR_07_TYPED_BLOCKED_HASH_INPUT_LEN=22660
VECTOR_07_TYPED_BLOCKED_RESULT_HASH=264c9e50a528a77cae05ccd00d2e1e31029c347eb694be431bd646c9b94ed5f1
VECTOR_07_TYPED_BLOCKED_RESULT_ID=3ea9058b-f2c2-5e7d-a0ef-451b83d2a5bb
```

Blocker: `BL_T029_UPSTREAM_IDENTITY_MISMATCH` at `task028_success_result.property_snapshot_hash`.

Test mapping: `T029_ID_004_TYPED_BLOCKED_HASH_VECTOR`, `T029_ID_005_TYPED_BLOCKED_UUID_VECTOR`, `T029_UP_011_COMMON_IDENTITY_MISMATCH`.
### 16.9 VECTOR_08 — Raw-boundary blocked

```text
VALID_RAW_REQUEST_CANONICAL_LEN=10276
VALID_RAW_REQUEST_CANONICAL_SHA256=fb47b48015c0af1b838efcaafa51c6dc759295370fe7fd73b8ad6cda63fe1dcd
UNKNOWN_RAW_REQUEST_CANONICAL_LEN=10347
UNKNOWN_RAW_REQUEST_CANONICAL_SHA256=251aeca74385642f788d827b3e836a90c0a30ae974d1f5ca0bb5381257fa7f4e
VECTOR_08_RAW_BOUNDARY_CANONICAL_LEN=21849
VECTOR_08_RAW_BOUNDARY_CANONICAL_SHA256=5a2f17fcd7b93132007647cd6271b18e8aef7f4cf976ea950c81fceb8b0b87d5
```

Test mapping: `T029_RAW_009_VALID_RAW_REQUEST_VECTOR`, `T029_RAW_010_RAW_BOUNDARY_BLOCKED_VECTOR`, `T029_ID_006_RAW_BOUNDARY_SHA_VECTOR`.
## 17. Frozen TEST_ID inventory and mapping

```text
FROZEN_TEST_ID_COUNT=117
UNIQUE_FROZEN_TEST_ID_COUNT=117
BLOCKER_REACHABILITY_TEST_COUNT=43
BLOCKER_REACHABILITY_VERIFIED_TARGET=43
```

| TEST_ID | TARGET_MODULE | TARGET_FUNCTION/STAGE | EXPECTED_OUTCOME | ORACLE_DEPENDENCY | BLOCKER_CODE_IF_ANY |
|---------|---------------|----------------------|------------------|-------------------|---------------------|
| `T029_BL_000_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage RAW_S00` | BLOCKER_EMITTED | NONE | BL_T029_REQUEST_UNKNOWN_FIELD |
| `T029_BL_001_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage RAW_S00` | BLOCKER_EMITTED | NONE | BL_T029_RAW_INPUT_BOUNDARY_MALFORMED |
| `T029_BL_002_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage RAW_S00` | BLOCKER_EMITTED | NONE | BL_T029_REQUIRED_FIELD_MISSING |
| `T029_BL_003_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK027_RAW_BLOCKED |
| `T029_BL_004_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK027_TYPED_BLOCKED |
| `T029_BL_005_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK028_RAW_BLOCKED |
| `T029_BL_006_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK028_TYPED_BLOCKED |
| `T029_BL_007_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK027_TYPE_INVALID |
| `T029_BL_008_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T00` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK028_TYPE_INVALID |
| `T029_BL_009_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T01` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED |
| `T029_BL_010_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T04` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_IDENTITY_MISMATCH |
| `T029_BL_011_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T04` | BLOCKER_EMITTED | NONE | BL_T029_PROFILE_MISMATCH |
| `T029_BL_012_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_FLOW_DIRECTION_MISMATCH |
| `T029_BL_013_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_COMPOSITION_AUTHORITY_MISSING |
| `T029_BL_014_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_COMPOSITION_AUTHORITY_MALFORMED |
| `T029_BL_015_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_COMPOSITION_AUTHORITY_HASH_MISMATCH |
| `T029_BL_016_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH |
| `T029_BL_017_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T05` | BLOCKER_EMITTED | NONE | BL_T029_REQUEST_HASH_MISMATCH |
| `T029_BL_018_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_MODELED_PATH_BOUNDARY_INVALID |
| `T029_BL_019_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_EMPTY_MODELED_PATH |
| `T029_BL_020_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T06` | BLOCKER_EMITTED | NONE | BL_T029_EXPECTED_MEMBER_MISSING |
| `T029_BL_021_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T06` | BLOCKER_EMITTED | NONE | BL_T029_UNEXPECTED_EXTRA_MEMBER |
| `T029_BL_022_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T06` | BLOCKER_EMITTED | NONE | BL_T029_DUPLICATE_MEMBER |
| `T029_BL_023_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_OUT_OF_ORDER_MEMBER |
| `T029_BL_024_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_OVERLAPPING_PATH_SEGMENT |
| `T029_BL_025_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_REFERENCE_PLANE_DISCONTINUITY |
| `T029_BL_026_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_REFERENCE_PLANE_SELF_LOOP |
| `T029_BL_027_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_PATH_CYCLE |
| `T029_BL_028_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_PATH_FORK |
| `T029_BL_029_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T08` | BLOCKER_EMITTED | NONE | BL_T029_PATH_JOIN |
| `T029_BL_030_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T07` | BLOCKER_EMITTED | NONE | BL_T029_MULTIPLICITY_INCOMPATIBILITY |
| `T029_BL_031_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T07` | BLOCKER_EMITTED | NONE | BL_T029_PRODUCER_CONVENTION_MISMATCH |
| `T029_BL_032_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T02` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID |
| `T029_BL_033_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T02` | BLOCKER_EMITTED | NONE | BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID |
| `T029_BL_034_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T07` | BLOCKER_EMITTED | NONE | BL_T029_PRESSURE_CONTRIBUTION_NONFINITE |
| `T029_BL_035_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T07` | BLOCKER_EMITTED | NONE | BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE |
| `T029_BL_036_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T07` | BLOCKER_EMITTED | NONE | BL_T029_PRESSURE_QUANTUM_MISMATCH |
| `T029_BL_037_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T09` | BLOCKER_EMITTED | NONE | BL_T029_EXCLUSION_AUTHORITY_INVALID |
| `T029_BL_038_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T09` | BLOCKER_EMITTED | NONE | BL_T029_EXCLUSION_EVIDENCE_MISSING |
| `T029_BL_039_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T09` | BLOCKER_EMITTED | NONE | BL_T029_COMPLETENESS_LEDGER_INCOMPLETE |
| `T029_BL_040_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T09_BLOCKED_BUILD` | BLOCKER_EMITTED | NONE | BL_T029_PARTIAL_RESULT_FORBIDDEN |
| `T029_BL_041_REACHABILITY` | `blocker_registry.py / validation.py` | `emit_blocker / stage T11` | BLOCKER_EMITTED | NONE | BL_T029_ARITHMETIC_FAILURE |
| `T029_BL_042_REACHABILITY` | `validation.py` | `T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS` | typed blocked result containing `BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY` at `task027_success_result.warnings` | NONE | BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY |
| `T029_RAW_001_TOP_LEVEL_NOT_DICT` | `raw_boundary.py` | `validate_raw_boundary` | BLOCKED_RAW | NONE | BL_T029_RAW_INPUT_BOUNDARY_MALFORMED |
| `T029_RAW_002_UNKNOWN_FIELD_ACCUMULATION` | `raw_boundary.py` | `validate_raw_boundary` | BLOCKED_RAW | NONE | BL_T029_REQUEST_UNKNOWN_FIELD |
| `T029_RAW_003_REQUIRED_FIELD_MISSING` | `raw_boundary.py` | `validate_raw_boundary` | BLOCKED_RAW | NONE | BL_T029_REQUIRED_FIELD_MISSING |
| `T029_RAW_004_EXACT_RAW_SCALAR_TYPES` | `raw_projection.py` | `canonicalize_raw_value` | EXACT_ENCODING | NONE | NONE |
| `T029_RAW_005_NO_FLOAT_TO_DECIMAL` | `raw_projection.py` | `canonicalize_raw_value` | RAW_UNSUPPORTED | NONE | NONE |
| `T029_RAW_006_NO_MAPPING_SEQUENCE_DUCK_TYPING` | `raw_projection.py` | `canonicalize_raw_value` | RAW_UNSUPPORTED | NONE | NONE |
| `T029_RAW_007_UNSUPPORTED_VALUE_NO_REPR` | `raw_projection.py` | `canonicalize_raw_value` | RAW_UNSUPPORTED | NONE | NONE |
| `T029_RAW_008_DICT_INSERTION_ORDER_PRESERVED` | `raw_projection.py` | `encode_raw_projection` | ORDER_PRESERVED | NONE | NONE |
| `T029_RAW_009_VALID_RAW_REQUEST_VECTOR` | `raw_projection.py` | `encode_raw_projection` | MATCH_SHA | VALID_RAW_REQUEST_CANONICAL_SHA256 | NONE |
| `T029_RAW_010_RAW_BOUNDARY_BLOCKED_VECTOR` | `result.py` | `build_raw_boundary_blocked_result` | MATCH_SHA | VECTOR_08 | BL_T029_REQUEST_UNKNOWN_FIELD |
| `T029_UP_001_TASK027_EXACT_SUCCESS_TYPE` | `upstream_replay.py` | `replay_task027_success` | TYPE_REJECT | NONE | BL_T029_UPSTREAM_TASK027_TYPE_INVALID |
| `T029_UP_002_TASK028_EXACT_SUCCESS_TYPE` | `upstream_replay.py` | `replay_task028_success` | TYPE_REJECT | NONE | BL_T029_UPSTREAM_TASK028_TYPE_INVALID |
| `T029_UP_003_TASK027_SCHEMA_VERSION` | `validation.py` | `T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS` | BLOCKER_IF_BAD | NONE | BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED |
| `T029_UP_004_TASK028_SCHEMA_VERSION` | `validation.py` | `T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS` | BLOCKER_IF_BAD | NONE | BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED |
| `T029_UP_005_TASK027_RESULT_HASH_REPLAY` | `upstream_replay.py` | `replay_task027_success` | HASH_MATCH | NONE | BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID |
| `T029_UP_006_TASK027_RESULT_ID_REPLAY` | `upstream_replay.py` | `replay_task027_success` | UUID_MATCH | NONE | BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID |
| `T029_UP_007_TASK028_RESULT_HASH_REPLAY` | `upstream_replay.py` | `replay_task028_success` | HASH_MATCH | NONE | BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID |
| `T029_UP_008_TASK028_RESULT_ID_REPLAY` | `upstream_replay.py` | `replay_task028_success` | UUID_MATCH | NONE | BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID |
| `T029_UP_009_SUCCESS_WARNINGS_BLOCKERS_EMPTY` | `validation.py` | `T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS` | EMPTY_TUPLES on valid upstream success | NONE | NONE |
| `T029_UP_010_COMMON_IDENTITY_MATCH` | `validation.py` | `T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES` | MATCH | NONE | NONE |
| `T029_UP_011_COMMON_IDENTITY_MISMATCH` | `validation.py` | `T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES` | BLOCKED | VECTOR_07 | BL_T029_UPSTREAM_IDENTITY_MISMATCH |
| `T029_UP_012_PROFILE_MATCH` | `validation.py` | `T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES` | MATCH | NONE | NONE |
| `T029_AUTH_001_MEMBER_M000_HASH_VECTOR` | `identity.py` | `compute_member_authority_hash` | MATCH_SHA | VECTOR_01 | NONE |
| `T029_AUTH_002_MEMBER_M001_HASH_VECTOR` | `identity.py` | `compute_member_authority_hash` | MATCH_SHA | VECTOR_02 | NONE |
| `T029_AUTH_003_EXCLUSION_HASH_VECTORS` | `identity.py` | `compute_exclusion_authority_hash` | MATCH_SHA_X000-X008 | NONE | NONE |
| `T029_AUTH_004_COMPOSITION_HASH_VECTOR` | `identity.py` | `compute_composition_authority_hash` | MATCH_SHA | VECTOR_03 | NONE |
| `T029_AUTH_005_CALLER_MEMBER_ORDER_PERMUTATION` | `identity.py` | `compute_composition_authority_hash` | PERMUTATION_INVARIANT | VECTOR_03_CALLER_MEMBER_ORDER_PERMUTATION_HASH | NONE |
| `T029_AUTH_006_GLOBAL_INDEX_CONTIGUOUS` | `path_binding.py` | `validate_global_index_domain` | CONTIGUOUS | NONE | BL_T029_OUT_OF_ORDER_MEMBER |
| `T029_AUTH_007_TASK027_MEMBER_EXACTLY_ONE` | `path_binding.py` | `require_exactly_one_task027_member` | EXACTLY_ONE | NONE | BL_T029_UNEXPECTED_EXTRA_MEMBER |
| `T029_AUTH_008_TASK028_COMPONENT_ONE_TO_ONE` | `path_binding.py` | `bind_members_to_producers` | ONE_TO_ONE | NONE | BL_T029_DUPLICATE_MEMBER |
| `T029_AUTH_009_TASK028_COMPONENT_TYPE_BINDING` | `path_binding.py` | `bind_members_to_producers` | TYPE_MATCH | NONE | BL_T029_EXPECTED_MEMBER_MISSING |
| `T029_AUTH_010_TASK028_AUTHORITY_HASH_BINDING` | `path_binding.py` | `bind_members_to_producers` | HASH_MATCH | NONE | BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH |
| `T029_AUTH_011_EXPECTED_MULTIPLICITY_BINDING` | `path_binding.py` | `bind_members_to_producers` | MULTIPLICITY_MATCH | NONE | BL_T029_MULTIPLICITY_INCOMPATIBILITY |
| `T029_AUTH_012_EXACT_MEMBER_PLANES` | `path_binding.py` | `bind_members_to_producers` | PLANE_MATCH | NONE | BL_T029_REFERENCE_PLANE_DISCONTINUITY |
| `T029_AUTH_013_FLOW_DIRECTION_START_TO_END` | `validation.py` | `T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES` | START_TO_END | NONE | BL_T029_FLOW_DIRECTION_MISMATCH |
| `T029_AUTH_014_NO_HIDDEN_EXCLUSION` | `completeness.py` | `validate_exclusion_partition` | NO_INFERENCE | NONE | BL_T029_EXCLUSION_EVIDENCE_MISSING |
| `T029_AUTH_015_EVIDENCE_REF_CANONICAL_ORDER` | `canonical.py` | `sort_evidence_refs` | UTF8_ASC | NONE | NONE |
| `T029_AUTH_016_EXCLUSION_PARTITION_COVERAGE` | `completeness.py` | `validate_exclusion_partition` | COMPLETE | NONE | BL_T029_COMPLETENESS_LEDGER_INCOMPLETE |
| `T029_PATH_001_ADJACENT_CONTINUITY` | `path_binding.py` | `evaluate_path_topology` | CONTIGUOUS | NONE | BL_T029_REFERENCE_PLANE_DISCONTINUITY |
| `T029_PATH_002_BOUNDARY_MATCH` | `path_binding.py` | `evaluate_path_topology` | BOUNDARY_MATCH | NONE | BL_T029_MODELED_PATH_BOUNDARY_INVALID |
| `T029_PATH_003_SELF_LOOP` | `path_binding.py` | `evaluate_path_topology` | SELF_LOOP_DETECTED | NONE | BL_T029_REFERENCE_PLANE_SELF_LOOP |
| `T029_PATH_004_CYCLE` | `path_binding.py` | `evaluate_path_topology` | CYCLE_DETECTED | NONE | BL_T029_PATH_CYCLE |
| `T029_PATH_005_FORK` | `path_binding.py` | `evaluate_path_topology` | FORK_DETECTED | NONE | BL_T029_PATH_FORK |
| `T029_PATH_006_JOIN` | `path_binding.py` | `evaluate_path_topology` | JOIN_DETECTED | NONE | BL_T029_PATH_JOIN |
| `T029_PATH_007_OVERLAPPING_DIRECTED_SEGMENT` | `path_binding.py` | `evaluate_path_topology` | OVERLAP_DETECTED | NONE | BL_T029_OVERLAPPING_PATH_SEGMENT |
| `T029_PATH_008_EXPECTED_MEMBER_MISSING` | `path_binding.py` | `bind_members_to_producers` | MISSING_MEMBER | NONE | BL_T029_EXPECTED_MEMBER_MISSING |
| `T029_PATH_009_UNEXPECTED_EXTRA_MEMBER` | `path_binding.py` | `bind_members_to_producers` | EXTRA_MEMBER | NONE | BL_T029_UNEXPECTED_EXTRA_MEMBER |
| `T029_PATH_010_SAME_PHYSICAL_PATH_PROOF` | `validation.py` | `T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY` | FULL_PROOF | VECTOR_06 | NONE |
| `T029_COMP_001_TASK027_PRESSURE_FIELD_BINDING` | `composition.py` | `extract_pressure_contribution` | STRAIGHT_TUBE_FRICTION | NONE | NONE |
| `T029_COMP_002_TASK028_PRESSURE_FIELD_BINDING` | `composition.py` | `extract_pressure_contribution` | COMPONENT_IRREVERSIBLE | NONE | NONE |
| `T029_COMP_003_SINGLE_OCCURRENCE_NOT_ADDED` | `composition.py` | `extract_pressure_contribution` | SINGLE_OCCURRENCE_EVIDENCE_ONLY | NONE | NONE |
| `T029_COMP_004_MULTIPLICITY_NOT_REAPPLIED` | `composition.py` | `sum_ordered_contributions` | NO_DOUBLE_MULTIPLY | NONE | NONE |
| `T029_COMP_005_PRESSURE_FINITE_POSITIVE` | `composition.py` | `validate_contribution` | POSITIVE_FINITE | NONE | BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE |
| `T029_COMP_006_PRESSURE_QUANTUM_001_PA` | `composition.py` | `validate_contribution` | QUANTUM_001 | NONE | BL_T029_PRESSURE_QUANTUM_MISMATCH |
| `T029_COMP_007_GLOBAL_ORDER_DECIMAL_SUM` | `composition.py` | `sum_ordered_contributions` | ORDERED_SUM | NONE | NONE |
| `T029_COMP_008_MODELED_TOTAL_351_504` | `composition.py` | `sum_ordered_contributions` | TOTAL_351_504 | VECTOR_06_MODELED_TOTAL | NONE |
| `T029_COMP_009_ACTIVE_TUBE_COUNT_NOT_MULTIPLIER` | `composition.py` | `sum_ordered_contributions` | NO_TUBE_COUNT_MULT | NONE | NONE |
| `T029_COMP_010_NO_PARTIAL_MODELED_TOTAL` | `result.py` | `build_blocked_result` | NO_PARTIAL_TOTAL | NONE | BL_T029_PARTIAL_RESULT_FORBIDDEN |
| `T029_LED_001_MEMBER_EVIDENCE_SCHEMA` | `result.py` | `build_member_evidence` | 16_FIELDS | NONE | NONE |
| `T029_LED_002_EXCLUSION_EVIDENCE_SCHEMA` | `result.py` | `build_exclusion_evidence` | 7_FIELDS | NONE | NONE |
| `T029_LED_003_COMPLETE_WITHIN_MODELED_BOUNDARY` | `completeness.py` | `build_completeness_ledger` | COMPLETE_STATUS | NONE | NONE |
| `T029_LED_004_EXCLUSION_SELF_DESCRIPTION` | `completeness.py` | `build_completeness_ledger` | SELF_DESCRIBING | NONE | NONE |
| `T029_LED_005_LEDGER_HASH_VECTOR` | `identity.py` | `compute_ledger_hash` | MATCH_SHA | VECTOR_05 | NONE |
| `T029_LED_006_FULL_PHYSICAL_COMPLETENESS_NOT_CLAIMED` | `result.py` | `build_success_result` | DEFERRED_CAPABILITY | NONE | NONE |
| `T029_ID_001_REQUEST_HASH_VECTOR` | `identity.py` | `compute_request_hash` | MATCH_SHA | VECTOR_04 | NONE |
| `T029_ID_002_SUCCESS_HASH_VECTOR` | `identity.py` | `compute_success_result_hash` | MATCH_SHA | VECTOR_06 | NONE |
| `T029_ID_003_SUCCESS_UUID_VECTOR` | `identity.py` | `derive_result_id` | MATCH_UUID | VECTOR_06_SUCCESS_RESULT_ID | NONE |
| `T029_ID_004_TYPED_BLOCKED_HASH_VECTOR` | `identity.py` | `compute_blocked_result_hash` | MATCH_SHA | VECTOR_07 | NONE |
| `T029_ID_005_TYPED_BLOCKED_UUID_VECTOR` | `identity.py` | `derive_result_id` | MATCH_UUID | VECTOR_07_TYPED_BLOCKED_RESULT_ID | NONE |
| `T029_ID_006_RAW_BOUNDARY_SHA_VECTOR` | `raw_projection.py` | `encode_raw_projection` | MATCH_SHA | VECTOR_08 | NONE |
| `T029_ID_007_PY311_PY312_BYTE_IDENTITY` | `identity.py` | `all canonicalize functions` | BYTE_IDENTICAL | ALL_VECTORS | NONE |
| `T029_ID_008_EXACT_KIND_TAG_MAPS` | `canonical.py` | `kind tag constants` | EXACT_MAPS | NONE | NONE |
| `T029_ID_009_REPEAT_RUN_IDENTITY` | `pipeline.py` | `compute_task029_composition` | DETERMINISTIC_REPEAT | VECTOR_06 | NONE |
| `T029_ID_010_CALLER_PERMUTATION_REQUEST_IDENTITY` | `identity.py` | `compute_request_hash` | PERMUTATION_INVARIANT | VECTOR_03 | NONE |

Frozen reachability fixture for `T029_BL_042_REACHABILITY`:

```text
FIXTURE=TASK-027 exact Task027SuccessResult
schema_version=valid
result_hash=valid replay
result_id=valid replay
warnings=("synthetic-warning",)
blockers=()
EXPECTED_BLOCKER=BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY
EXPECTED_FIELD_PATH=task027_success_result.warnings
MUST_NOT_EMIT=BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID
```

`T029_UP_009_SUCCESS_WARNINGS_BLOCKERS_EMPTY` remains unchanged in name and semantic purpose.

## 18. Implementation sequence I01–I19

Design plan only. Not executed in this gate.

| Step | Scope | Deliverable |
|------|-------|-------------|
| I01 | `enums.py`, `models.py`, `canonical.py` constants | Frozen enums, dataclasses, field-order tuples, namespaces |
| I02 | `canonical.py` framing primitives | VALUE/RECORD/TUPLE framing, kind tags |
| I03 | `identity.py` authority hashes | Member/exclusion/composition authority canonicalize + hash |
| I04 | `raw_projection.py` | Closed raw encoder, `encode_raw_projection()` |
| I05 | `upstream_replay.py` | TASK-027/TASK-028 production replay adapters |
| I06 | `blocker_registry.py` | 43-code enum, emit/collapse, message map |
| I07 | `validation.py` T05 | Composition authority tree validators |
| I08 | `path_binding.py` | Producer-member binding (T06) |
| I09 | `path_binding.py` | Path topology validation (T08) |
| I10 | `completeness.py` | Exclusion partition (T09) |
| I11 | `result.py` | Ledger member/exclusion evidence builders (T10) |
| I12 | `composition.py` | Decimal composition (T11) |
| I13 | `identity.py`, `result.py` | Success/blocked identity and builders (T12) |
| I14 | `pipeline.py` | `compute_task029_composition()` orchestration |
| I15 | Frozen vector fixture module | External oracle constants (not generated by SUT) |
| I16 | Blocker reachability tests | 43 `T029_BL_*_REACHABILITY` tests |
| I17 | Full frozen TEST_ID suite | Remaining 74 frozen TEST_ID tests |
| I18 | `T029_ID_007_PY311_PY312_BYTE_IDENTITY` | Cross-version byte identity on py311/py312 |
| I19 | Quality gates | Ruff, mypy, full regression |
## 19. Public API boundary

```text
PUBLIC_API_EXTENSION=false
```

TASK-029 remains an internal exchanger engineering capability under `hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition`. No FastAPI route, CLI command, or top-level package export is authorized unless a separate future authorization changes this.
## 20. Cursor contributor policy

```text
TASK029_CONTRIBUTOR_GOVERNANCE_ERRATUM=001

CONTRIBUTOR_GOVERNANCE_SOURCE=
ISSUE_173_CONTRIBUTOR_ATTRIBUTION_GOVERNANCE_ERRATUM_001

ENGINEERING_DESIGN_REVIEW_RESULT=PASS
ENGINEERING_DESIGN_REVIEW_REOPEN_REQUIRED=false

DESIGN_CONTRACT_STATUS=FROZEN
DESIGN_CONTRACT_FROZEN=true

HXFORGE_IMPLEMENTATION_CONTRIBUTOR=CURSOR

CURSOR_DISTINCT_CONTRIBUTOR_ATTRIBUTION_REQUIRED=true
CURSOR_GITHUB_LINKED_ACCOUNT_REQUIRED=false
CURSOR_ANONYMOUS_GIT_CONTRIBUTOR_ALLOWED=true
CURSOR_REPOSITORY_LOCAL_GIT_IDENTITY_REQUIRED=true

CURSOR_GIT_AUTHOR_NAME=Cursor
CURSOR_GIT_AUTHOR_EMAIL=cursor@local

CURSOR_GIT_IDENTITY_SEMANTICS=
STABLE_REPOSITORY_LOCAL_ANONYMOUS_CONTRIBUTOR

COMMIT_AS_CHARLES_WHEN_CURSOR_ATTRIBUTION_REQUIRED=false

GLOBAL_GIT_IDENTITY_MUTATION_FORBIDDEN=true
GITHUB_ACCOUNT_IMPERSONATION_FORBIDDEN=true
FABRICATED_GITHUB_LOGIN_FORBIDDEN=true
FABRICATED_GITHUB_NOREPLY_ADDRESS_FORBIDDEN=true

PRINT_GIT_CONFIG_USER_NAME_AND_EMAIL_BEFORE_FIRST_COMMIT=true
SILENT_GLOBAL_GIT_IDENTITY_CHANGE=false

CURSOR_GITHUB_ACCOUNT_EXPECTED=false
CURSOR_GITHUB_COMMIT_AUTHOR_MAPPING_EXPECTED=null
CURSOR_CONTRIBUTOR_CLASS=Anonymous
CURSOR_CONTRIBUTOR_EXPECTED_NAME=Cursor
CURSOR_CONTRIBUTOR_EXPECTED_EMAIL=cursor@local
```

Supersedes the previous requirement `CURSOR_GITHUB_LINKED_GIT_IDENTITY_REQUIRED_BEFORE_FIRST_COMMIT=true` and any equivalent statement requiring a GitHub-linked Cursor account.

Repository precedent: `hxforge-agent <hxforge-agent@local>` is tracked by GitHub as contributor type `Anonymous` (commit `0f05efca70b1e8abf6101df9979da4ef75d6de44`). Cursor uses the same class of stable repository-local anonymous Git author attribution: `Cursor <cursor@local>`.

This is not account impersonation, not a fabricated GitHub user, and not a fabricated GitHub noreply address.

No engineering Design Review rerun is required solely for this governance erratum because technical design content is unchanged.
## 21. Design acceptance checklist

| Item | Description | DESIGN_SPECIFIED |
|------|-------------|------------------|
| D01_SOURCE_DEFINITION_EXACT_BINDING | Design binds Issue #173 R4 without semantic change | YES |
| D02_SCOPE_ISOLATION | No TASK-030, no public API, no new physics | YES |
| D03_MODULE_ARCHITECTURE | 17-file package tree frozen | YES |
| D04_EXACT_SCHEMA_MAPPING | All §3 schemas with exact field order/count | YES |
| D05_UPSTREAM_TASK027_REPLAY | Production `compute_result_hash` / `derive_result_id` | YES |
| D06_UPSTREAM_TASK028_REPLAY | Production `compute_success_result_hash` / `compute_result_id` | YES |
| D07_IDENTITY_COMPATIBILITY | Common runtime identity exact string equality | YES |
| D08_MEMBER_AUTHORITY_BINDING | One-to-one TASK-028 component binding | YES |
| D09_REFERENCE_PLANE_TOPOLOGY | 12-step path binding + all predicates | YES |
| D10_EXCLUSION_COMPLETENESS | Partition algorithm for v0.2 + in-scope types | YES |
| D11_MULTIPLICITY_NO_DOUBLE_COUNT | No `pressure * multiplicity` in TASK-029 | YES |
| D12_DECIMAL_COMPOSITION | 28-digit HALF_EVEN, 0.001 quantum, one final quantize | YES |
| D13_CANONICAL_KIND_MAP | All frozen kind-tag maps in §11 | YES |
| D14_RAW_PROJECTION | Closed encoder, bool-before-int, dict order preserved | YES |
| D15_BLOCKER_REGISTRY_43 | 43 codes, exact order, ordinals 00..41 preserved, ordinal 42 additive | YES |
| D16_BLOCKER_REACHABILITY_43 | 43/43 reachability TEST_ID mapped | YES |
| D17_SUCCESS_RESULT_BUILDER | T10–T12 gated success builder | YES |
| D18_TYPED_BLOCKED_BUILDER | No ledger/total/partial engineering | YES |
| D19_RAW_BOUNDARY_BUILDER | Exact 6-field raw-boundary contract | YES |
| D20_PROVENANCE | Frozen path and upstream hash order | YES |
| D21_ORACLE_VECTOR_8_MAPPING | 8/8 vectors with exact SHA/UUID | YES |
| D22_FROZEN_TEST_ID_117_MAPPING | 117/117 TEST_ID mapping table | YES |
| D23_PY311_PY312_BYTE_IDENTITY | Cross-version byte identity test mapped | YES |
| D24_NO_NEW_PHYSICS | TASK029_NEW_PHYSICS_FORMULAS=FORBIDDEN | YES |
| D25_NO_PUBLIC_API_EXTENSION | PUBLIC_API_EXTENSION=false | YES |
| D26_NO_TASK030_SCOPE_IMPORT | No TASK-030 authorization or scope | YES |

```text
DESIGN_ACCEPTANCE_ITEM_COUNT=26
```
## 22. Final governance block

```text
TASK029_DESIGN_CONTRACT_FREEZE_RESULT=PASS

DESIGN_CONTRACT_PATH=
docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md

BASE_SHA=6dd4bfa81a330fb36eec4cb262664184657279d4

SOURCE_DEFINITION_ISSUE=173
SOURCE_DEFINITION_REVISION=R4
SOURCE_DEFINITION_FROZEN=true

TASK029_DESIGN_CONTRACT_R4_REVIEW_RESULT=PASS

DESIGN_CONTRACT_R4_ALIGNED=true
DESIGN_CONTRACT_STATUS=FROZEN
DESIGN_CONTRACT_FROZEN=true
DESIGN_CONTRACT_FREEZE_COMPLETE=true

BLOCKER_REGISTRY_COUNT=43
BLOCKER_REACHABILITY_VERIFIED_COUNT=43
UNREACHABLE_BLOCKER_COUNT=0

FROZEN_TEST_ID_COUNT=117
UNIQUE_FROZEN_TEST_ID_COUNT=117

ORACLE_VECTOR_COUNT=8
ORACLE_REVIEW_PASS_COUNT=8
ORACLE_VECTOR_VALUES_CHANGED=false

DESIGN_ACCEPTANCE_PASS_COUNT=26/26
IMPLEMENTATION_READINESS=PASS

F_T029_DC_001_RESOLVED_BY_SOURCE_R4=true
F_T029_DC_002_RESOLVED=true
F_T029_DC_003_RESOLVED=true
F_T029_DC_004_RESOLVED=true

F_T03_TABLE_DISPOSITION=ACCEPTED_MINOR_NONBLOCKING

TASK029_IMPLEMENTATION_AUTHORIZED=false
TASK030_AUTHORIZED=false

NO_STEP_IMPLIES_THE_NEXT=TRUE
```
