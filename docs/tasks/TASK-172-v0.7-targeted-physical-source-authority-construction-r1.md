# TASK172 R1 — targeted physical source-authority construction

## 1. Receipt and scope

This is a documentation-only authority-construction receipt for Draft PR277.
It follows the accepted R5 semantic review and executes the required order:

1. material identity;
2. solid-metal thermal-conductivity authority;
3. native TASK026-compatible tube wall correction;
4. native TASK166-compatible shell wall correction;
5. cross-binding review.

The sequence stops at the first missing prerequisite. No material grade,
conductivity value, active correction equation, numerical rule or runtime
capability is invented.

~~~ini
TASK_ID=TASK172_V0_7_TARGETED_PHYSICAL_SOURCE_AUTHORITY_CONSTRUCTION_R1
PR=277
PREVIOUS_HEAD_SHA=5a5c8954a0ddd509f489b6bc6d2c35e86f2bb4f0
MODE=CONTROLLED_ENGINEERING_SOURCE_AUTHORITY_CONSTRUCTION_ONLY
SCOPE=MATERIAL_IDENTITY;MATERIAL_K;TUBE_ACTIVE_WALL_CORRECTION;SHELL_ACTIVE_WALL_CORRECTION;CROSS_BINDING
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SOLVER_IMPLEMENTATION=false
NUMERICAL_TOLERANCE_FREEZE=false
MESH_CONVERGENCE_QUALIFICATION=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
RESULT=BLOCKED
BLOCK_REASON=MATERIAL_IDENTITY_INPUT_CONTRACT_MISSING
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_IDENTITY_AUTHORITY_INPUT_CONTRACT_R1_ONLY
~~~

The evidence payload is
`evidence/TASK-172-targeted-physical-source-authority-construction-r1.json`.
The registry adds an append-only `r6_extension`; R1–R5 records and hashes are
not rewritten.

## 2. Evidence boundary and audit method

The audit covered the active shell-and-tube configuration, geometry, tube-side
thermal, wall-resistance and relevant source/provenance contracts. The
authoritative question was whether a physical tube-wall material identity is
already bound to the TASK020–023/TASK026/TASK037 chain.

The following distinction is enforced throughout:

* a typed carrier is not automatically a reviewed authority;
* a fluid property snapshot is not solid-metal material authority;
* a fixture/demo value is not a product-bound TASK172 material profile;
* a forbidden field name is not a request/result field;
* a bibliography entry without the complete equation and domain is not a
  transferable wall-correction authority.

No new external source bytes were acquired or promoted. This is intentional:
the material identity prerequisite is absent, so phases B–E may not select a
value or claim a transferable correction.

## 3. Historical `tube_thermal_conductivity` anomaly reconciliation

The historical report of a non-frozen TASK026 draft field was checked against
the current repository and reachable Git history. The only current-main
occurrence is the literal string in
`src/hexagent/exchangers/shell_tube/tube_side_thermal/stage_pipeline.py` in
`TASK026_T025_FORBIDDEN_FIELDS`. It was introduced by commit
`37f39d902143e4938f83cd7edb48231d5fabf937` as part of the TASK026 R8
implementation. It is explicitly a field that TASK026 must reject from the
TASK025 upstream payload; it is not a TASK026 material input or result field.

The current TASK026 upstream read set contains only the seven hydraulic
geometry fields and excludes material data. No TASK-026 design document or
frozen material-field proposal containing this field exists in reachable
repository history. The user-reported draft is therefore not an immutable
repository authority artifact and cannot be used without an independently
identifiable source, revision and provenance record.

| Required fact | Evidence | Determination |
| --- | --- | --- |
| `tube_thermal_conductivity` occurrence | `stage_pipeline.py`, `TASK026_T025_FORBIDDEN_FIELDS` | Found only as a forbidden upstream token, not a data carrier |
| Introduction point | `37f39d902143e4938f83cd7edb48231d5fabf937`, TASK026 R8 | Current-main occurrence is implementation-boundary metadata |
| TASK026 upstream use | `TASK026_T025_UPSTREAM_READ_SET` | Not read, not materialized, not passed downstream |
| Frozen TASK026 material authority | Reachable TASK026 history and docs | Not found |
| Source/provenance for a material value | TASK026 records and current shell-tube chain | Not found |
| Reuse for TASK172 | Identity, component, source, domain and approval are absent | Rejected |

