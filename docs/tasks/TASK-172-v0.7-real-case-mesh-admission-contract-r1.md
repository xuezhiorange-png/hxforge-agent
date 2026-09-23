# TASK-172 v0.7 — Real-Case Mesh Admission Contract R1

Task: `TASK172_V0_7_REAL_CASE_MESH_ADMISSION_CONTRACT_R1`
PR: #277 (`OPEN_DRAFT`)
Authorized predecessor: `8703d17e88b9215b755d402bd4686d36f14ad673`
Result: `REAL_CASE_MESH_ADMISSION_CONTRACT_CANDIDATE_COMPLETED`

## Decision and lifecycle

This receipt defines a fail-closed real-case mesh-admission contract candidate.
It does **not** create a production mesh profile, select a real-case initial
mesh or refinement schedule, generalize R103, or enable production Rating.
The contract is complete only as an admission gate whose unresolved production
policy operands evaluate false until separately authority-bound.

```ini
REAL_CASE_MESH_ADMISSION_CONTRACT_ID=TASK172-REAL-CASE-MESH-ADMISSION-CONTRACT-R1
SCHEMA_VERSION=hxforge.task172.real-case-mesh-admission.v1
LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
REAL_CASE_MESH_ADMISSION_CONTRACT_DEFINED=true
REAL_CASE_MESH_ADMISSION_CONTRACT_CANDIDATE_CREATED=true
REAL_CASE_MESH_ADMISSION_REVIEWED_AUTHORITY=false
MESH_AUTHORITY_REAL_CASE_GENERALIZATION_BOUND=false
PRODUCTION_MESH_SELECTION_CONTRACT_BOUND=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
```

R103 remains `REVIEWED_AUTHORITY` only for its frozen synthetic fixture/profile
scope. Its qualification is not evidence that a real exchanger can use the
same cell counts, thresholds, headroom, caps, or numerical reference policy.

## Frozen authority replay

| Authority | Bound identity | Effective scope relevant here |
|---|---|---|
| TASK170 v0.7 freeze | `docs/tasks/TASK-170-v0.7-scope-source-golden-freeze.md`, SHA-256 `5fc00303e3a74a850b22f89a4c56bbad1b269f39d6a32e652b56b19402b22de0` | Production Rating requires explicit case geometry/topology, mesh and numerical-profile authorities; numerical cells remain distinct from physical compartments. |
| TASK171 reviewed entry profile | `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`; reviewed receipt `TASK170-R4-INDEPENDENT-ENTRY-REVIEW-R5`; `docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md`, SHA-256 `62d03bb1d95ee647870b62d2c5a8bafbff4df2fa215c6d282c379a4876311943` | Steady, single-phase, Newtonian; fixed tubesheet; E-shell; one shell pass; one straight-through declared tube pass; explicit opposing countercurrent paths; native accepted geometry and existing TASK020–024 gates. |
| TASK171 R4 topology/mapping receipt | `V07-T171-TOPOLOGY-R4-V1`, `V07-T171-CELL-COMPARTMENT-R4-V1`, `V07-T171-CONSERVATION-R4-V1`; `docs/tasks/TASK-170-v0.7-task171-entry-authority-r4.md`, SHA-256 `ecf01cb2b019a7b43a4dd6241890893fb4238a0a11dec4a1c4e91d780c9e08ca` | Explicit physical and cell identities, event-preserving mapping, exact support/area conservation semantics; no numeric mesh preset. |
| TASK172 mesh-convergence model contract | `V07-T172-MESH-CONVERGENCE-CONTRACT-R1`; `docs/tasks/TASK-172-v0.7-mesh-convergence-contract-r1.md`, SHA-256 `3577f64cc5280d7988068c145fe3e495d58d6548392c6fb7329df070b077cf7c` | Structural identity/refinement/comparison contract; no real sequence, count, threshold, estimator, or mesh profile selected. |
| R98 numerical overlay | `C_round=1.0`, profile hash `029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6`; independent-review receipt SHA-256 `0e3fbb2204f0335201a577fba29cc7210467b7648d10fee0658a449ec67a2aad` | Reviewed mesh-cell-scale residual-acceptance applicability on its fixed synthetic training/holdout scope; not real-case mesh acceptance authority. |
| R102 continuous reference | `SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024`; `docs/tasks/TASK-172-v0.7-continuous-reference-oracle-scipy-canonical-envelope-binding-correction-r1.md`, SHA-256 `300eee99502beb815bf72a64b57d2c66a771c8d2cf795e5fa8148ac875c5e5d8` | Reviewed synthetic qualification reference and measured empirical uncertainty envelope; not a proven true-error bound or an online production oracle mandate. |
| R103 final mesh qualification | extension `r103_extension`, canonical hash `331bb73c09f0b2ec00260886abb1ceec65b3a2996dcb02a17d144e252ef51ac9`; R103 document SHA-256 `4ab8c5c6ae1a7f499feaa2411c701d57c0b75b5aef4533e27991c187d019d431` | `REVIEWED_AUTHORITY` for six frozen synthetic fixtures and their approved qualification profile only. |

