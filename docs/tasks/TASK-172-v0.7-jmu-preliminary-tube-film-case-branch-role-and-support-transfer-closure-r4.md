# TASK172 v0.7 J_mu preliminary tube-film case, branch-role, and support-transfer closure R4

## Receipt identity

```ini
TASK_ID=TASK172_V0_7_JMU_PRELIMINARY_TUBE_FILM_CASE_BRANCH_ROLE_AND_SUPPORT_TRANSFER_CLOSURE_R4
TASK_SCOPE=TARGETED_TASK026_TO_TASK172_PRELIMINARY_TUBE_FILM_TRANSFER_CLOSURE_ONLY
PREVIOUS_HEAD_SHA=5539fe2d74b1a14cd4df6ad46a1b4ae5a097434a
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
```

This record is documentation/evidence only. It does not select a case, create a
film instance, alter TASK026 or TASK166, or authorize TASK172 implementation.

## Decision summary

The R4 audit resolves one semantic boundary and keeps the remaining transfer
edges fail-closed:

* `h_i` is a scalar correlation result with units of W/m2/K. Its transport from
  TASK026 does not itself require substituting a wall area for the native flow
  area used to calculate velocity, Reynolds number, and Prandtl number.
* Construction of a local radial wall branch does require an authoritative
  local inside heat-transfer area. TASK025's total parallel flow area and total
  surface area are not a local physical-support map.
* TASK026 currently has no TASK172 case identity, located state identity, or
  physical-support binding. A caller-supplied property snapshot and a native
  branch result therefore cannot be admitted as a TASK171-located preliminary
  film.
* The C3 preliminary-film wall-correction role is still unresolved. The
  accepted C3 correction cannot be silently omitted or silently applied merely
  because the preliminary role has not been selected.
* CWT and CHF remain separate accepted native branch authorities, but their
  TASK172 transfer is conditional on a case-bound thermal boundary, located
  property snapshot, and physical support. Transition remains fail-closed.

Accordingly, the complete TASK026-to-TASK172 preliminary-film transfer
contract is not yet bound. The correct result is `BLOCKED`, with no production
authority candidate and no implementation work.

## Scope and inherited authorities

This R4 record inherits, without rewriting, the following reviewed material and
wall-state records:

* `V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1`
* `V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1`
* `V07-T172-TUBE-WALL-CORRECTION-R1`
* `V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2`
* `V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2`
* `V07-T172-WALL-TEMPERATURE-STATE-R1`
* `V07-T172-CLEAN-RADIAL-WALL-STATE-R1`

The shell preliminary-film branch remains explicitly paused and is not
reopened here:

```ini
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
SHELL_PRELIMINARY_FILM_SOURCE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_LEAD
```

This record also does not revisit the Q source, source mean-bulk state,
material/k_wall, J_mu implementation, wall solve, fixed-point closure, or any
numerical gate.

## Native TASK026 evidence

The native inputs were audited from the accepted repository blobs. Their
identities are retained here so that a future transfer record can bind exact
inputs rather than a similarly named object.

| Native object | Repository identity | Relevant meaning |
| --- | --- | --- |
| `nusselt_selector.py` | blob `750d92e2da2284202190afe93cf47589eb3a6bb2`; SHA-256 `d2059a83624308b5cdb808e1e314c1b7514e31eaca31899570cde343d3ea2109` | Deterministic branch selection from typed thermal boundary and native regime inputs |
| `single_phase.py` | blob `90a39ab66dd3b2600f228cf513bf398c9c0cb254`; SHA-256 `c9cc6444a79975edd3b5b37249a2ee0909a5f07987b3783d70d99e5342f3ff08` | Native single-phase calculation of velocity, Re, Pr, Nu, and scalar `h_i` |
| `stage_pipeline.py` | blob `51034d2efdfdbeb5b5149467da323de95d8d474f`; SHA-256 `2ec94d18f061c88ca05f7d64f7bac1ea604c6f2c3aa62e994597fd3bd68852c2` | TASK026 stage/result identity and provenance assembly |
| `request.py` | blob `492d269fd82222c6c04b442d9ef90fa600d70730`; SHA-256 `d438504563e4c48adb6cdaa00b5552b121909d344781e4a9a99c049fbcf84ab4` | Typed request, property snapshot, thermal boundary, and deferred capability inputs |
| TASK-007 correlation note | blob `35b51c5007cbd48556d93d14e0106431c60a0cb9`; SHA-256 `c650cc275d05972afd0f86eb80d1c5eaf303a91cfa305b771314f731bd4130cb` | Native correlation scope and limitation record |