The TASK037 material/conductivity dataclasses are real typed carriers and its
cylindrical wall equation is an inherited equation authority. The current
release-demo material (`T039-MAT-001`, `FIXTURE-GRADE`) is scoped fixture
authority, not a TASK172 product material. TASK013/TASK017 material records
belong to the separate double-pipe/material-cost path and are explicitly not
imported into TASK021/022 shell-and-tube geometry.

~~~ini
LEGACY_TUBE_THERMAL_CONDUCTIVITY_FIELD_FOUND=true
LEGACY_FIELD_CURRENT_MAIN_PRESENT=true
LEGACY_FIELD_CURRENT_MAIN_OCCURRENCE_TYPE=TASK026_FORBIDDEN_FIELDS_TOKEN_NOT_REQUEST_OR_RESULT_FIELD
LEGACY_FIELD_FROZEN_AUTHORITY=false
LEGACY_FIELD_SOURCE_PROVENANCE_COMPLETE=false
LEGACY_FIELD_REUSABLE_FOR_TASK172=false
LEGACY_FIELD_DISPOSITION=RETAIN_FORBIDDEN_FIELD_TOKEN_AS_TASK026_T025_BOUNDARY_METADATA;DO_NOT_TREAT_AS_MATERIAL_AUTHORITY;NO_REUSE
~~~

## 4. Phase A — material identity input contract

The active TASK020 request carries construction/configuration identity but no
physical material identity. TASK021’s approved tube geometry snapshot carries
dimensions and source binding but deliberately carries no material grade.
TASK022/023 likewise do not establish a solid tube material. Therefore the
first lawful construction is a project-defined input contract, not a selected
material.

### 4.1 Proposed contract

~~~ini
MATERIAL_IDENTITY_AUTHORITY_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
MATERIAL_IDENTITY_AUTHORITY_VERSION=r1
MATERIAL_IDENTITY_STATUS=PROPOSED_AUTHORITY
MATERIAL_IDENTITY_COMPONENT_ROLE=TUBE_WALL_METAL
MATERIAL_IDENTITY_BOUND=false
MATERIAL_IDENTITY_INPUT_CONTRACT_MISSING=true
MATERIAL_PROFILE_ID=NONE
MATERIAL_DEFAULT_FORBIDDEN=true
MATERIAL_SELECTION_BY_CONDUCTIVITY_FORBIDDEN=true
MATERIAL_SELECTION_BY_DIAMETER_FORBIDDEN=true
MATERIAL_SELECTION_BY_COMMON_PRACTICE_FORBIDDEN=true
MATERIAL_SELECTION_FROM_TASK034_FORBIDDEN=true
~~~

The `MATERIAL_IDENTITY_INPUT_CONTRACT_MISSING=true` flag means that the
product-bound input is missing; the contract proposal itself is present in
this receipt. A future request must bind, at minimum:

| Required field | Contract rule |
| --- | --- |
| `component_role` | Exact physical role; initial role is `TUBE_WALL_METAL` |
| `material_id` | Immutable project/catalog identity, not a free-form alias |
| `material_grade_or_specification` | Grade/specification and product form |
| `material_standard` | Standard or controlled internal specification |
| `source_id`, `source_version`, `source_location` | Exact source lineage |
| `source_class` and rights/permission | Legal and governance status |
| `evidence_refs` | Reviewable material and property evidence |
| `approval_status` | Independent review boundary; no implicit approval |
| `canonical_hash` | Identity of the complete material record |
| upstream bindings | Exact TASK020/geometry/request identity and component mapping |

The contract must reject absent, ambiguous, substituted, or silently defaulted
material identity. It must also prevent a conductivity record for one grade,
component or product form from binding to another.

### 4.2 No material is selected

No 304, 316/316L, copper, carbon steel, TEMA typical material, vendor default,
TASK037 fixture grade, TASK013/TASK017 material or value inferred from a
conductivity number is selected. There is no lawful `MATERIAL_PROFILE_ID` at
this head.