The registry contains no reviewed real-case production mesh admission or
selection authority. The repository search covered TASK170–TASK172 documents,
the TASK172 authority registry and production source for existing real-case
mesh-profile/generalization bindings. It found TASK171's structural mapping
contract and TASK172's model-level mesh schema, but no reviewed real-case
initial-mesh rule, production refinement profile, real-case convergence
threshold/sequence, general-case resource cap, or real-case reference policy.
The R103 extension itself binds six synthetic fixtures and does not bind a
real-case-generalization predicate.

## Three separate identities

### Physical topology

Physical topology is the native exchanger/case graph: configuration, shell
and tube pass identities, explicit flow paths, physical compartments, accepted
geometry intervals, native physical events, physical coordinates, and area/
length/event ownership. It comes from reviewed native TASK020–024 and TASK171
producers. Mesh generation cannot create or rewrite any of these identities.

The supported topology candidate is exactly:

```text
FIXED_TUBESHEET
E_SHELL
ONE_SHELL_PASS
ONE_DECLARED_STRAIGHT_THROUGH_TUBE_PASS
EXPLICIT_COUNTERCURRENT_HOT_AND_COLD_PATHS
NATIVE_TASK020_024_ACCEPTED_GEOMETRY
EXISTING_SINGLE_SEGMENTAL_BAFFLE_AND_BELL_COMPATIBILITY_GATES
```

U-tube, floating-head, additional or split passes, branching/reversing paths,
cocurrent, alternate shell/baffle families, two-phase/transient service, and
cases requiring unmodeled leakage, axial wall conduction, ambient loss, or
other excluded physics remain blocked/deferred. This scope statement does not
override any stricter native geometry or case-level authority gate.

### Numerical mesh

A numerical mesh is a deterministic partition of already admitted physical
supports. It has a mesh/profile/sequence identity, canonical boundary vector,
cell identities, refinement lineage, and a physical-to-cell mapping hash.
Numerical cells are not physical compartments. A physical baffle compartment
is not automatically one cell.

### Production admission

Admission is a separate predicate over a case-bound set of reviewed authority
records and a production mesh profile. A structurally valid mesh mapping alone
does not qualify its cell count or establish mesh adequacy. Mesh admission is
not case-level production admission and does not authorize TASK173/TASK174.

## Required case-bound prerequisites

Before any real-case mesh selection, every required record below must resolve
to an exact version, canonical hash, lifecycle, allowed scope, case binding,
and applicability proof. Caller assertions, names without payload identities,
and missing records do not satisfy a prerequisite.

