# TASK172 — Jμ wall-producer material and `k_wall` transfer authority R1

## 1. Scope and receipt

This is a documentation/evidence-only audit of the material and solid-wall
thermal-conductivity authority required by the future clean radial
wall-temperature producer for the shell-side Jμ path. It does not select a
material, create a material profile, introduce a conductivity value or curve,
solve a wall temperature, implement Jμ, or modify TASK026/TASK166.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_WALL_PRODUCER_K_WALL_MATERIAL_TRANSFER_AUTHORITY_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=01e0647cf20289796a2539640fd64d04e14f77f3
MODE=JMU_WALL_PRODUCER_K_WALL_MATERIAL_TRANSFER_AUTHORITY_ONLY
RESULT=RESOLVED
OUTCOME=OUTCOME_B_MODEL_LEVEL_MATERIAL_K_WALL_TRANSFER_CONTRACT_COMPLETE_NO_INSTANCE
```

The result is deliberately split into model and case levels. The reviewed
contracts define how a future case must supply `k_wall`; they do not supply a
case material or make the wall producer executable.

## 2. Effective reviewed-authority inventory

The following are the effective records after the append-only R14–R19
material overlays. Earlier proposal records remain immutable historical
records and are not used to downgrade the effective reviewed state.

| Authority | Effective lifecycle | Exact role in this audit | Case instance present |
| --- | --- | --- | --- |
| `V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1` | `REVIEWED_AUTHORITY`, independent review `ACCEPTED` | Layer A identity-input shape, ownership, provenance, case/configuration and geometry binding | No |
| `V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1` | `REVIEWED_AUTHORITY`, independent review `ACCEPTED` | Layer B source-bound solid-conductivity property-body contract | No |
| `V07-T172-CONSTANT-K-QUALIFICATION-R1` | `REVIEWED_AUTHORITY`, independent review `ACCEPTED` | Layer C case-level fixed-value/domain-coverage qualification contract | No |
| `V07-T172-WALL-TEMPERATURE-STATE-R1` | `PROPOSED_AUTHORITY` for state-definition scope | Wall-state schema and dependency vocabulary; not a runtime producer | No |
| `V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2` | `REVIEWED_AUTHORITY` | Clean radial relation with supplied films and qualified material input | No |
| `V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2` | `REVIEWED_AUTHORITY` | Local area and cylindrical-resistance mapping | No |

The material review evidence is bound by the exact source records already
accepted by governance:

```ini
LAYER_A_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
LAYER_A_EXTERNAL_ACCEPTANCE_EVIDENCE_CANONICAL_HASH=04625dac1bf22961f338b59f572a01a063fadf0beea8aeec9ce8d3d720a536d2
LAYER_B_ID=V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1
LAYER_B_EXTERNAL_ACCEPTANCE_EVIDENCE_CANONICAL_HASH=e39be8c4d5a06d2947e1de54ce46dc9fee92b1752e266cce2158a82b98b319ea
LAYER_C_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
LAYER_C_CLOSURE_RECORDING_EVIDENCE_CANONICAL_HASH=5e28f71ee42deae968c53b600e19ec10d67f41cccf276324625940a69ee8fd16
CLEAN_WALL_NETWORK_ID=V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2
CLEAN_WALL_NETWORK_HASH=e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29
LOCAL_CYLINDRICAL_MAPPING_ID=V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2
LOCAL_CYLINDRICAL_MAPPING_HASH=49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c
```

## 3. Layer separation and current case state

Layer A identifies a physical material. Layer B carries a complete
source-bound thermal-property body. Layer C determines whether a case may
represent that body as a constant value over a complete wall-temperature
domain. None of these layers permits an engine to infer missing fields.

```ini
MATERIAL_IDENTITY_CONTRACT_BOUND=true
MATERIAL_IDENTITY_REVIEWED_AUTHORITY_AVAILABLE=true
REAL_CASE_MATERIAL_IDENTITY_BOUND=false

THERMAL_CONDUCTIVITY_CONTRACT_BOUND=true
THERMAL_CONDUCTIVITY_REVIEWED_AUTHORITY_AVAILABLE=true
REAL_CASE_K_WALL_PROFILE_BOUND=false

