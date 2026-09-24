# TASK172 R3 — native TASK026 preliminary tube-film transfer authority

## 1. Receipt and scope

This documentation/evidence-only receipt audits whether the existing native
TASK026 tube-side film can be used as an input to a future TASK172 clean
radial wall-temperature producer.  It does not implement a transfer adapter,
change TASK026, add a wall correction, select a case branch, solve a wall
temperature, or start numerical work.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_R3
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=d2d4ebb02dc4c6de66e2c2421ccf43e037621eea
MODE=TASK026_NATIVE_PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
SHELL_PRELIMINARY_FILM_SOURCE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_LEAD
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The shell preliminary-film branch is intentionally frozen.  This receipt
does not select `h_c`, a geometry-corrected film without `J_mu`, a fully
corrected film, or any other shell-side coefficient.  The Q, material, wall
conductivity, mean-bulk-temperature, localization, and numerical authorities
remain unchanged from the accepted predecessor state.

## 2. Native TASK026 evidence

The audit uses the exact R8 implementation at the predecessor head.  No
production source is copied into the evidence payload and no source file is
modified.

| Native authority | Location | Object identity at predecessor | Relevant semantics |
| --- | --- | --- | --- |
| `R8_TASK026_SELECTOR` | `src/hexagent/exchangers/shell_tube/tube_side_thermal/nusselt_selector.py` | Git blob `750d92e2da2284202190afe93cf47589eb3a6bb2`; SHA-256 `d2059a83624308b5cdb808e1e314c1b7514e31eaca31899570cde343d3ea2109` | Re/Pr regime dispatch; CWT/CHF selection; native Gnielinski C3 |
| `TASK026_R8_SINGLE_PHASE_PIPELINE` | `src/hexagent/exchangers/shell_tube/tube_side_thermal/single_phase.py` | Git blob `90a39ab66dd3b2600f228cf513bf398c9c0cb254`; SHA-256 `c9cc6444a79975edd3b5b37249a2ee0909a5f07987b3783d70d99e5342f3ff08` | S06–S12 property snapshot, velocity, Re, Pr, Nu and `h_i` |
| `TASK026_R8_STAGE_PIPELINE` | `src/hexagent/exchangers/shell_tube/tube_side_thermal/stage_pipeline.py` | Git blob `51034d2efdfdbeb5b5149467da323de95d8d474f`; SHA-256 `2ec94d18f061c88ca05f7d64f7bac1ea604c6f2c3aa62e994597fd3bd68852c2` | typed request, TASK025 read set, property/phase checks, transition blocking |
| `TASK026_R8_TYPED_REQUEST` | `src/hexagent/exchangers/shell_tube/tube_side_thermal/request.py` | Git blob `492d269fd82222c6c04b442d9ef90fa600d70730`; SHA-256 `d438504563e4c48adb6cdaa00b5552b121909d344781e4a9a99c049fbcf84ab4` | required `thermal_boundary_condition`, property snapshot and frozen deferred capabilities |
| `TASK026_CORRELATION_CONTRACT` | `docs/tasks/TASK-007-tube-annulus-correlations.md` | Git blob `35b51c5007cbd48556d93d14e0106431c60a0cb9`; SHA-256 `c650cc275d05972afd0f86eb80d1c5eaf303a91cfa305b771314f731bd4130cb` | native correlation scope and the separate generic contract |

The exact R8 selector facts are:

* `Re < 2300` dispatches to the laminar family.  The required typed
  `thermal_boundary_condition` is `CWT` or `CHF`, and
  `select_laminar_correlation` returns `Nu_D=3.66` or `Nu_D=4.36`
  respectively.  The native laminar Pr precondition is `Pr > 0.6`.
* `2300 <= Re < 3000` returns `TRANSITION` with no correlation identity and
  the stage pipeline emits `BL_REGIME_NO_CORRELATION_APPLICABLE`.
* `Re >= 3000` dispatches to the native turbulent C3/Gnielinski path.  Its
  native evaluator Pr envelope is `0.5 <= Pr <= 2000`; the native calculation
  is `h_i=Nu*k/D_h`.
