# TASK172 R2 — targeted primary transfer authority acquisition for tube wall correction

## 1. Scope and disposition

This is a documentation-only acquisition for the remaining
`TUBE-WALL-CORRECTION-AUTHORITY` blocker on Draft PR277.  It follows the
R22 native-base selector adjudication and does not reopen the already resolved
selector ownership question.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_PRIMARY_TRANSFER_AUTHORITY_ACQUISITION_R2
PR_NUMBER=277
PREVIOUS_HEAD_SHA=96cb245390972e24fb3569b248d9fb385da968dd
MODE=TARGETED_PRIMARY_TRANSFER_AUTHORITY_ACQUISITION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
TARGET_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
RESULT=PASS_WITH_PROPOSED_AUTHORITY_CANDIDATE
SOURCE_RESEARCH_SCOPE=EXACT_TASK026_C3_BASE_AND_LAWFULLY_REVIEWABLE_TUBE_TRANSFER_ONLY
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```
The result is a complete candidate package, not an approval or an executable
production admission.  The candidate remains `PROPOSED_AUTHORITY` pending an
independent authority review.  The canonical blocker is not removed.

The effective five-blocker ledger is unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 2. Native target and domain separation

The native target is the reviewed TASK026 production path, not the adjacent
generic correlation service:

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

The three Reynolds domains remain distinct and are never collapsed into
`Re >= 3000`:

| Domain | Exact meaning | Transfer consequence |
| --- | --- | --- |
| `TASK026_DISPATCH_RE_DOMAIN` | `Re < 2300` selects C1/C2; `2300 <= Re < 3000` is transition/blocked; `Re >= 3000` dispatches TASK026 C3, subject to the C3 applicability check | Dispatch is not by itself source validity |
| `C3_REPOSITORY_EVALUATOR_RE_DOMAIN` | `3000 <= Re <= 5000000` in the pinned C3 metadata/evaluator | Inclusive endpoints remain repository behavior only |
| `C3_SOURCE_VALIDITY_RE_DOMAIN` | `3000 < Re < 5000000` in the inherited source authority | This open interval controls transfer; no endpoint is promoted |
| `TRANSFER_RE_DOMAIN` | `intersection(TASK026 dispatch, exact native C3 authority, exact transfer source)` = `3000 < Re < 5000000` | `TRANSFER_RE_DOMAIN_BOUND=true` |

```ini
TASK026_DISPATCH_RE_DOMAIN=Re < 2300 laminar; 2300 <= Re < 3000 transition/blocked; Re >= 3000 TASK026 C3 dispatch; C3 applicability remains separately enforced
C3_REPOSITORY_EVALUATOR_RE_DOMAIN=3000 <= Re <= 5000000
C3_SOURCE_VALIDITY_RE_DOMAIN=3000 < Re < 5000000
TRANSFER_RE_DOMAIN=3000 < Re < 5000000
TRANSFER_RE_DOMAIN_BOUND=true
ENDPOINT_3000_TRANSFER_AUTHORIZED=false
ENDPOINT_5000000_TRANSFER_AUTHORIZED=false
```

The transfer package retains the native C3 Prandtl domain
`0.5 <= Pr <= 2000`.  This is a reviewed native input-domain restriction, not
a new extension or a wider claim about the transfer source:

```ini
PR_DOMAIN_BOUND=true
EFFECTIVE_TRANSFER_PR_DOMAIN=0.5 <= Pr <= 2000; inherited native C3 domain; no extension beyond it
```

## 3. Acquired source

### 3.1 Selected authoritative source candidate

The new source is an official government-laboratory technical manual, not the
original Gnielinski publication.  It is used because the manual itself gives a
complete source-specific tube relation and temperature correction in one
publicly reviewable location.  It is recorded as a verified source and as a
proposed transfer candidate; it is not self-promoted to reviewed authority.

| Field | Bound value |
| --- | --- |
| Candidate source ID | `SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3` |
| Source revision | `INL/EXT-14-31366 Revision 3`, printed March 2018 |
| Title | *RELAP-7 Theory Manual* |
| Authors | R.A. Berry, L. Zou, H. Zhao, H. Zhang, J.W. Peterson, R.C. Martineau, S.Y. Kadioglu, D. Andrs, E.J. Hansel |
| Issuer | Idaho National Laboratory, operated for the U.S. Department of Energy |
| Exact locations | §2.2.3, Eqs. (41)–(43), report pp. 30–31; §7.4.1.1 and §7.4.1.1.1, Eqs. (739)–(744), report pp. 177–179 |
| Public access | [official INL PDF](https://inldigitallibrary.inl.gov/content/uploads/50/2026/04/Sort_4964.pdf) |
| Acquired bytes | SHA-256 `ff25dc788b5fbefd91e9dda2e643332c35ff2e2f9acce7f9bfcb2bc8e2d48c75` |
| Rights | Cover states `Unlimited Release` and `Approved for public release; further dissemination unlimited`; PDF is not vendored |
| Source role | `OFFICIAL_GOVERNMENT_LABORATORY_TECHNICAL_MANUAL` |
| Source status | `VERIFIED_SOURCE`; candidate transfer package `PROPOSED_AUTHORITY` |

The manual states that its current wall heat-transfer models are steady-state
and fully developed; short-pipe/entrance effects are outside that model.  In
its single-phase liquid / tube-geometry section it defines the Gnielinski
relation, the liquid Reynolds number, and the temperature correction:

```text
Nu_Gnielinski = ((f/2)(Re - 1000) Pr)
                / (1 + 12.7 (f/2)^0.5 (Pr^(2/3) - 1))