MATERIAL_K_WALL_TRANSFER_CONTRACT_BOUND=true
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROPERTY_BODY_ACTUAL_VALUE_BOUND=false
ACTUAL_MATERIAL_CASE_ACCEPTED=false
```

`MATERIAL_K_WALL_TRANSFER_CONTRACT_BOUND=true` is a model-level result only:
the accepted contracts define the required identity/body/qualification
transfer. `WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false` remains the case-level
result because no case supplies the required identity, property body, source
domain, geometry/support binding and reviewed qualification record.

## 4. Material identity audit

The clean radial network requires the material of the tube wall metal, not a
generic exchanger material or a material name selected by a caller. A future
case record must bind, at minimum, the reviewed Layer A contract by exact ID
and hash and then provide an unambiguous physical identity including the
applicable standard/specification, grade or alloy, product form, condition or
temper where applicable, source/revision, rights/evidence, case/configuration
and wall-geometry/support binding.

The accepted Layer A contract explicitly forbids hidden/default material,
material-name-to-property derivation, runtime material-database lookup as
engineering authority and reuse of the legacy `tube_thermal_conductivity`
field. A bare grade string or caller assertion is therefore not an instance.

### 4.1 Fixture and cross-task guards

The repository contains material-looking values, but none is an effective
TASK172 case authority:

| Record | Classification for this audit | Why it is not promoted |
| --- | --- | --- |
| `T039-MAT-001` / `FIXTURE-GRADE` in TASK037 release-demo and tests | `TEST_FIXTURE` / `DEMO_CARRIER` | It is a scoped TASK037 fixture; its identity and point value are preserved as historical test data, without TASK172 grade/form/source-domain approval. |
| `SA-106-B` material records in TASK017/TASK013 tests | `GENERIC_EXAMPLE` / separate-task authority | They belong to a different preliminary double-pipe material path and are not bound to the TASK172 shell-and-tube case, geometry or wall profile. |
| `SS304` values in double-pipe golden cases | `CASE_BOUND_FROZEN_GOLDEN_FOR_OTHER_SCOPE` | Their case/golden provenance does not bind the TASK172 tube-wall component or its Jμ wall-state contract. |
| legacy `tube_thermal_conductivity` carrier | `UNBOUND_FOR_TASK172` | It lacks the required Layer A/B/C identity, provenance, case, support and domain bindings; reuse is forbidden. |

No fixture, demo, golden or generic material record is selected by this
audit. The absence of a case-bound identity is a blocking condition even
though the model-level identity contract is reviewed.

## 5. Thermal-property and constant-k contract audit

Layer B is accepted for contract scope and permits two property-body forms:

```ini
PROPERTY_QUANTITY_KIND=SOLID_THERMAL_CONDUCTIVITY
COMPONENT_SCOPE=TUBE_WALL_METAL
ALLOWED_PROPERTY_MODELS=FIXED_SOURCE_VALUE,SOURCE_BOUND_K_OF_T
PROPERTY_BODY_REQUIRED=true
SOURCE_PROVENANCE_AND_RIGHTS_REQUIRED=true
CASE_CONFIGURATION_BINDING_REQUIRED=true
GEOMETRY_PHYSICAL_SUPPORT_BINDING_REQUIRED=true
INTERPOLATION_WITHOUT_SOURCE_RULE=FORBIDDEN
EXTRAPOLATION=FORBIDDEN
OUT_OF_DOMAIN=BLOCKED
```

Layer C is separately accepted as a model-level qualification contract. For
the initial constant representation it admits only a source-declared fixed
value with an explicitly declared temperature basis and domain. It does not
convert a `SOURCE_BOUND_K_OF_T` body to a constant by midpoint, averaging,
nearest-row selection, or an engine-chosen approximation. Such a conversion
would require another independently reviewed authority.

Accordingly, the actual case-level property model and source remain
unbound:

```ini
K_WALL_MODEL_TYPE=UNBOUND_NO_CASE_PROPERTY_MODEL_SELECTED
K_WALL_MODEL_SOURCE_ID=NONE_NO_CASE_PROPERTY_SOURCE_SELECTED
K_WALL_MODEL_SOURCE_LOCATION=NONE
K_WALL_MODEL_DOMAIN_BOUND=false
CONSTANT_K_AUTHORITY_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
CONSTANT_K_AUTHORITY_STATUS=REVIEWED_AUTHORITY
CONSTANT_K_VALUE_BOUND=false
CONSTANT_K_TEMPERATURE_DOMAIN_BOUND=false
CONSTANT_K_MATERIAL_IDENTITY_BOUND=false
CONSTANT_K_CASE_TRANSFER_BOUND=false
```

The `CONSTANT_K_TEMPERATURE_DOMAIN_BOUND=false` field retains its established
case-level meaning. It does not contradict the reviewed Layer C model rule
that defines how a future case must cover both wall surfaces.

## 6. Wall-temperature basis for `k_wall`

The reviewed Layer C contract requires the future qualification interval to
be an absolute material-wall-temperature interval covering the complete set
of both:

```text
TUBE_METAL_INNER_SURFACE for every admitted physical support
TUBE_METAL_OUTER_SURFACE for every admitted physical support
```

It forbids substituting bulk, inlet, outlet, arithmetic mean, ambient or a
convenient single surface temperature. The model-level property-state rule
is therefore bound as follows:

```ini
K_WALL_PROPERTY_TEMPERATURE_STATE_RULE_BOUND=true
K_WALL_PROPERTY_TEMPERATURE_STATE=COMPLETE_TUBE_METAL_INNER_AND_OUTER_SURFACE_STATE_COVERAGE;NO_SINGLE_MEAN_SUBSTITUTION
```

This is a coverage rule, not a fabricated wall-temperature value. It does
not assert that either wall state has been solved for a real case. The
existing `V07-T172-WALL-TEMPERATURE-STATE-R1` schema remains a proposed
definition-level authority and does not become a runtime producer through
this audit.

## 7. Material-to-wall geometry relation

The reviewed clean network and local cylindrical mapping establish the
physical relation consumed by a future producer:

```text
R_i,j = 1/(h_i,j A_i,j)
R_w,j = d_i ln(d_o/d_i)/(2 k_wall A_i,j)
R_o,j = 1/(h_o,j A_o,j)
```

The local area and diameter identities are inherited only from the exact
TASK171/TASK037 physical support and the accepted local mapping. They do not
select a material. The model-level binding contract is complete:

```ini
MATERIAL_TO_WALL_GEOMETRY_MAPPING_CONTRACT_BOUND=true
REAL_MATERIAL_TO_WALL_GEOMETRY_MAPPING_BOUND=false
```

The future instance must bind the material component to the same
`TUBE_WALL_METAL` and exact physical support/geometry used by the local
cylindrical relation. A name-similar component, shell material, nominal
diameter without authoritative mapping, or whole-exchanger geometry cannot
substitute for that binding.

## 8. Coupling and producer boundary

No case property model is selected, so the material-to-wall-state coupling
cannot be classified as an actual case behavior:

```ini
K_WALL_CREATES_WALL_STATE_COUPLING=undetermined
```

For a future source-declared fixed value whose domain covers all required
wall states, `k_wall` itself need not create a property-to-wall-temperature
loop. A source-bound `k(T)` body is not converted by Layer C R1 and would
need a separate reviewed constant/variable-property authority. Those two
possibilities cannot be collapsed while the case body is absent.

The clean radial equations are physically defined, but this task does not
make their execution available:

```ini
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
CLEAN_RADIAL_NETWORK_RUNTIME_PRODUCER_BOUND=false
CLEAN_RADIAL_NETWORK_NUMERICAL_EXECUTION_AUTHORIZED=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