* The typed pipeline validates the caller-supplied property snapshot and
  recomputes its property snapshot hash.  The snapshot contains bulk
  temperature and pressure plus `rho`, `mu`, `k`, and `c_p`, but it does not
  carry a TASK171 physical-support identity, local cell identity, wall state,
  or wall viscosity.
* The TASK025 read set supplies hydraulic and flow-area identities.  The
  native calculation uses `total_parallel_flow_area_m2` for velocity and
  `hydraulic_diameter_m` for `h_i`; it does not define a local wall-area or
  physical-support projection.

The generic TASK-007 document and the exact R8 selector are retained as
separate records.  This R3 receipt does not alter their existing transition
scope wording or reconcile that historical documentation distinction.

## 3. Native branch-selection contract

Native branch selection is not ambiguous inside TASK026.  Given a typed,
hash-valid property snapshot, positive mass flow, TASK025 hydraulic inputs,
Re/Pr calculated by the frozen pipeline, and the required thermal boundary
condition, the selector is deterministic and contains no hidden CWT/CHF
default:

```ini
PRELIMINARY_TUBE_FILM_SOURCE_RULE_BOUND=true
TASK026_BRANCH_SELECTION_INPUTS_BOUND=true
TASK026_THERMAL_BOUNDARY_SELECTION_BOUND=true
TASK026_BRANCH_SELECTION_DETERMINISTIC=true
TASK026_NATIVE_BRANCH_SELECTION_INPUTS=PROPERTY_SNAPSHOT_RHO_MU_K_CP;TASK025_TOTAL_PARALLEL_FLOW_AREA;TASK025_HYDRAULIC_DIAMETER;POSITIVE_MASS_FLOW;THERMAL_BOUNDARY_CONDITION_CWT_OR_CHF
TASK026_NATIVE_BRANCH_SELECTION_RULE=Re<2300->LAMINAR(CWT_OR_CHF);2300<=Re<3000->TRANSITION_NO_CORRELATION;Re>=3000->TURBULENT_C3;PR_ENVELOPE_REQUIRED
```

These fields mean that TASK026 can select its own native result once its
typed inputs are present.  They do **not** mean that TASK172 has selected a
case branch.  A separate transfer edge still has to bind the selected branch
to the clean radial wall producer, including its state location, area basis,
physical support, preliminary role, and any branch-specific wall-correction
policy.

The missing Task172-level binding is therefore recorded separately:

```ini
TASK172_PRELIMINARY_BRANCH_SELECTION_BINDING=false
TASK172_PRELIMINARY_THERMAL_BOUNDARY_CASE_BINDING=false
TASK172_PRELIMINARY_FILM_ROLE_BINDING=false
```

## 4. Branch-by-branch transfer disposition

### 4.1 Laminar CWT

The reviewed CWT authority is an exact native constant-property scope.  It
does not create a variable-property wall correction and does not itself
declare that the CWT result is the preliminary film for a Jμ wall producer.
The native result could be a future explicit film input only after a case
selects CWT and a separate transfer rule binds the result to the located
TASK172 tube bulk state, local area basis and physical support.

```ini
CWT_NATIVE_RULE_BOUND=true
CWT_NATIVE_CORRELATION_ID=tube_laminar_cwt@1.0.0
CWT_NATIVE_FORM=Nu_D=3.66;h_i=Nu_D*k/D_h
CWT_TASK172_PRELIMINARY_TRANSFER_BOUND=false
CWT_TASK172_PRELIMINARY_TRANSFER_LIMITATION=NO_TASK172_CASE_BRANCH_ROLE_OR_LOCATED_AREA_SUPPORT_BINDING;NO_PRELIMINARY_FILM_TRANSFER_AUTHORITY
CWT_PRELIMINARY_ACTIVE_WALL_CORRECTION=NOT_CREATED;NATIVE_SCOPE_CONSTANT_PROPERTY_ONLY
```

### 4.2 Laminar CHF

The CHF result has the same transfer boundary.  Its exact native constant
property rule is preserved, but a future preliminary use is not authorized
merely because the typed request contains a `thermal_boundary_condition`.