`Task025ValidResult` supplies native hydraulic/geometry quantities including
`single_tube_flow_area_m2`, `total_parallel_flow_area_m2`,
`hydraulic_diameter_m`, and
`internal_heat_transfer_surface_area_m2`. `Task026 PropertySnapshot` supplies
bulk T/P, rho, mu, k, cp, phase, property-source/version, and a snapshot hash.
The audited TASK026 request/result does not add a TASK171 stream/side/state
location, physical interval, wall-interface, or numerical-cell identity.

## TASK172 case identity and role audit

The existing TASK171 `Definition`, `State`, `Cell`, and `Wall` identities are
the authoritative topology/support vocabulary. They are not, by themselves, a
case-selected TASK172 preliminary-film authority. No existing TASK172 case
identity was found that binds all of the following together:

```text
TASK171 topology identity
TASK026 request/result identity
native property snapshot identity and hash
thermal boundary selection
stream and equipment-side assignment
physical interval / wall-interface support
property state location
preliminary-film role
```

Consequently this R4 record does not fabricate a case ID or turn a caller
assertion into an authority. The required case contract remains unbound:

```ini
TASK172_PRELIMINARY_FILM_CASE_CONTRACT_BOUND=false
TASK172_PRELIMINARY_FILM_CASE_IDENTITY=NONE
TASK172_PRELIMINARY_FILM_CASE_HASH_BOUND=false
TASK172_PRELIMINARY_FILM_CASE_IDENTITY_REASON=NO_EXISTING_TASK172_CASE_AUTHORITY_BINDS_TASK026_RESULT_THERMAL_BOUNDARY_LOCATED_STATE_AND_TASK171_SUPPORT
```

The native branch selector is deterministic for its own typed inputs. That is
not the same as selecting the TASK172 case role:

```ini
TASK026_NATIVE_BRANCH_SELECTED_BY_NATIVE_INPUTS=true
TASK172_PRELIMINARY_BRANCH_ROLE_RULE_BOUND=false
TASK172_PRELIMINARY_THERMAL_BOUNDARY_CASE_BINDING=false
```

The future case authority must bind the exact native request/result hashes and
the selected thermal-boundary identity. It must not infer branch role from a
bare correlation name, a numerical Reynolds interval, or vocabulary membership.

## Conditional branch-role table

The following table records the only permissible conditional interpretation of
the native branches. It is a transfer contract requirement, not a production
admission or a new branch authority.

| Native branch | Native scope | TASK172 role condition | R4 transfer state |
| --- | --- | --- | --- |
| CWT | `V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1`, `Nu_D=3.66`, constant-property, no active correction | Exact case-bound CWT thermal boundary, exact located property snapshot, and exact physical support | `CWT_TASK172_PRELIMINARY_TRANSFER_BOUND=false` |
| CHF | `V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1`, `Nu_D=4.36`, constant-property, no active correction | Exact case-bound CHF thermal boundary, exact located property snapshot, and exact physical support | `CHF_TASK172_PRELIMINARY_TRANSFER_BOUND=false` |
| Transition | Native selector has no applicable correlation in `2300 <= Re < 3000` | No fallback, interpolation, or branch substitution | `TRANSITION_PRELIMINARY_FILM_AVAILABLE=false` |
| C3 | Native turbulent C3/Gnielinski branch and separately reviewed active C3 wall correction | A separate preliminary-role policy must say whether the accepted correction is required, prohibited, or otherwise source-bound | `C3_TASK172_PRELIMINARY_TRANSFER_BOUND=false` |

The C3 policy remains:

```ini
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY=UNRESOLVED_PRELIMINARY_ROLE_MUST_NOT_SILENTLY_SELECT_UNCORRECTED_C3_OR_APPLY_ACCEPTED_C3_CORRECTION
PRELIMINARY_TUBE_FILM_ACTIVE_WALL_CORRECTION_REQUIRED=undetermined
TUBE_FILM_DEPENDS_ON_WALL_STATE=undetermined
TUBE_FILM_CREATES_WALL_STATE_LOOP=undetermined
```

No CWT/CHF/C3 result is copied across supports, and no transition result is
manufactured.

## Located tube-bulk state transfer

TASK026's property snapshot is a value-and-source record, not a located
TASK171 state. It lacks, in the audited request/result shape:

* `stream_id` and independent equipment-side identity;
* `state_id` and state-location enum;
* `physical_segment_id`, `physical_interval_id`, or `wall_interface_id`;
* numerical-cell identity and physical/fluid-path support;
* an exact case/segment scope saying where the snapshot applies.

The snapshot hash proves the snapshot bytes; it does not prove the physical
support or state location. Therefore:

```ini
TASK026_PROPERTY_SNAPSHOT_SOURCE_STATE_ID_BOUND=false
TASK026_PROPERTY_SNAPSHOT_GRANULARITY_BOUND=false
TASK026_PROPERTY_SNAPSHOT_GRANULARITY=UNRESOLVED_UNSCOPED_CASE_OR_SEGMENT_SNAPSHOT
TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_BOUND=false
TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_REASON=PROPERTY_VALUES_AND_HASH_EXIST_BUT_TASK171_STREAM_SIDE_LOCATION_AND_PHYSICAL_SUPPORT_ARE_ABSENT
```

The future transfer must bind the native property snapshot to a TASK171
`State` at an explicitly declared location and support. It may not use an
arithmetic temperature/property average, same-array-index convention, or
caller assertion to create that mapping.

## Scalar `h_i` versus wall-area ownership

The native single-phase calculation uses `total_parallel_flow_area_m2` to
calculate velocity and then uses the native hydraulic diameter and property
snapshot to calculate a scalar `h_i`:

```text
u = m_dot / (rho * total_parallel_flow_area)
Re = rho * u * D_h / mu
Pr = cp * mu / k
Nu = native branch correlation(Re, Pr)
h_i = Nu * k / D_h
```

This separates two contracts that must not be conflated:

```ini
HI_SCALAR_TRANSFER_REQUIRES_AREA_MAPPING=false
WALL_RESISTANCE_CONSTRUCTION_REQUIRES_AREA_MAPPING=true
```

The first value means that a previously established scalar with units W/m2/K
does not require relabeling the native velocity-area basis as a wall area. It
does not mean the scalar is admitted without its state, branch, and source
identity bindings.

For a local clean radial wall branch, the film resistance is instead:

```text
R_i,j = 1 / (h_i,j * A_i,j)
```

where `A_i,j` is the authoritative local inside heat-transfer area on the
physical support of branch `j`. The TASK025 total surface area cannot be
silently divided by cell count, and the native flow area cannot be substituted
for it. No TASK026-to-TASK172 local area projection is currently bound:

```ini
TASK026_NATIVE_VELOCITY_AREA_IDENTITY_BOUND=true
TASK026_TO_TASK172_AREA_MAPPING_BOUND=false
TASK026_TO_TASK172_AREA_MAPPING_REASON=NATIVE_FLOW_AREA_IS_VELOCITY_BASIS_ONLY_AND_NO_LOCAL_PHYSICAL_WALL_AREA_PROJECTION_IS_BOUND
```

This is a downstream wall-resistance dependency, not a claim that scalar `h_i`
itself was calculated using the wrong area.

## Physical-support mapping and granularity

TASK171 separates immutable physical intervals from numerical cells. The
preliminary tube film required by the clean radial network must be bound to a
physical support that can own a local wall area. For this transfer contract,
the minimum required support granularity is the physical interval; a numerical
cell may refine within it but cannot supply a new hardware or event boundary:

```ini
PRELIMINARY_TUBE_FILM_REQUIRED_SUPPORT_GRANULARITY_BOUND=true
PRELIMINARY_TUBE_FILM_REQUIRED_SUPPORT_GRANULARITY=PHYSICAL_INTERVAL
PRELIMINARY_TUBE_FILM_REQUIRED_SUPPORT_GRANULARITY_MEANING=IMMUTABLE_TASK171_PHYSICAL_INTERVAL_OR_EXPLICIT_WALL_SUPPORT_NOT_NUMERICAL_CELL_DEFAULT
```

The current TASK026 result has no such binding. A future mapping must include
the exact `physical_segment_id`, interval/support coordinates, wall-interface
identity, native geometry identity, and the relevant request/result/property
hashes. It must also prove that the native result is valid for that support.

```ini
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_BOUND=false
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_REASON=TASK026_RESULT_HAS_NO_TASK171_PHYSICAL_INTERVAL_OR_WALL_INTERFACE_BINDING
TASK026_RESULT_REUSE_ACROSS_MULTIPLE_SUPPORTS_AUTHORIZED=false
TASK026_RESULT_REUSE_REASON=NO_SOURCE_BOUND_PROJECTION_OR_REUSE_RULE_AND_NO_DUPLICATION_OF_A_WHOLE_RESULT_ACROSS_LOCAL_SUPPORTS
```

Mesh refinement inside one physical interval may change numerical-cell
identity and resolution. It cannot promote a mesh cut to a physical interval,
cross a native event boundary, or create a mapping that the native result did
not provide.

## Transfer-contract disposition

The required identity is the conjunction of case, branch, state, area, and
support binding. It is not enough that the native selector can calculate a
number:

```ini
TASK172_PRELIMINARY_FILM_CASE_CONTRACT_BOUND=false
TASK172_PRELIMINARY_BRANCH_ROLE_RULE_BOUND=false
TASK026_TO_TASK172_PRELIMINARY_TRANSFER_CONTRACT_BOUND=false
TASK026_TO_TASK172_PRELIMINARY_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
REAL_PRELIMINARY_TUBE_FILM_INSTANCE_PRESENT=false
JMU_PRELIMINARY_TUBE_FILM_TRANSFER_CANDIDATE_CREATED=false
```