f = [1.58 ln(Re) - 3.28]^-2
Re_liq = rho_liq u_liq D_h / mu_liq

Nu_turb = Nu_Gnielinski (Pr_liq / Pr_w)^0.11
0.05 <= Pr_liq / Pr_w <= 20
```

The source defines `Pr_liq` using the liquid-phase/bulk temperature and
`Pr_w` using wall temperature.  The cited relation has no separate
heating/cooling exponent or gas branch; the proposed target contract is
therefore one unbranched single-phase-liquid wall-temperature relation.  It
does not authorize use for gases, two-phase flow, boiling, annuli, rod bundles,
or natural-circulation alternatives.

### 3.2 Exact compatibility with the native C3 base

The source manual uses a friction-factor convention different from the native
TASK026 expression.  Compatibility is established algebraically, without
changing the native formula:

```text
a = 0.790 ln(Re) - 1.64
f_native = a^-2

1.58 ln(Re) - 3.28 = 2a
f_source = (2a)^-2 = f_native / 4
f_source / 2 = f_native / 8
```

Substituting `f_source / 2` into the manual's Eq. (741) gives the native
TASK026 C3 numerator and denominator exactly.  The source's Eq. (744) is then
a source-defined multiplicative correction to that same base relation.  This
is a compatibility proof for the formula representation and combination
location; it is not an experimental validation and does not alter any native
coefficient, threshold, or result identity.

## 4. Transferability package

The following restrictions are part of the candidate package.  A field marked
`true` means the effective transfer contract is bounded; it does not mean the
candidate has been independently approved.

| Required field | Candidate binding and limitation | Status |
| --- | --- | --- |
| Base correlation | Exact native `tube_turbulent_gnielinski@1.0.0`, TASK026 R8 path | `BOUND` |
| Correction equation | INL Eq. (744), multiplicative `(Pr_liq/Pr_w)^0.11` | `BOUND` |
| Coefficient/exponent | Source exponent `0.11`; no other correction coefficient | `BOUND` |
| Re domain | Source states `Re > 1000`; intersection with native source/evaluator contract gives `3000 < Re < 5000000` | `BOUND` |
| Pr domain | Effective target domain `0.5 <= Pr <= 2000`, inherited native C3 restriction; no widening | `BOUND` |
| Property-ratio domain | Source `0.05 <= Pr_liq/Pr_w <= 20` | `BOUND` |
| Fluid family | Single-phase liquid only; proposed initial HXForge admission is the already reviewed pure-water profile | `BOUND` |
| Geometry | Native circular internal tube; `D_h` is native tube inside diameter | `BOUND` |
| Roughness | Only the native smooth/Petukhov-style base representation; no roughness correction or rough-tube transfer is admitted | `BOUND_AS_STRICT_PRECONDITION` |
| Length/development | Fully developed only; entrance/short-pipe correction is not admitted | `BOUND` |
| Thermal boundary | Steady single-phase forced wall heat transfer with explicitly supplied wall temperature; no boiling/phase branch | `BOUND` |
| Heating/cooling | One source relation with no direction-specific branch; both signs require the same source-defined ratio semantics and valid wall state | `BOUND_AS_UNBRANCHED_RELATION` |
| Bulk state | `TUBE_FLUID_BULK_STATE`; source §2.2.3 defines area-average bulk temperature over the fluid cross-section | `BOUND` |
| Wall state | `TUBE_FLUID_WALL_INTERFACE`; source Eq. (744) consumes wall-temperature Prandtl state | `BOUND` |
| Metal mapping | No automatic alias to `TUBE_METAL_INNER_SURFACE`; any clean-surface alias remains a separate reviewed contract | `BOUND` |
| Combination mode | `MULTIPLICATIVE_CORRECTION`, explicitly shown by Eq. (744) | `BOUND` |
| Direct transfer evidence | Same Gnielinski structure plus the exact friction-factor conversion above; no silent composition | `BOUND` |

The source does not provide a separate numeric Pr interval at Eq. (744).  The
candidate consequently uses the already reviewed native C3 Pr domain as a
hard intersection and records that no extension is being claimed.  Likewise,
the candidate does not infer a roughness correction: it requires the native
base representation and rejects roughness-dependent use.  These are
fail-closed target preconditions, not invented source ranges.

```ini
PRIMARY_SOURCE_BOUND=true
SOURCE_RIGHTS_BOUND=true
CORRECTION_EQUATION_BOUND=true
CORRECTION_COEFFICIENTS_EXPONENTS_BOUND=true
PR_DOMAIN_BOUND=true
PROPERTY_RATIO_DOMAIN_BOUND=true
FLUID_FAMILY_DOMAIN_BOUND=true
GEOMETRY_DOMAIN_BOUND=true
ROUGHNESS_DOMAIN_BOUND=true
LENGTH_DEVELOPMENT_DOMAIN_BOUND=true
THERMAL_BOUNDARY_DOMAIN_BOUND=true
HEATING_COOLING_BRANCHES_BOUND=true