```ini
CHF_NATIVE_RULE_BOUND=true
CHF_NATIVE_CORRELATION_ID=tube_laminar_chf@1.0.0
CHF_NATIVE_FORM=Nu_D=4.36;h_i=Nu_D*k/D_h
CHF_TASK172_PRELIMINARY_TRANSFER_BOUND=false
CHF_TASK172_PRELIMINARY_TRANSFER_LIMITATION=NO_TASK172_CASE_BRANCH_ROLE_OR_LOCATED_AREA_SUPPORT_BINDING;NO_PRELIMINARY_FILM_TRANSFER_AUTHORITY
CHF_PRELIMINARY_ACTIVE_WALL_CORRECTION=NOT_CREATED;NATIVE_SCOPE_CONSTANT_PROPERTY_ONLY
```

### 4.3 Transition

The transition band is explicitly unavailable as a preliminary film.  The
native result has no correlation identity and the pipeline fail-closes at S09.
No neutral value, extrapolation, or neighboring-branch fallback is allowed.

```ini
TRANSITION_NATIVE_RULE_BOUND=true
TRANSITION_NATIVE_RANGE=2300<=Re<3000
TRANSITION_PRELIMINARY_FILM_AVAILABLE=false
TRANSITION_PRELIMINARY_FILM_DISPOSITION=BL_REGIME_NO_CORRELATION_APPLICABLE
```

### 4.4 Turbulent C3

The native C3 branch is a valid TASK026 result path, but the accepted
TASK172 C3 wall-property correction is a separate reviewed model-level
authority.  It is not automatically part of the native TASK026 result or a
preliminary wall-producer policy.  A future transfer must decide, by explicit
authority, whether the preliminary input is the uncorrected native C3 film or
the C3 result with its reviewed active correction.  The latter also requires
the located tube wall state and its case-level prerequisites.

```ini
C3_NATIVE_RULE_BOUND=true
C3_NATIVE_CORRELATION_ID=tube_turbulent_gnielinski@1.0.0
C3_NATIVE_FORM=Gnielinski_Nu;h_i=Nu*k/D_h
C3_NATIVE_WALL_STATE_INPUT=false
C3_REVIEWED_ACTIVE_CORRECTION_AUTHORITY=V07-T172-TUBE-WALL-CORRECTION-R1
C3_TASK172_PRELIMINARY_TRANSFER_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY=UNRESOLVED_PRELIMINARY_ROLE_MUST_NOT_SILENTLY_SELECT_UNCORRECTED_C3_OR_APPLY_ACCEPTED_C3_CORRECTION
```

Accordingly, `C3_TASK172_PRELIMINARY_TRANSFER_BOUND=false` is not a finding
against the accepted C3 authority.  It records that a model-level C3
correction authority is not the same thing as a TASK172 preliminary-film
transfer authority.

## 5. Native-to-TASK172 transfer checks

The transfer requires more than a native `h_i` value.  The future clean
radial network needs a film coefficient located on the same physical support
as the wall branch, with an explicit area basis and state identity.  The
native TASK026 request and result do not supply that projection:

| Transfer edge | Native evidence | R3 disposition |
| --- | --- | --- |
| Tube bulk state | Caller-supplied `PropertySnapshot` has bulk T/P and properties; request/provenance are not a TASK171 physical cell/support identity | Not bound |
| Local film/area basis | Velocity uses total parallel flow area; `h_i` uses native `D_h`; no local inner-area or support rule | Not bound |
| Physical support | TASK025 read set has hydraulic/area identities but no TASK171 `physical_segment_id`/support interval binding | Not bound |
| Branch role | Native selector requires CWT/CHF and dispatches C3, but no selected TASK172 preliminary-film role exists | Not bound |
| C3 correction policy | Accepted C3 wall correction is separate and requires wall state; preliminary use is not selected | Not bound |

```ini
TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_BOUND=false
TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_REASON=NATIVE_PROPERTY_SNAPSHOT_VALUES_LACK_LOCATED_TASK171_STREAM_SIDE_CELL_AND_PHYSICAL_SUPPORT_IDENTITY
TASK026_TO_TASK172_AREA_MAPPING_BOUND=false
TASK026_TO_TASK172_AREA_MAPPING_REASON=NATIVE_TOTAL_PARALLEL_FLOW_AREA_AND_HYDRAULIC_DIAMETER_DO_NOT_DEFINE_LOCAL_WALL_AREA_RESISTANCE_BASIS
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_BOUND=false
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_REASON=TASK026_RESULT_HAS_NO_TASK171_PHYSICAL_INTERVAL_OR_WALL_INTERFACE_BINDING
```