```text
CASE_ID
CONFIGURATION_ID
GEOMETRY_ID
TOPOLOGY_AUTHORITY_ID
FLOW_PATH_MAPPING_ID
PHYSICAL_COMPARTMENT_MAP_ID
AREA_OWNERSHIP_MAP_ID
LENGTH_OWNERSHIP_MAP_ID
HOT_STREAM_PATH_ID
COLD_STREAM_PATH_ID
PROPERTY_PROFILE_AUTHORITY_ID
MATERIAL_AUTHORITY_ID
WALL_AUTHORITY_ID
TUBE_HTC_AUTHORITY_ID
SHELL_HTC_AUTHORITY_ID
WALL_CORRECTION_AUTHORITY_ID
NUMERICAL_PROFILE_AUTHORITY_ID
MESH_PROFILE_AUTHORITY_ID
```

Every authority reference must additionally bind its source/revision/evidence,
units where applicable, domain, lifecycle, canonical payload hash, case and
geometry applicability, and producer/consumer identity. Material, property,
correlation, wall-correction, and numerical authorities remain their own
TASK172 case-admission gates; a mesh candidate cannot substitute for them.

## Physical-topology to cell mapping

Each candidate cell record binds at least:

```text
CELL_ID, MESH_ID, REFINEMENT_LEVEL, PHYSICAL_SUPPORT_ID
PHYSICAL_INTERVAL_START, PHYSICAL_INTERVAL_END
FLUID_PATH_INTERVAL_START, FLUID_PATH_INTERVAL_END
PHYSICAL_COMPARTMENT_ID, HOT_FLOW_PATH_ID, COLD_FLOW_PATH_ID
TUBE_AREA_I_M2, TUBE_AREA_O_M2, CELL_LENGTH_M
LOCAL_GEOMETRY_BINDING_ID, PHYSICAL_EVENT_OWNERSHIP
```

The mapping contract is:

1. Native physical intervals and events are supplied by their reviewed producer.
   Under TASK171 R2, interval boundaries include native axial start, every
   native baffle-plane center, and axial end. A mesh cannot repair a missing
   native boundary or invent an extra physical cut.
2. Cells completely and deterministically partition each admitted physical
   interval on their explicitly identified paths. Gaps, unauthorized overlap,
   orphan cells, cross-event cells, or missing support fail closed.
3. Cell areas and lengths are allocated from the bound geometry/area producers;
   sums preserve the parent interval and native totals under the admitted exact
   representation. No second area formula, inferred flow split, or tolerance
   is introduced here.
4. Countercurrent pairing follows explicit physical path identity/direction,
   not equipment side, array index, or serialized record order.
5. Refinement changes only numerical-cell identities. It cannot create,
   duplicate, move, split, remove, or reassign a hardware or physical event,
   compartment, flow path, manufacturable dimension, or native support.
6. Any nonmatching tube/shell partitions require an explicitly admitted common
   physical-support intersection map; interpolation or positional pairing is
   not inferred.

`CELL_MAPPING_CANONICAL_HASH` is the canonical hash of the complete ordered
mapping payload using the existing `hexagent.canonical_json` contract. The
payload ordering is canonical-key ordering, not physical direction; direction
is carried in explicit path identities and coordinates. Replaying identical
bound authorities and input geometry must reproduce identical mapping bytes
and hash.

## Mesh identity schema

`REAL_CASE_MESH_PROFILE_ID` binds schema version, allowed topology profile,
initial-mesh/refinement/convergence/reference/wall/resource policies, authority
hash set, scope, lifecycle, and review receipt. Those policy slots remain
unbound in this candidate.

`REAL_CASE_MESH_INSTANCE_ID` binds `CASE_ID`, `CONFIGURATION_ID`, `GEOMETRY_ID`,
topology and path identities, mesh-profile ID/hash, sequence ID, cell count,
canonical cell-boundary vector, physical mapping hash, parent mesh ID/hash
(when refined), and the exact authority hash set. It is deterministic and
contains no random/adaptive geometry mutation. Parent/child identity alone does
not authorize a refinement operation.