## 5. Phase B — solid-metal conductivity authority

Phase B cannot begin because Phase A has no bound material identity. The
inherited TASK037 physical equation remains unchanged:

~~~text
R_w,j = d_i * ln(d_o / d_i) / (2 * k_wall * A_i,j)
~~~

This does not authorize a value of `k_wall`. A future material-specific record
must provide the grade/specification, conductivity source and revision, exact
temperature basis, units, valid temperature interval, constant-k treatment
rule if applicable, component mapping, evidence and approval. The interval
must cover the reviewed TASK172 wall-temperature hull; a point value alone is
not a constant-k domain authority.

~~~ini
MATERIAL_K_SOURCE_AUTHORITY_STATUS=BLOCKED
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_K_VALUE_BOUND=false
MATERIAL_K_UNIT_BOUND=false
MATERIAL_K_EVALUATION_TEMPERATURE_BOUND=false
MATERIAL_K_COMPONENT_MAPPING_COMPLETE=false
MATERIAL_K_AUTHORITY_DISPOSITION=DISPOSITION_BLOCKED_MATERIAL_IDENTITY_PREREQUISITE_MISSING
MATERIAL_K_AUTHORITY_ID=NONE
~~~

No material source was selected and no constant-k claim was made.

## 6. Phase C — native TASK026 tube correction

The tube-side base remains the native TASK026 selector and its exact source
and domain. An active correction would need an independently reviewable
equation compatible with that base, including coefficient/exponent, bulk and
wall-state definitions, property ratio, heating/cooling branch, Re/Pr and
ratio domains, geometry/roughness and developing-flow assumptions, and an
explicit combination rule.

Because the required material identity and the exact wall-state/material
binding are absent, the construction sequence does not select or transfer a
tube correction. The R5 result remains authoritative: Sieder–Tate full text
and transfer domain are unavailable, and a remembered
`(mu/mu_wall)^0.14` factor is forbidden.

~~~ini
TUBE_WALL_CORRECTION_ID=NONE
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_SOURCE_BOUND=false
TUBE_WALL_CORRECTION_BASE_COMPATIBILITY_BOUND=false
TUBE_WALL_CORRECTION_APPLICABILITY_BOUND=false
TUBE_WALL_CORRECTION_MATERIAL_PROFILE_BOUND=false
TUBE_WALL_CORRECTION_SURFACE_BASIS_BOUND=false
TUBE_WALL_CORRECTION_DISPOSITION=DISPOSITION_BLOCKED_UPSTREAM_MATERIAL_IDENTITY_AND_WALL_STATE_PREREQUISITE_MISSING;NO_TRANSFER_ATTEMPTED
SIEDER_TATE_TRANSFER_AUTHORITY=UNAVAILABLE
~~~

This is not a statement that no suitable primary source can ever exist. It is
a fail-closed statement that no source may be transferred at this head.

## 7. Phase D — native TASK166 shell correction

The shell-side base remains TASK166 Bell–Delaware. A shell correction would
need an exact Bell-compatible primary authority defining the wall/bulk state,
surface basis, equation, domain and combination rule for Bell heat transfer.
TASK034’s Bayram–Sevilgen wall-property term remains negative lineage
evidence only: it is a shell pressure-drop `phi_s` quantity with a different
method, output and identity. It cannot become a Bell HTC correction.

No tube-side correction is reused on the shell side. No bulk temperature is
silently substituted for a wall-fluid temperature, and no neutral factor is
introduced.

~~~ini
SHELL_WALL_CORRECTION_ID=NONE
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_SOURCE_BOUND=false
SHELL_WALL_CORRECTION_BASE_COMPATIBILITY_BOUND=false
SHELL_WALL_CORRECTION_APPLICABILITY_BOUND=false
SHELL_WALL_CORRECTION_MATERIAL_PROFILE_BOUND=false
SHELL_WALL_CORRECTION_SURFACE_BASIS_BOUND=false
SHELL_WALL_CORRECTION_DISPOSITION=DISPOSITION_BLOCKED_UPSTREAM_MATERIAL_IDENTITY_AND_WALL_STATE_PREREQUISITE_MISSING;NO_TRANSFER_ATTEMPTED
TASK034_WALL_AUTHORITY_REUSE=NO
~~~

