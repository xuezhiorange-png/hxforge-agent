# TASK172 R1 — independent review of the tube wall-correction candidate

## 1. Receipt and scope

This is a documentation-only independent scoped review of the proposed tube
wall-property correction.  It does not promote the candidate, modify TASK026,
or authorize production use.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_AUTHORITY_INDEPENDENT_REVIEW_R1
PR_NUMBER=277
EXPECTED_START_HEAD=4cc4b6253a2b99a19fb25fa8f2adfd1173f50836
MODE=INDEPENDENT_AUTHORITY_REVIEW_ONLY
SUBJECT_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
SUBJECT_SOURCE_ID=SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_FOR_SCOPED_TUBE_WALL_CORRECTION_AUTHORITY
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_TUBE_TURBULENT_WALL_PROPERTY_CORRECTION_ONLY
LIFECYCLE_PROMOTION_PERFORMED=false
TUBE_WALL_CORRECTION_STATUS=PROPOSED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The review accepts the candidate as sufficiently complete for a separately
scoped external authority decision.  It does not convert the candidate into a
`REVIEWED_AUTHORITY`, and it does not make the correction executable.

The effective TASK172 entry ledger remains five blockers:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 2. Source integrity

The selected source was independently checked from the public INL copy:

* **Source:** *RELAP-7 Theory Manual*, INL/EXT-14-31366 Revision 3,
  printed March 2018.
* **Issuer and authors:** Idaho National Laboratory for the U.S. Department
  of Energy; R.A. Berry, L. Zou, H. Zhao, H. Zhang, J.W. Peterson,
  R.C. Martineau, S.Y. Kadioglu, D. Andrs, and E.J. Hansel.