## R103 transfer matrix and disposition

The complete row-by-row disposition is in the linked machine-readable transfer
matrix. Its operative conclusions are:

| R103 element | Candidate real-case disposition |
|---|---|
| Primary `[1,2,4,8,16,32,64,128]` and secondary `[3,6,12,24,48,96]` | Synthetic validation sequences only; no absolute cell count is a production default or template. |
| Three-axis threshold grid `[1e-2,1e-3,1e-4,1e-5]`, selected tuple, componentwise-loosest rule | Synthetic sensitivity/selection result only; real-case threshold transfer is unbound. |
| Two consecutive passing pairs and one later headroom level | R103-specific quantitative rule only; exact production evidence count/headroom is unbound. |
| Resource caps `[32,64,128,256]`, synthetic selected cap 128 | Synthetic feasibility evidence only; no production maximum-cell cap is bound. TASK171's 4096 raw-record safeguard is not a numerical cell count. |
| `C_round=1.0` | Retained only within the reviewed mesh-cell-scale numerical acceptance scope exercised by R103; real-case mesh acceptance transfer is unbound. |
| R102 SciPy GL1024 `Q_ref` and `U_Q` | Frozen synthetic qualification reference. No online real-case reference oracle is required or selected by R102; production reference policy remains unbound. `U_Q` remains a measured empirical envelope, not a formal bound. |
| Wall extrema and numeric wall criteria | `T_wall_inner`/`T_wall_outer` and support identity can be represented as observables; synthetic extrema/tolerances are not real-case expected values or production stopping limits. |
| Deterministic replay | Canonical identity/mapping determinism transfers as a project contract; R103's bitwise/numeric replay observations are limited to its fixtures/runtimes. |
| Failure taxonomy | Existing fail-closed model vocabulary transfers as contract shape. It does not transfer R103 resource limits or imply that an implementation exists. |

No R103 threshold, sequence, headroom, or cap is silently used to fill an
unbound production slot. `R103 → real-case` statuses, evidence, limitations,
and review requirements are fully enumerated in the matrix.

## Initial mesh, refinement, convergence, reference, and resource policy

```ini
INITIAL_REAL_CASE_MESH_RULE_BOUND=false
INITIAL_REAL_CASE_MESH_RULE=UNBOUND
REAL_CASE_REFINEMENT_RULE_BOUND=false
REAL_CASE_REFINEMENT_SPLIT_OPERATOR=UNBOUND
REAL_CASE_CONVERGENCE_RULE_BOUND=false
REAL_CASE_THRESHOLD_TRANSFER_BOUND=false
REAL_CASE_HEADROOM_RULE_BOUND=false
PRODUCTION_REFERENCE_ORACLE_REQUIRED=UNBOUND
REAL_CASE_REFERENCE_POLICY_BOUND=false
REAL_CASE_RESOURCE_POLICY_BOUND=false
REAL_CASE_MAX_CELL_COUNT=UNBOUND
NORMALIZED_REAL_CASE_MESH_DESCRIPTOR_BOUND=false
```

TASK171 binds physical-event boundaries and permits explicit subdivision
strictly inside the same native-bounded intervals. It does not select a
production starting subdivision, midpoint/equal split operator, refinement
ratio, cells-per-compartment rule, normalized maximum support width, or
stopping threshold. TASK172's mesh model contract similarly binds schema
shape, not those quantitative values. No developer-chosen default is admitted.

R103's SciPy GL1024 oracle is a continuous-reference qualification producer,
not an online production solve requirement. This candidate does not decide
that online reference comparison is either required or unnecessary for every
real case; the production reference policy must be separately authority-bound.
If any future comparison consumes R102 `U_Q`, it must preserve its measured
empirical uncertainty-envelope classification and reviewed propagation rule;
it must not be called a formal true-error bound.