## 8. Phase E — cross-binding review

Cross-binding is not ready because there is no actual material profile or
active correction to bind. The future binding must reject any mismatch in:

* material identity, component role or product form;
* source/revision, rights or approval status;
* temperature/pressure domain and phase;
* wall surface/state location;
* tube/shell geometry and area basis;
* base correlation/method identity;
* units, reference state and property snapshot;
* upstream result/request identity and canonical hash.

~~~ini
WALL_TEMPERATURE_STATE_REQUIRED=true
WALL_TEMPERATURE_STATE_AUTHORITY_BOUND=false
PHYSICAL_AUTHORITY_CROSS_BINDING=NOT_READY
PHYSICAL_AUTHORITY_PORTION_CLOSED=false
~~~

The requirement for a wall-temperature state is recorded, not implemented.
It remains downstream of the unresolved wall-state and active-correction
authority boundary.

## 9. Unchanged numerical and implementation boundary

This receipt does not research or alter the three numerical blockers:

~~~ini
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
MESH_CONVERGENCE_QUALIFICATION=OPEN
NUMERICAL_PROFILE_STATUS=PARTIALLY_CLOSED
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
NUMERICAL_EXECUTABLE_QUALIFICATION_DEFERRED_UNTIL_PROPERTY_AND_ACTIVE_CORRELATION_AUTHORITY_FIXED=true
~~~

No property runtime, material resolver, wall solver, correction factor,
iteration loop, tolerance, mesh rule, equation or dependency was added.

## 10. Final entry status and next gate

The R5 reviewed water and clean-wall semantic overlays remain unchanged. The
targeted physical construction is blocked at the absent material input. The
six R5 blockers remain unchanged; the material identity absence is the exact
sub-blocker of the material/constant-k item rather than an invented seventh
engineering authority.

~~~ini
WATER_PROFILE_R2_STATUS=REVIEWED_AUTHORITY
WATER_PROFILE_INDEPENDENT_REVIEW=CLOSED_FOR_TASK172_ENTRY
CLEAN_WALL_NETWORK_R2_STATUS=REVIEWED_AUTHORITY
LOCAL_CYLINDRICAL_MAPPING_R2_STATUS=REVIEWED_AUTHORITY
WALL_SURFACE_NETWORK_INDEPENDENT_REVIEW=CLOSED_FOR_TASK172_ENTRY
MATERIAL_IDENTITY_INPUT_CONTRACT_CREATED=true
MATERIAL_IDENTITY_BOUND=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
REMAINING_TASK172_ENTRY_BLOCKERS=MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN;TUBE-WALL-CORRECTION-AUTHORITY;SHELL-WALL-CORRECTION-AUTHORITY;LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION;NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW;MESH-CONVERGENCE-QUALIFICATION
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_IDENTITY_AUTHORITY_INPUT_CONTRACT_R1_ONLY
SUPPORTED_FLUID_PROFILE_APPROVED=false
FOULED_WALL_PROFILE_APPROVED=false
VARIABLE_K_WALL_APPROVED=false
TUBE_WALL_CORRECTION_APPROVED=false
SHELL_WALL_CORRECTION_APPROVED=false
~~~

The next gate is specifically to provide or review an actual TASK172-bound
material identity input. It does not authorize selecting a grade, constructing
k authority, implementing a resolver or starting TASK172 production work.

## 11. Review checklist

An independent reviewer should verify:

* the current-main `tube_thermal_conductivity` token is not misclassified as
  a material input;
* no historical draft without immutable source identity is promoted;
* TASK020–023 material absence is correctly reported;
* TASK037 equation inheritance is separated from material selection;
* no TASK013/TASK017 or fixture material is imported across domain boundaries;
* no conductivity value, grade, constant-k interval or correction equation is
  invented;
* TASK034 pressure-drop wall authority is not transferred to TASK166 HTC;
* tube and shell correction authorities remain separate;
* R5 statuses and six blocker identities remain unchanged;
* no production code, dependency, solver, numerical rule, Ready or Merge
  action is implied.