* **Public access:** [official INL PDF](https://inldigitallibrary.inl.gov/content/uploads/50/2026/04/Sort_4964.pdf).
* **Rights:** the report states `Unlimited Release` and `Approved for public
  release; further dissemination unlimited`; the PDF is not vendored.
* **Acquired bytes:** SHA-256
  `ff25dc788b5fbefd91e9dda2e643332c35ff2e2f9acce7f9bfcb2bc8e2d48c75`.

The reviewed locations are §2.2.3, Eqs. (41)–(43), report pp. 30–31, and
§7.4.1.1/§7.4.1.1.1, Eqs. (739)–(744), report pp. 177–179.  The source
expresses the wall heat-transfer coefficient for single-phase liquid flow as a
maximum of laminar, turbulent, and natural-circulation branches (Eq. 739).  In
the tube-geometry turbulent branch it supplies the Gnielinski relation, its
friction-factor convention, liquid Reynolds number, and the wall-temperature
Prandtl correction:

```text
Nu_Gnielinski = ((f/2)(Re - 1000) Pr)
                / (1 + 12.7 (f/2)^0.5 (Pr^(2/3) - 1))
f = [1.58 ln(Re) - 3.28]^-2
Re_liq = rho_liq u_liq D_h / mu_liq
Nu_turb = Nu_Gnielinski (Pr_liq / Pr_w)^0.11
0.05 <= Pr_liq / Pr_w <= 20
```

The source says that `Pr_liq` uses liquid-phase temperature and `Pr_w` uses
wall temperature.  It does not state a separate numeric `Pr` interval for
Eq. (744), and it does not provide a direction-specific exponent.

The source's general §2.2.3.1 discussion also contains a Dittus–Boelter
default for a different internal-pipe model.  That relation is not imported.
The candidate binds specifically to the named tube turbulent branch in
§7.4.1.1.1 and does not combine source sections silently.

## 3. Native TASK026 base

The native target is the reviewed TASK026 R8 production selector rather than
the adjacent generic correlation service:

```ini
NATIVE_BASE_AUTHORITY_ID=SRC-T172-REPO-TUBE
NATIVE_BASE_SELECTOR_VERSION=R8
NATIVE_BASE_CORRELATION_ID=tube_turbulent_gnielinski@1.0.0
NATIVE_SELECTOR_DOCUMENT_PARITY=RESOLVED_BY_SCOPE
NATIVE_BASE_BINDING_STATUS=BOUND
NATIVE_BASE_BINDING_BOUND=true
TASK026_NATIVE_BASE_AUTHORITY=R8_TASK026_SELECTOR
GENERIC_SERVICE_POLICY_APPLIES_TO_TASK026=false
NATIVE_TUBE_CORRELATION_CHANGED=false
LEGACY_TUBE_RESULT_SEMANTICS_CHANGED=false
```

The R8 target formula is:

```text
f_native = (0.790 ln(Re) - 1.64)^-2
f_native/8 is used in the native Gnielinski relation.
```

The relevant pinned artifact identities are inherited without modification:

| Artifact | SHA-256 |
| --- | --- |
| `nusselt_selector.py` | `d2059a83624308b5cdb808e1e314c1b7514e31eaca31899570cde343d3ea2109` |
| `single_phase.py` | `c9cc6444a79975edd3b5b37249a2ee0909a5f07987b3783d70d99e5342f3ff08` |
| `stage_pipeline.py` | `2ec94d18f061c88ca05f7d64f7bac1ea604c6f2c3aa62e994597fd3bd68852c2` |
| `correlations/tube.py` | `e9cd8d26d47821f81810ff8382547d1c907d1ed0182ceabe2d1bcdb1a0ffb526` |
| `TASK-007-tube-annulus-correlations.md` | `c650cc275d05972afd0f86eb80d1c5eaf303a91cfa305b771314f731bd4130cb` |
| `docs/CORRELATIONS.md` | `e137959f5bf04784f78383db27a13736098ea47f926b323510d80dbe23f6fe9e` |

## 4. Algebraic base-compatibility review

The source and native friction-factor conventions are algebraically
compatible.  Let `a = 0.790 ln(Re) - 1.64`.  Then:

```text
f_native = a^-2
1.58 ln(Re) - 3.28 = 2a
f_RELAP = (2a)^-2 = f_native/4
f_RELAP/2 = f_native/8
```

Substitution into source Eq. (741) produces the exact native TASK026 C3
Gnielinski numerator and denominator.  The source Eq. (744) then multiplies
that same base by `(Pr_liq/Pr_w)^0.11`.  No native coefficient, exponent,
formula, dispatch threshold, or result identity is changed.

```ini
BASE_FORMULA_ALGEBRAIC_EQUIVALENCE=PASS_EXACT
FRICTION_CONVENTION_MAPPING_VALID=true
NATIVE_BASE_FORMULA_CHANGED=false
```

This is a representation and combination-location proof only.  It is not an
experimental validation of the target exchanger.

## 5. System-model extraction review

### 5.1 Branch separability

The source Eq. (739) is a system-level selection rule:

```text
h_wall,liq = max(h_lam, h_turb, h_NC)
```

The source nevertheless defines `h_turb` separately in the subsequent tube
geometry equations.  The candidate transfers only the source-defined
turbulent branch to the already scoped TASK026 forced-turbulent C3 branch.
It does not import the source's `max` selector, laminar branch, natural
circulation branch, or mode-selection orchestration.  TASK026 remains the
authority for deciding that its C3 branch is applicable.

This is a component-level extraction with an explicit target precondition,
not a claim that the RELAP system model and TASK026 are identical.

```ini
TURBULENT_BRANCH_SEPARABLE=true
RELAP_SYSTEM_ORCHESTRATION_TRANSFER_REQUIRED=false
SOURCE_SYSTEM_MAX_ORCHESTRATION_IMPORTED=false
NATURAL_CIRCULATION_TRANSFERRED=false
LAMINAR_BRANCH_TRANSFERRED=false
```

### 5.2 Context and source precedence

The general internal-pipe discussion in §2.2.3.1 is not silently mixed with
the selected dependent-closure relation.  The transfer record selects
§7.4.1.1.1 because it explicitly identifies the tube turbulent wall branch,
while the native target independently binds the TASK026 Gnielinski base.  The
Dittus–Boelter relation in the general discussion is therefore outside this
candidate's source role, not an unresolved second formula for the target.

```ini
SOURCE_CONTEXT_SELECTION_BOUND=true
SOURCE_CONTEXT_CONFLICT_RESOLVED_BY_EXPLICIT_SCOPE=true
UNSELECTED_RELAP_INTERNAL_PIPE_DEFAULT_IMPORTED=false
```

## 6. Reynolds and Prandtl domain review

### 6.1 Reynolds domain

The source relation states that its Reynolds number is limited above 1000.
The native TASK026 path has a separate dispatch and C3 contract:

```ini
TASK026_DISPATCH_RE_DOMAIN=Re>=3000 for C3; 2300<=Re<3000 transition/blocked
C3_REPOSITORY_EVALUATOR_RE_DOMAIN=3000<=Re<=5000000
C3_SOURCE_VALIDITY_RE_DOMAIN=3000<Re<5000000
TRANSFER_RE_DOMAIN=3000<Re<5000000
ENDPOINT_3000_TRANSFER_AUTHORIZED=false
ENDPOINT_5000000_TRANSFER_AUTHORIZED=false
```

The effective transfer interval is the strict intersection.  The repository's
inclusive evaluator endpoints are not promoted to source or transfer
authority.

```ini
TRANSFER_RE_DOMAIN_BOUND=true
```

### 6.2 Prandtl domain

Eq. (744) does not state a separate numeric `Pr` interval.  The review does
not invent one or claim that the source independently validated an interval
that it does not print.  Instead, the candidate is restricted to the already
reviewed native C3 domain for both liquid/bulk and wall-property Prandtl
states, with no extension beyond that base domain:

```ini
SOURCE_PR_NUMERIC_INTERVAL_STATED=false
TARGET_PR_DOMAIN=0.5<=Pr<=2000 for each admitted Pr state
PR_DOMAIN_TRANSFER_JUSTIFIED=PASS_AS_STRICT_NATIVE_INTERSECTION
PR_DOMAIN_TRANSFER_EXTENDS_SOURCE=false
PR_DOMAIN_BOUND=true
```

This is sufficient for the scoped candidate because Eq. (744) contributes a
dimensionless correction to the exact target base, the source supplies the
independent ratio bound, and no conflicting narrower source restriction is
stated in the selected branch.  It is a hard target precondition, not a claim
that the source has a hidden broader numeric domain.  A future source-specific
Pr restriction, if identified, must be intersected before implementation.

## 7. Property-ratio and state semantics

The source ratio orientation is retained exactly:

```ini
PROPERTY_RATIO=Pr_liq/Pr_w
PROPERTY_RATIO_ORIENTATION=Pr_liq_DIVIDED_BY_Pr_w
PROPERTY_RATIO_DOMAIN=0.05<=Pr_liq/Pr_w<=20
PROPERTY_RATIO_EXPONENT=0.11
RATIO_CLAMPING_ALLOWED=false
RATIO_EXTRAPOLATION_ALLOWED=false
```

Both Prandtl values must come from the same reviewed property-authority family
at their explicitly identified states.  A missing state, non-positive value,
ratio outside the source interval, or property-authority mismatch blocks; the
engine may not reverse, clamp, or extrapolate the ratio.

The source's state meanings map as follows:

| Source state | TASK172 state | Review result |
| --- | --- | --- |
| Area-average liquid/bulk temperature in §2.2.3 Eq. (41) | `TUBE_FLUID_BULK_STATE` | exact semantic mapping |
| Fluid property state evaluated at source wall temperature for `Pr_w` | `TUBE_FLUID_WALL_INTERFACE` | exact semantic mapping |
| Solid-metal surface temperature | `TUBE_METAL_INNER_SURFACE` | not an automatic substitute |

`TUBE_FLUID_WALL_INTERFACE` means the fluid-facing wall state used to evaluate
the source wall-temperature property, not an independently created solid
thermodynamic property state.  The clean-surface alias to a metal boundary is
a separate passive-network identity and does not authorize metal-property
substitution here.

```ini
BULK_STATE_MAPPING_VALID=true
WALL_STATE_MAPPING_VALID=true
WALL_STATE_MAPPING_AUTHORITY_BOUND=true
METAL_SURFACE_AUTOMATIC_ALIAS=false
```

## 8. Heating/cooling semantics

Eq. (744) is written as one unbranched relation in the selected
single-phase-liquid tube branch.  It contains no different heating and
cooling exponent and no sign-dependent coefficient.  The candidate therefore
allows either heat-flow sign only when the actual wall state, both Prandtl
states, ratio, and all source/base domains are valid:

```ini
HEATING_COOLING_SEMANTICS=UNBRANCHED_SOURCE_RELATION_VALID_FOR_BOTH_DIRECTIONS
HEATING_BRANCH_ADMITTED=true
COOLING_BRANCH_ADMITTED=true
DIRECTION_SPECIFIC_EXPONENT=false
```

This does not infer a new physical branch.  `q` sign and wall-state
calculation remain downstream TASK172 authority; this review only confirms
that the selected source relation itself is not direction-branched.

## 9. Geometry, roughness, and development scope

The transfer is limited to the same physical problem as the native C3 base:

```ini
SOURCE_FLUID_SCOPE=SINGLE_PHASE_LIQUID
TASK172_INITIAL_ADMISSION_FLUID_SCOPE=REVIEWED_PURE_WATER_PROFILE_ONLY
GEOMETRY_SCOPE_VALID=true
GEOMETRY_SCOPE=INTERNAL_CIRCULAR_TUBE_NATIVE_DH
ROUGHNESS_DOMAIN_TYPE=NEGATIVE_SCOPE_PRECONDITION
ROUGHNESS_DOMAIN_VALID=true
ROUGHNESS_EXTENSION_ADMITTED=false
FULLY_DEVELOPED_SCOPE_VALID=true
ENTRANCE_OR_SHORT_PIPE_EXTENSION_ADMITTED=false
ANNULUS_TRANSFERRED=false
ROD_BUNDLE_TRANSFERRED=false
GAS_TRANSFERRED=false
TWO_PHASE_TRANSFERRED=false
```

`ROUGHNESS_DOMAIN_VALID=true` means only that the candidate's strict smooth
base precondition is explicit.  It is not a numerical roughness range proved
by the source.  Roughness-dependent use, entrance effects, short pipes,
annuli, rod bundles, gas, two-phase flow, and natural-circulation alternatives
remain blocked.

## 10. Canonical identity and fail-closed review

The proposed authority identity must bind, at minimum:

* authority ID/version and lifecycle state;
* source ID, revision, exact location, rights status, and acquired-byte hash;
* native TASK026 base ID/version and source-artifact hashes;
* Eq. (744), exponent, friction-convention mapping, and combination mode;
* transfer Re domain, native target Pr domain, ratio orientation and bounds;
* pure-water fluid scope, circular geometry, smoothness precondition, and
  fully-developed condition;
* bulk and fluid-facing wall state identities;
* source-context selection and the explicit exclusion of RELAP orchestration;
* out-of-domain and extrapolation policies.

Changing any identity-bearing source, equation, exponent, domain, state,
geometry, base identity, combination rule, or lifecycle field requires a new
authority identity.  Missing or mismatched source bytes/revision, native base,
state, ratio, domain, geometry, or combination rule blocks.  No caller
assertion, library availability, neutral factor, or last iterate can create a
valid correction authority.

```ini
CANONICAL_PREIMAGE_COMPLETE=true
OUT_OF_DOMAIN_POLICY=BLOCKED
EXTRAPOLATION_POLICY=FORBIDDEN
MISSING_STATE_POLICY=BLOCKED
SOURCE_REVISION_MISMATCH_POLICY=BLOCKED
NATIVE_BASE_IDENTITY_MISMATCH_POLICY=BLOCKED
```

## 11. Scoped decision and limits

All four targeted questions are resolved for this review scope:

1. The source's larger `max(laminar,turbulent,natural-circulation)` model is
   not transferred; its explicitly defined turbulent tube branch is separable
   and is mapped to TASK026's already selected turbulent branch.
2. The source's absent standalone numeric Pr interval is recorded honestly.
   The target candidate uses the strict, already reviewed native C3 Pr domain
   as a non-widening hard intersection, while retaining the source's exact
   ratio interval.
3. The source relation is unbranched for heating/cooling; no new directional
   exponent or coefficient is inferred.
4. The source wall temperature is mapped to the fluid-facing wall state, not
   silently to a metal property state.

Accordingly:

```ini
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_TUBE_WALL_CORRECTION_AUTHORITY
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_TUBE_TURBULENT_WALL_PROPERTY_CORRECTION_ONLY
REVIEW_EVIDENCE_BOUND=true
TRANSFERABILITY_ESTABLISHED=true

TUBE_WALL_CORRECTION_RESOLUTION_RESULT=AUTHORITY_CANDIDATE_COMPLETE
TUBE_WALL_CORRECTION_STATUS=PROPOSED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
LIFECYCLE_PROMOTION_PERFORMED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

This is not approval of the source as a reviewed production authority.  It is
not an experimental validation, a material qualification, a wall-temperature
solver decision, a numerical convergence decision, or permission to apply the
candidate to shell-side Bell heat transfer.

## 12. Governance and next gate

No production or engineering implementation is part of this receipt:

```ini
NATIVE_BASE_CORRECTION_PERFORMED=false
TASK026_FILES_CHANGED=false
TASK007_FILES_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_TUBE_WALL_CORRECTION_ACCEPTANCE
NO_STEP_IMPLIES_THE_NEXT=true
```

The machine-readable review evidence and registry overlay bind the source
fingerprint, native-base fingerprints, algebraic proof, system-model
extraction decision, domain intersections, state mappings, canonical field
set, and lifecycle state.  Historical R1–R23 records remain immutable.