TUBE_CORRECTION_BULK_STATE_ID=TUBE_FLUID_BULK_STATE
TUBE_CORRECTION_WALL_STATE_ID=TUBE_FLUID_WALL_INTERFACE
BULK_STATE_DEFINITION_BOUND=true
WALL_STATE_DEFINITION_BOUND=true
WALL_STATE_MAPPING_AUTHORITY_BOUND=true

COMBINATION_MODE=MULTIPLICATIVE_CORRECTION
COMBINATION_RULE_BOUND=true
DIRECT_TRANSFER_EVIDENCE_BOUND=true
TRANSFERABILITY_ESTABLISHED=true
OUT_OF_DOMAIN_POLICY=BLOCKED
EXTRAPOLATION_POLICY=FORBIDDEN
```

`TRANSFERABILITY_ESTABLISHED=true` here means that the proposed package has a
complete, bounded transfer description.  It does not mean `REVIEWED_AUTHORITY`
or production permission.  Independent review remains required.

## 5. Source limitations and non-selected evidence

The acquisition checked the following sources without silently promoting them:

| Evidence | Disposition |
| --- | --- |
| [Sieder & Tate (1936), DOI 10.1021/ie50324a027](https://doi.org/10.1021/ie50324a027) | Primary bibliographic identity only in this acquisition; publisher full text and a rights-cleared review copy were not obtained. No exponent or equation is transcribed. |
| [ASME PTC 12.5 single-phase heat exchangers](https://www.asme.org/codes-standards/find-codes-standards/single-phase-heat-exchangers) | Official standard candidate, but the normative text is copyrighted/purchase-only for this review; not selected as the source copy. |
| [Sandia Aria manual](https://www.sandia.gov/files/sierra/Aria_Users_5_22/command_summary/heat_transfer_correlations.html) | Feature/interface corroboration only; the exposed page does not supply a complete transferable liquid circular-tube equation/domain package. Existing `VERIFIED_SOURCE_NOT_TRANSFERABLE` disposition is retained. |
| [Gnielinski 2013 KIT record](https://publikationen.bibliothek.kit.edu/1000041280) | Publication metadata only; no complete reviewable transfer package was acquired for this gate. |
| Taler 2016 and other publisher-hosted variants | Discovery/cross-check only where full text and transfer rights were unavailable or the base geometry/correlation differed. |

No search snippet, abstract, blog, library default, remembered exponent, or
secondary equation is used as authority.  The selected INL manual is an
authoritative implementation source for this candidate, while the original
Gnielinski lineage remains an inherited native-base source.  The source does
not authorize transfer to TASK166 Bell shell heat transfer and is not used for
that purpose.

## 6. Lifecycle and fail-closed semantics

```ini
TUBE_WALL_CORRECTION_RESOLUTION_RESULT=AUTHORITY_CANDIDATE_COMPLETE
TUBE_WALL_CORRECTION_STATUS=PROPOSED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
SOURCE_CANDIDATE_LIFECYCLE=VERIFIED_SOURCE_WITH_PROPOSED_TRANSFER_PACKAGE
NEW_AUTHORITY_SELF_APPROVAL=false
```

The candidate cannot enter production until an independent reviewer accepts the
transfer package and a later implementation gate supplies the already
authorized wall-state, material/property, numerical and case-binding
capabilities.  Missing or mismatched source ID, revision, source bytes,
native-base ID/hash, state identity, Pr ratio, domain, geometry, or combination
rule must block.  The engine must not extrapolate, clip the ratio, substitute
metal temperature for fluid-facing wall temperature, or apply this tube
candidate to shell-side Bell heat transfer.

No source, formula, threshold, tolerance, production module, dependency, test
semantics, material instance, or shell correction is changed by this receipt.

## 7. Evidence and next gate

The machine-readable companion records the source fingerprint, all transfer
fields, native artifact fingerprints, algebraic compatibility proof, rejected
evidence, effective blockers and lifecycle status.  Its own canonical hash is
bound in the append-only registry extension.

```ini
NATIVE_BASE_CORRECTION_PERFORMED=false
TASK026_FILES_CHANGED=false
TASK007_FILES_CHANGED=false
GENERIC_SERVICE_POLICY_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_TUBE_WALL_CORRECTION_AUTHORITY_INDEPENDENT_REVIEW_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```