The native selector inputs are therefore complete and deterministic, while
the transfer edges remain fail-closed.  No same-index assumption, arithmetic
state averaging, nominal diameter substitution, or hidden interpolation is
introduced.

## 6. Dependency semantics

The dependency status is branch-conditional.  Native CWT/CHF computation has
no wall-viscosity input.  The accepted C3 correction, if selected by a future
case, requires a tube-fluid wall state; a preliminary film role could then
participate in a wall-state dependency.  Because no branch and no
preliminary policy are selected here, the global fields remain
`undetermined` rather than being forced to one branch's answer.

```ini
PRELIMINARY_TUBE_FILM_ACTIVE_WALL_CORRECTION_REQUIRED=undetermined
TUBE_FILM_DEPENDS_ON_WALL_STATE=undetermined
TUBE_FILM_DEPENDS_ON_ACTIVE_WALL_CORRECTION=undetermined
TUBE_FILM_CREATES_WALL_STATE_LOOP=undetermined
JMU_WALL_COUPLING_CIRCULARITY_PATH_IDENTIFIED=true
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_WALL_COUPLING_ITERATION_AUTHORIZED=false
FIXED_POINT_ITERATION_PERFORMED=false
```

This does not reopen or decide the shell preliminary-film branch.  The
potential shell-side path remains conditional because the shell film source
is still unbound.  No iteration, relaxation, tolerance, fallback, or
last-iterate acceptance is specified.

## 7. Preserved dependencies and forbidden shortcuts

The following state is carried forward without promotion or deletion:

```ini
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
SHELL_PRELIMINARY_FILM_SOURCE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_LEAD
QUALIFIED_Q_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

The following transfers remain prohibited:

* TASK026 native CWT/CHF/C3 is not promoted to a TASK172 preliminary input
  by correlation-name similarity.
* The accepted C3 wall correction is not applied to CWT/CHF and is not
  silently selected for preliminary use.
* Transition receives no guessed film and no neighboring-branch fallback.
* The native total flow area is not reinterpreted as a local wall area.
* A caller property snapshot is not treated as a located TASK171 state.
* TASK034 pressure-drop wall semantics, legacy `tube_thermal_conductivity`,
  or an unreviewed shell film are not reused.

## 8. Decision

The native TASK026 source rule is complete and deterministic, but none of the
branch-specific Task172 preliminary transfer edges is complete.  The smallest
direct gaps are:

1. no case-bound TASK172 selection of CWT, CHF, or C3 as the preliminary film;
2. no explicit preliminary role/policy for whether C3 uses its active wall
   correction;
3. no located tube-bulk-state transfer;
4. no local area-basis transfer; and
5. no physical-support transfer.

The correct result is therefore a blocked transfer authority, not a defect in
the native selector:

```ini
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
JMU_PRELIMINARY_TUBE_FILM_TRANSFER_CANDIDATE_CREATED=false
ACQUISITION_OUTCOME=OUTCOME_F_MULTIPLE_TUBE_TRANSFER_GAPS
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_GATE=AUTHORIZE_TASK172_JMU_PRELIMINARY_TUBE_FILM_CASE_BRANCH_ROLE_AND_SUPPORT_TRANSFER_CLOSURE_R4_ONLY
```

The next gate is intentionally limited to the case-selected native branch,
preliminary-film role/C3 policy, and located bulk/area/physical-support
transfer.  It does not authorize shell-film research, Q/material work,
implementation, or numerical qualification.

## 9. Governance and artifact integrity

Only this review document, its machine-readable evidence, and the append-only
registry extension are in scope.  Historical R1/R2/R3/R4 records and all
TASK026/TASK166 payloads remain immutable.  No new authority is promoted and
no production admission path is created.

```ini
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
HISTORICAL_RECORDS_REWRITTEN=false
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The machine-readable companion records the exact predecessor SHA, source
fingerprints, native branch facts, transfer dispositions, preserved shell/Q/
material state, canonical self-hash, and the next gate.  It does not contain
an actual film instance, material, wall state, or numerical result.
