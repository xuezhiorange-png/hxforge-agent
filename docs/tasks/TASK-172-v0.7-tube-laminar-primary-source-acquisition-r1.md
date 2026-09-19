# TASK172 — targeted primary-source acquisition for laminar tube wall authority R1

## 1. Receipt and immutable boundary

This is a documentation-only acquisition for the unresolved laminar branch
coverage in `TUBE-WALL-CORRECTION-AUTHORITY`.  It follows the prior laminar
adjudication and does not change TASK026, its constants, its selector, or the
already accepted turbulent C3 authority.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_PRIMARY_SOURCE_ACQUISITION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=043b9eef76d12f1469ab52a5b5f393192b098bfa
PREVIOUS_HEAD_SHA=043b9eef76d12f1469ab52a5b5f393192b098bfa
MODE=TARGETED_LAMINAR_PRIMARY_SOURCE_ACQUISITION_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_WITH_BLOCKER_RETAINED
SOURCE_ACQUISITION_SCOPE=EXACT_TASK026_LAMINAR_CWT_AND_CHF_SOURCE_SEMANTICS
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TURBULENT_C3_AUTHORITY_CHANGED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The acquired source body is used to determine what the exact analytical
laminar solutions assume.  The receipt is not an independent review and does
not promote a correction or an omission disposition.

## 2. Acquisition result

An official NASA/NTRS technical report was obtained as a complete, publicly
reviewable derivation source.  Its Chapter 3 derivation covers the two
boundary conditions separately and explicitly frames the analytical treatment
with constant material properties.  It therefore closes the source-body
question for the constant-property model, but it does not supply either:

* a variable-property wall/bulk correction compatible with the exact TASK026
  CWT or CHF selector branch; or
* a source-qualified TASK172 rule that permits omitting such a correction when
  a future wall-temperature/property closure is active.

The source is consequently recorded as `VERIFIED_SOURCE` for its stated
constant-property derivations.  No branch-specific TASK172 wall disposition
candidate is created.

```ini
SOURCE_BODY_ACQUISITION_STATUS=COMPLETE
CWT_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CHF_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CWT_TASK172_VARIABLE_PROPERTY_USE_AUTHORIZED=false
CHF_TASK172_VARIABLE_PROPERTY_USE_AUTHORIZED=false
CWT_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CHF_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CWT_OMISSION_SEMANTICS_BOUND=false
CHF_OMISSION_SEMANTICS_BOUND=false
```

This result is deliberately different from both `ACTIVE_CORRECTION_REQUIRED`
and `EXPLICIT_NO_ACTIVE_WALL_CORRECTION_REQUIRED`.  A constant-property
analytical model is not, by itself, authority for a variable-property TASK172
wall-state extension or for a silent omission of that extension.

## 3. Acquired source and rights