The smallest unresolved edges are:

1. define and independently review the TASK172 case-bound preliminary-film
   contract without creating a real case instance;
2. bind the exact CWT/CHF/C3 role policy, with transition fail-closed;
3. bind a located TASK026 property snapshot to a TASK171 tube bulk state;
4. bind the native scalar/result to the exact physical interval and local wall
   area required by the clean radial network.

Until these edges are closed, the accepted native TASK026 result remains a
native calculation result only. There is no permission to reuse it across
multiple TASK171 supports and no permission to feed it into a J_mu wall-state
calculation.

## Preserved downstream state

The R4 record does not alter the shell, Q, material, source mean-bulk, wall
producer, or numerical states:

```ini
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE=UNBOUND
SOURCE_TO_TASK032_BULK_MAPPING_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false

SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No TASK026, TASK166, TASK171, or production behavior is changed by this
record.

## Governance and validation intent

The allowed change set is limited to this review document, its machine-readable
evidence, and an append-only registry extension. In particular:

```ini
TASK026_CHANGED=false
TASK166_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The final validation receipt records JSON/schema, canonical/hash, registry,
append-only, link, allowlist, whitespace, lint, format, type, manifest, lock,
and repository regression checks. Exact-head CI is required after the final
documentation commit; it does not promote any authority lifecycle state.

## R4 receipt

```ini
TASK_ID=TASK172_V0_7_JMU_PRELIMINARY_TUBE_FILM_CASE_BRANCH_ROLE_AND_SUPPORT_TRANSFER_CLOSURE_R4
RESULT=BLOCKED
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=5539fe2d74b1a14cd4df6ad46a1b4ae5a097434a
FINAL_HEAD_SHA=<filled-after-commit>

TASK172_PRELIMINARY_FILM_CASE_CONTRACT_BOUND=false
TASK172_PRELIMINARY_FILM_CASE_IDENTITY=NONE
TASK172_PRELIMINARY_FILM_CASE_HASH_BOUND=false
TASK172_PRELIMINARY_BRANCH_ROLE_RULE_BOUND=false
CWT_TASK172_PRELIMINARY_TRANSFER_BOUND=false
CHF_TASK172_PRELIMINARY_TRANSFER_BOUND=false
TRANSITION_PRELIMINARY_FILM_AVAILABLE=false
C3_TASK172_PRELIMINARY_TRANSFER_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY=UNRESOLVED_PRELIMINARY_ROLE_MUST_NOT_SILENTLY_SELECT_UNCORRECTED_C3_OR_APPLY_ACCEPTED_C3_CORRECTION
PRELIMINARY_TUBE_FILM_ACTIVE_WALL_CORRECTION_REQUIRED=undetermined
TUBE_FILM_DEPENDS_ON_WALL_STATE=undetermined
TUBE_FILM_CREATES_WALL_STATE_LOOP=undetermined

TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_BOUND=false
TASK026_PROPERTY_SNAPSHOT_GRANULARITY_BOUND=false
HI_SCALAR_TRANSFER_REQUIRES_AREA_MAPPING=false
WALL_RESISTANCE_CONSTRUCTION_REQUIRES_AREA_MAPPING=true
TASK026_TO_TASK172_AREA_MAPPING_BOUND=false
PRELIMINARY_TUBE_FILM_REQUIRED_SUPPORT_GRANULARITY_BOUND=true
PRELIMINARY_TUBE_FILM_REQUIRED_SUPPORT_GRANULARITY=PHYSICAL_INTERVAL
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_BOUND=false
TASK026_RESULT_REUSE_ACROSS_MULTIPLE_SUPPORTS_AUTHORIZED=false

TASK026_TO_TASK172_PRELIMINARY_TRANSFER_CONTRACT_BOUND=false
TASK026_TO_TASK172_PRELIMINARY_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
REAL_PRELIMINARY_TUBE_FILM_INSTANCE_PRESENT=false
JMU_PRELIMINARY_TUBE_FILM_TRANSFER_CANDIDATE_CREATED=false

SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
PR_BODY_UPDATED=false
LOCAL_VALIDATION=<filled-after-validation>
INTERMEDIATE_GITHUB_CI_RUNS=0
EXACT_FINAL_HEAD_CI_RUN=<filled-after-CI>
EXACT_FINAL_HEAD_CI=<filled-after-CI>
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_JMU_PRELIMINARY_TUBE_FILM_CASE_AND_SUPPORT_TRANSFER_CONTRACT_CONSTRUCTION_R5_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