The production resource policy remains unbound. The TASK171 limit of 4096 raw
records is an admission safety guard, not an approved maximum mesh size. No
R103 cap is promoted.

## Wall observables and acceptance

The candidate observable schema records inner/outer wall temperature by exact
physical support, support location, mapping identity, and any admitted
minimum/maximum extrema. It distinguishes these states from bulk-fluid states
and from array positions. No R103 synthetic wall value is an expected value
for an arbitrary real exchanger. A real-case wall comparison producer,
metric, numerical precision floor, acceptance tolerance, and stopping role
are not bound here; therefore `REAL_CASE_WALL_ACCEPTANCE_RULE_BOUND=false`.

## Typed fail-closed outcomes

The contract adds no runtime enum. It reuses existing TASK171/TASK172
vocabulary and maps admission failures as follows:

| Admission condition | Existing status/code mapping |
|---|---|
| Missing topology/profile/provenance authority | `TOPOLOGY_AUTHORITY_INCOMPLETE` / `PROVENANCE_INVALID` |
| Unsupported topology or topology identity mismatch | `UNSUPPORTED_TOPOLOGY` / `UPSTREAM_IDENTITY_MISMATCH` |
| Invalid cell or physical mapping | `INVALID_MESH_MAPPING` / `INVALID_PHYSICAL_MAPPING` |
| Duplicate physical event | `DUPLICATE_PHYSICAL_EVENT` |
| Invalid area allocation | `INVALID_AREA_OWNERSHIP` |
| Length/support coverage failure | `INVALID_PHYSICAL_MAPPING` |
| Refinement not authority-bound | `TOPOLOGY_AUTHORITY_INCOMPLETE` with the missing refinement authority as field |
| Resource exhausted | `MESH_RESOURCE_EXHAUSTED`; never a convergence success |
| Mesh criteria not satisfied | `MESH_NOT_CONVERGED` |
| Missing comparison observable/reference authority | `MISSING_OBSERVABLE_AUTHORITY` |
| Numerical precision floor unresolved | `PRECISION_FLOOR_UNRESOLVED` |

A blocked or invalid mapping has no authoritative partial rating. The last
mesh may be retained only as diagnostic data under the existing TASK172
contract. `MESH_CONVERGED` would mean only mesh criterion acceptance in its
bound profile; it does not prove physical validation, correlation authority,
case admission, or TASK173 rating success.

## Explicit production admission predicate

```text
REAL_CASE_MESH_ADMISSIBLE =
    topology_authority_valid
    AND geometry_mapping_valid
    AND mesh_profile_authority_valid
    AND case_scope_supported
    AND every_required_case_binding_present_and_applicable
    AND initial_mesh_rule_bound
    AND refinement_rule_bound
    AND convergence_rule_bound
    AND resource_policy_bound
    AND deterministic_mapping_valid
```

For this candidate, the first four structural predicates are requirements, not
evidence of an admitted real instance. The initial mesh, production refinement,
quantitative convergence/headroom, and resource-policy operands remain false.
Thus `REAL_CASE_MESH_ADMISSIBLE=false` and
`PRODUCTION_MESH_ADMISSION_ENABLED=false`.

Finally:

```ini
MESH_ADMISSION_SUCCESS_EQUALS_CASE_PRODUCTION_ADMISSION_SUCCESS=false
CASE_PRODUCTION_ADMISSION_REQUIRES_ALL_TASK172_CASE_AUTHORITIES=true
TASK173_OR_TASK174_AUTHORIZED=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
PRODUCTION_RATING_PERFORMED=false
MESH_POLICY_RETUNED=false
PRECISION_POLICY_RETUNED=false
REFERENCE_ORACLE_REDEFINED=false
R103_REWRITTEN=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

Next gate: `AUTHORIZE_TASK172_REAL_CASE_MESH_ADMISSION_CONTRACT_INDEPENDENT_REVIEW_ONLY`.