| Field | Bound value |
| --- | --- |
| Source | `NASA-CR-189922` / `NAS 1.26:189922` |
| Title | *Elements of radiative interactions in gaseous systems* |
| Author | Surendra N. Tiwari |
| Issuer | Old Dominion University for NASA Langley Research Center |
| Date | December 1991 |
| Source class | `OFFICIAL_GOVERNMENT_TECHNICAL_REPORT` |
| NTRS landing page | [NASA NTRS record 19920012099](https://ntrs.nasa.gov/citations/19920012099) |
| Acquired PDF | [NTRS PDF](https://ntrs.nasa.gov/api/citations/19920012099/downloads/19920012099.pdf) |
| Acquired bytes | SHA-256 `46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e` |
| PDF review | 198 pages; report pages reviewed by rendered-page inspection because the acquired PDF is image/scanned content |
| Rights | NTRS metadata identifies the work as U.S. Government work with public use permitted; source PDF is not vendored |
| Source status | `VERIFIED_SOURCE` for the exact cited derivations; not `REVIEWED_AUTHORITY` for a TASK172 wall disposition |

The source bytes, landing-page identity, retrieval date (`2026-09-15`), page
locations, and rights statement are recorded in the machine-readable evidence
and registry overlay.  The report is not treated as the original publication
of the Incropera table carried by TASK026; the native TASK026 source identity
and result semantics remain unchanged.

## 4. CWT branch — independent source audit

```ini
BRANCH=LAMINAR_CWT
CORRELATION_ID=tube_laminar_cwt@1.0.0
THERMAL_BOUNDARY=CONSTANT_WALL_TEMPERATURE
CWT_SOURCE_ID=SRC-T172-NASA-CR-189922-CWT-R1
CWT_SOURCE_CLASS=OFFICIAL_GOVERNMENT_TECHNICAL_REPORT
CWT_SOURCE_REVISION=NASA-CR-189922;NAS 1.26:189922;December 1991
CWT_SOURCE_LOCATION=Chapter 3 §3.3.3; report pp.14-16 and 19-20; Eqs.3.20a,3.28,3.47-3.51; PDF pp.28-34 (1-indexed)
CWT_SOURCE_RIGHTS=US_GOVERNMENT_WORK_PUBLIC_USE_PERMITTED_PER_NTRS_METADATA
CWT_SOURCE_BYTES_HASH=46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e
CWT_SOURCE_BODY_ACQUIRED=true
CWT_EQUATION_BOUND=true
CWT_BOUNDARY_CONDITION_BOUND=true
CWT_PROPERTY_EVALUATION_BASIS_BOUND=true
CWT_CONSTANT_PROPERTY_ASSUMPTION_BOUND=true
CWT_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CWT_OMISSION_SEMANTICS_BOUND=false
CWT_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED
```

The source's CWT derivation uses the circular-tube fully developed analytical
problem with centerline symmetry and a uniform wall-temperature boundary.  In
the classical no-viscous-heating result, the wall temperature is prescribed
and the fully developed result is reported as `Nu_D = 3.658` (Eq. 3.51), which
is consistent with the native TASK026 rounded value `Nu_D = 3.66`.  The source
derivation is framed using constant material properties; its thermal
diffusivity and conductance terms therefore use one constant nominal property
set rather than a bulk-state/wall-state property pair.

The source does not define a separate wall-fluid property state, viscosity
ratio, heating/cooling correction branch, or combination rule for a future
temperature-dependent TASK172 closure.  The report also discusses a distinct
viscous-heating variant; that variant is not silently converted into a wall
viscosity correction for the native CWT branch.

The CWT source semantics are thus:

```ini
CWT_EQUATION=FULLY_DEVELOPED_CIRCULAR_TUBE_CONSTANT_PROPERTY_CWT_NU_D_3.658_EQ_3.51
CWT_PROPERTY_STATE_DEFINITION=CONSTANT_NOMINAL_PROPERTIES_IN_ANALYTICAL_MODEL
CWT_WALL_PROPERTY_STATE_DEFINED=false
CWT_BULK_WALL_PROPERTY_RATIO_DEFINED=false
CWT_VARIABLE_PROPERTY_EXTENSION_DEFINED=false
CWT_HEATING_COOLING_RULE_FOR_VARIABLE_PROPERTY=UNBOUND
CWT_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CWT_TASK172_VARIABLE_PROPERTY_USE_AUTHORIZED=false
CWT_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
CWT_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
```

## 5. CHF branch — independent source audit

```ini
BRANCH=LAMINAR_CHF
CORRELATION_ID=tube_laminar_chf@1.0.0
THERMAL_BOUNDARY=CONSTANT_HEAT_FLUX
CHF_SOURCE_ID=SRC-T172-NASA-CR-189922-CHF-R1
CHF_SOURCE_CLASS=OFFICIAL_GOVERNMENT_TECHNICAL_REPORT
CHF_SOURCE_REVISION=NASA-CR-189922;NAS 1.26:189922;December 1991
CHF_SOURCE_LOCATION=Chapter 3 §3.3.2; report pp.14-19; Eqs.3.20a,3.28,3.39-3.46; PDF pp.28-33 (1-indexed)
CHF_SOURCE_RIGHTS=US_GOVERNMENT_WORK_PUBLIC_USE_PERMITTED_PER_NTRS_METADATA
CHF_SOURCE_BYTES_HASH=46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e
CHF_SOURCE_BODY_ACQUIRED=true
CHF_EQUATION_BOUND=true
CHF_BOUNDARY_CONDITION_BOUND=true
CHF_PROPERTY_EVALUATION_BASIS_BOUND=true
CHF_CONSTANT_PROPERTY_ASSUMPTION_BOUND=true
CHF_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CHF_OMISSION_SEMANTICS_BOUND=false
CHF_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED
```

The CHF derivation treats a fully developed laminar circular-tube flow with a
uniform wall heat flux, centerline symmetry, and negligible frictional
heating.  The source reports `Nu_D = 4.364` (Eq. 3.46), consistent with the
native TASK026 rounded value `Nu_D = 4.36`.  As with CWT, the derivation uses a
constant nominal property set; it does not prescribe a variable-property
bulk/wall evaluation or a correction to be combined with the native CHF
constant.

The CHF source semantics are kept independent from CWT:

```ini
CHF_EQUATION=FULLY_DEVELOPED_CIRCULAR_TUBE_CONSTANT_PROPERTY_CHF_NU_D_4.364_EQ_3.46
CHF_PROPERTY_STATE_DEFINITION=CONSTANT_NOMINAL_PROPERTIES_IN_ANALYTICAL_MODEL
CHF_WALL_PROPERTY_STATE_DEFINED=false
CHF_BULK_WALL_PROPERTY_RATIO_DEFINED=false
CHF_VARIABLE_PROPERTY_EXTENSION_DEFINED=false
CHF_HEATING_COOLING_RULE_FOR_VARIABLE_PROPERTY=UNBOUND
CHF_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CHF_TASK172_VARIABLE_PROPERTY_USE_AUTHORIZED=false
CHF_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
CHF_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
```

## 6. Domain and assumption audit

The acquired derivation supports the following source-level assumptions for
both branches.  Native TASK026 domain checks remain a separate inherited
contract and are not widened by this receipt.

| Requirement | CWT | CHF | Acquisition disposition |
| --- | --- | --- | --- |
| Circular-tube geometry | stated | stated | Bound for source model; native inside-diameter basis retained |
| Laminar flow | stated | stated | Bound for source model; no transition extension |
| Fully developed hydrodynamics | stated | stated | Bound; entrance/developing correction not supplied |
| Fully developed thermal field | stated by the analytical solution | stated by the analytical solution | Bound; no entrance-region transfer |
| Thermal boundary | uniform wall temperature | uniform wall heat flux | Bound independently |
| Property assumption | constant material properties | constant material properties | Bound; no variable-property transfer |
| Wall/bulk property states | no distinct pair defined | no distinct pair defined | Unbound for TASK172 variable-property use |
| Axial conduction | not present in the reduced relation | not present in the reduced relation | No separate axial-conduction extension authorized |
| Viscous/frictional heating | classical CWT result does not authorize a wall correction; source variant is separate | negligible frictional heating assumption | No wall-correction transfer authorized |
| Heating/cooling branch rule | not supplied for variable-property extension | not supplied for variable-property extension | Unbound |
| Fluid family | analytical incompressible-fluid context | analytical incompressible-fluid context | Does not authorize a broader production fluid profile |

The common constant-property framing is evidence for why the native analytical
values are not a variable-property wall correction.  It is not evidence that
`requires_wall_viscosity=false` is an explicit TASK172 omission authority.

## 7. Source finding and lifecycle decision

```ini
LAMINAR_CWT_SOURCE_BODY_ACQUIRED=true
LAMINAR_CWT_EQUATION_BOUND=true
LAMINAR_CWT_BOUNDARY_CONDITION_BOUND=true
LAMINAR_CWT_PROPERTY_EVALUATION_BASIS_BOUND=true
LAMINAR_CWT_CONSTANT_PROPERTY_ASSUMPTION_BOUND=true
LAMINAR_CWT_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
LAMINAR_CWT_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CWT_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CWT_AUTHORITY_CANDIDATE_CREATED=false

LAMINAR_CHF_SOURCE_BODY_ACQUIRED=true
LAMINAR_CHF_EQUATION_BOUND=true
LAMINAR_CHF_BOUNDARY_CONDITION_BOUND=true
LAMINAR_CHF_PROPERTY_EVALUATION_BASIS_BOUND=true
LAMINAR_CHF_CONSTANT_PROPERTY_ASSUMPTION_BOUND=true
LAMINAR_CHF_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
LAMINAR_CHF_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CHF_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CHF_AUTHORITY_CANDIDATE_CREATED=false
```

The exact source body is now available, but the TASK172 disposition remains
unresolved because the source does not answer the additional variable-property
wall-state question.  The source therefore cannot be used to create an
`EXPLICIT_NO_ACTIVE_WALL_CORRECTION_REQUIRED` candidate.  Equally, the source
does not establish that a correction is required, so no active-correction
candidate is created.

The following are expressly not used as omission authority:

* the native `requires_wall_viscosity=false` flag;
* the rounded native constants `3.66` and `4.36` alone;
* the accepted turbulent C3 correction;
* a remembered Sieder–Tate factor or any neutral factor;
* a narrow water range;
* a library/backend result or a search snippet.

## 8. Effective state and parent blocker

```ini
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
TURBULENT_C3_CORRECTION_STATUS=REVIEWED_AUTHORITY
TURBULENT_C3_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false

HISTORICAL_RECORDS_REWRITTEN=false
TASK026_FILES_CHANGED=false
TASK026_EQUATIONS_CHANGED=false
TASK026_CONSTANTS_CHANGED=false
TASK026_DOMAINS_CHANGED=false
TURBULENT_C3_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

The separate case-level tube-correction admission gate remains active and
unimplemented.  It must continue to reject a case unless every admitted
native branch has a reviewed correction or explicit omission disposition,
with exact native identity, source, state, domain, geometry, material and
property bindings.

## 9. Evidence, registry and next gate

The companion evidence file records the acquired source bytes hash, source
rights, exact branch locations, rendered-page review, source assumptions,
native artifact fingerprints, branch findings, rejected/limited evidence and
the unchanged five-blocker ledger.  The append-only registry extension binds
the evidence and this document by SHA-256.

No lifecycle promotion is performed by this acquisition.  The next gate is:

```ini
NEXT_GATE=AWAIT_COMPLETE_LAMINAR_PRIMARY_SOURCE_AUTHORITY
NO_STEP_IMPLIES_THE_NEXT=true
```

That gate must obtain or explicitly review a source-qualified disposition for
the TASK172 variable-property wall-state boundary for both native laminar
branches.  It must not transfer the turbulent C3 correction, infer omission
from the native boolean, or alter TASK026.
