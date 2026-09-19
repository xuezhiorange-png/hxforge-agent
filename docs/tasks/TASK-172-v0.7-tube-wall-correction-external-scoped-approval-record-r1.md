# TASK172 R1 — external scoped acceptance for the tube wall correction

## 1. Decision and scope

This receipt records the external scoped review decision supplied in the
authorized task instruction.  It is a model-level lifecycle record only; it is
not a GitHub review event, a human expert signature, or production permission.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_EXTERNAL_SCOPED_APPROVAL_RECORD_R1
PR_NUMBER=277
EXPECTED_START_HEAD=8401b0ac6f1313cbede53c1630252f40672ad824
MODE=EXTERNAL_REVIEW_DECISION_RECORDING_ONLY
AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
SOURCE_ID=SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_TUBE_WALL_CORRECTION_AUTHORITY
EXTERNAL_REVIEW_SCOPE=MODEL_LEVEL_TUBE_TURBULENT_WALL_PROPERTY_CORRECTION_ONLY
EXTERNAL_REVIEW_EVIDENCE_BOUND=true
EXTERNAL_SCOPED_ACCEPTANCE=true
```

The external decision is recorded as an external ChatGPT review decision
provided by the authorized task instruction.  No GitHub reviewer, human
expert, organization, credential, or professional signature is claimed.

## 2. Source and native-base bindings

The acceptance retains the verified source and native selector bindings.  It
does not promote the source itself to a new lifecycle state.

```ini
SOURCE_REGISTRY_ID=INL-EXT-14-31366-R3
SOURCE_TITLE=RELAP-7 Theory Manual
SOURCE_REVISION=INL/EXT-14-31366 Revision 3
SOURCE_AUTHOR_LAST=J.E. Hansel
SOURCE_BYTES_SHA256=ff25dc788b5fbefd91e9dda2e643332c35ff2e2f9acce7f9bfcb2bc8e2d48c75
SOURCE_STATUS=VERIFIED_SOURCE

NATIVE_BASE_AUTHORITY_ID=SRC-T172-REPO-TUBE
NATIVE_BASE_SELECTOR_VERSION=R8
NATIVE_BASE_CORRELATION_ID=tube_turbulent_gnielinski@1.0.0
BASE_FORMULA_ALGEBRAIC_EQUIVALENCE=PASS_EXACT
FRICTION_CONVENTION_MAPPING_VALID=true
TURBULENT_BRANCH_SEPARABLE=true
RELAP_SYSTEM_ORCHESTRATION_TRANSFER_REQUIRED=false
```

The source correction from `E.J. Hansel` to `J.E. Hansel` is already recorded
by the immutable R25 provenance correction.  This R26 receipt reuses that
effective projection and does not rewrite R23, R24, or R25.

## 3. Accepted model-level authority scope

Only the scoped model-level turbulent tube wall-property correction is
accepted:

```text
Nu_turb = Nu_Gnielinski * (Pr_liq / Pr_w)^0.11
```

The accepted scope remains bound to:

```ini
PROPERTY_RATIO_ORIENTATION=Pr_liq_DIVIDED_BY_Pr_w
PROPERTY_RATIO_DOMAIN=0.05<=Pr_liq/Pr_w<=20
PROPERTY_RATIO_EXPONENT=0.11
COMBINATION_MODE=MULTIPLICATIVE_CORRECTION
TRANSFER_RE_DOMAIN=3000<Re<5000000
ENDPOINT_3000_TRANSFER_AUTHORIZED=false
ENDPOINT_5000000_TRANSFER_AUTHORIZED=false
SOURCE_PR_NUMERIC_INTERVAL_STATED=false
TARGET_PR_DOMAIN=0.5<=Pr<=2000
PR_DOMAIN_TRANSFER_JUSTIFIED=PASS_AS_STRICT_NATIVE_INTERSECTION
PR_DOMAIN_TRANSFER_EXTENDS_SOURCE=false
TUBE_CORRECTION_BULK_STATE_ID=TUBE_FLUID_BULK_STATE
TUBE_CORRECTION_WALL_STATE_ID=TUBE_FLUID_WALL_INTERFACE
BULK_STATE_MAPPING_VALID=true
WALL_STATE_MAPPING_VALID=true
METAL_SURFACE_AUTOMATIC_ALIAS=false
HEATING_COOLING_SEMANTICS=UNBRANCHED_SOURCE_RELATION_VALID_FOR_BOTH_DIRECTIONS
SOURCE_FLUID_SCOPE=SINGLE_PHASE_LIQUID
TASK172_INITIAL_ADMISSION_FLUID_SCOPE=REVIEWED_PURE_WATER_PROFILE_ONLY
GEOMETRY_SCOPE=INTERNAL_CIRCULAR_TUBE_NATIVE_DH
ROUGHNESS_DOMAIN_TYPE=NEGATIVE_SCOPE_PRECONDITION
FULLY_DEVELOPED_SCOPE_VALID=true
```

No roughness-dependent extension, entrance or short-pipe extension, annulus,
rod-bundle, gas, two-phase, natural-circulation, shell-side Bell transfer, or
other out-of-scope transfer is admitted.

## 4. Lifecycle promotion boundary

The external acceptance permits exactly this model-level promotion:

```ini
TUBE_WALL_CORRECTION_STATUS=REVIEWED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
LIFECYCLE_PROMOTION_PERFORMED=true
```

This promotion does not select a material, create a material profile, bind a
case-level property value, or authorize execution for an actual segment.
Case-level admission remains fail-closed until all required state, source,
native-base, material, geometry, and exact-hash bindings are present and
reviewed.  Out-of-domain, extrapolated, missing, or mismatched inputs remain
blocked.

## 5. Engineering semantics and blocker state

The acceptance changes no equations, coefficients, exponent, domain,
transferability rule, state mapping, or combination rule.  It does not remove
the canonical entry blocker because the remaining record is a model-level
authority acceptance, not an implementation or case-level readiness decision.

```ini
SOURCE_PROVENANCE_CORRECTED=true
ENGINEERING_REVIEW_RESULT=PASS_FOR_SCOPED_TUBE_WALL_CORRECTION_AUTHORITY
TRANSFERABILITY_ESTABLISHED=true
ENGINEERING_SEMANTICS_CHANGED=false
EQUATION_CHANGED=false
EXPONENT_CHANGED=false
DOMAIN_CHANGED=false
TRANSFERABILITY_CHANGED=false
STATE_MAPPING_CHANGED=false
COMBINATION_RULE_CHANGED=false
INDEPENDENT_REVIEW_ENGINEERING_CONCLUSION_CHANGED=false

TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 6. Governance and next gate

The source remains `VERIFIED_SOURCE`; no source lifecycle promotion is
performed.  The acceptance is not a material/property case approval, and no
Golden, Ready, or Merge state follows from it.

```ini
HISTORICAL_R23_R24_R25_PAYLOADS_REWRITTEN=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK026_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
MATERIAL_PROFILE_CREATED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ADJUDICATION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```