The absence of a case material/profile therefore fails closed. No fixture k,
legacy k, runtime catalog lookup, caller assertion or last iterate may be
used to make the future Jμ producer appear ready.

## 9. Model/case decision

The audit resolves the model-level transfer contract but finds no real case
instance. The exact outcome is:

```ini
RESULT=RESOLVED
OUTCOME=OUTCOME_B_MODEL_LEVEL_MATERIAL_K_WALL_TRANSFER_CONTRACT_COMPLETE_NO_INSTANCE
MATERIAL_K_WALL_TRANSFER_CONTRACT_BOUND=true
REAL_CASE_MATERIAL_IDENTITY_BOUND=false
REAL_CASE_K_WALL_PROFILE_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
```

This is not a shell wall-correction approval. The shell correction remains
blocked because Jμ still lacks the separate preliminary-film, Q/wall-state,
applicability, and executable closure authorities.

## 10. Preserved unrelated state and effective blockers

The following branches are not reopened or promoted:

```ini
CWT_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
CHF_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
C3_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_ORDERING_SOURCE_LEAD
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
QUALIFIED_Q_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
```

The parent shell authority remains fail-closed:

```ini
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 11. Governance and next gate

Only this audit document, machine-readable evidence and a new append-only
registry extension are changed. No historical payload/hash is rewritten.
There is no material selection, material profile, property value/curve,
engineering calculation, production change, dependency change, or numerical
work.

```ini
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
REAL_CASE_CONSTRUCTED=false
REAL_MATERIAL_INSTANCE_CONSTRUCTED=false
REAL_K_WALL_PROFILE_CONSTRUCTED=false
WALL_TEMPERATURE_SOLVE_PERFORMED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_JMU_WALL_PRODUCER_CASE_LEVEL_MATERIAL_K_WALL_INSTANCE_BINDING_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The next gate is recorded only as a future authorization target. It must not
be executed automatically and must not create an instance without an
explicit case and source-bound material/property evidence.
