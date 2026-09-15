# TASK172 R1 — primary transfer authority acquisition for tube wall correction

## 1. Receipt and bounded scope

This is a documentation-only, targeted primary-authority acquisition for the
tube-side wall-property correction blocker on Draft PR277. It freezes the
native TASK026 target, records the source material that was actually acquired
and reviewed, and records the transferability decision. It does not implement
or approve a wall correction and it does not modify TASK026, the material
layers, the shell-side correction, numerical authority, or mesh authority.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_PRIMARY_TRANSFER_AUTHORITY_ACQUISITION_R1
PR=277
PREVIOUS_HEAD_SHA=2855ef3aa84211250b47130e5c459fd6dca37327
MODE=TARGETED_PRIMARY_AUTHORITY_ACQUISITION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
TARGET_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
RESULT=BLOCKED
SOURCE_RESEARCH_SCOPE=TASK026_NATIVE_TARGET_AND_PRIMARY_TRANSFERABILITY_ONLY
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The effective entry ledger remains exactly five blockers:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The earlier material model-level closure and case-level fail-closed state are
inherited without change. No material, conductivity value, correction factor,
wall temperature, or numerical value is introduced here.

## 2. Native TASK026 target freeze

The target is the production TASK026 tube-side thermal path, not a new
correlation and not an adjacent generic service:

```ini
NATIVE_TARGET_SELECTOR_AUTHORITY_ID=SRC-T172-REPO-TUBE
NATIVE_TARGET_SELECTOR_VERSION=R8
TASK026_TARGET_PATH=stage_pipeline -> compute_single_phase -> nusselt_selector
NATIVE_TARGET_CORRELATIONS=tube_laminar_cwt@1.0.0;tube_laminar_chf@1.0.0;tube_turbulent_gnielinski@1.0.0
NATIVE_TARGET_EFFECTIVE_RE_DOMAIN=C1/C2 Re < 2300; R8 selector blocks 2300 <= Re < 3000; C3 dispatch Re >= 3000 with declared C3 maximum 5e6
NATIVE_TARGET_PR_DOMAIN=C1/C2 Pr > 0.6; C3 0.5 <= Pr <= 2000
NATIVE_TARGET_GEOMETRY=circular_tube; characteristic length=tube inside diameter
NATIVE_TARGET_WALL_CORRECTION=NONE
```

The R8 selector source and the native correlation metadata were audited at
the pinned repository base. The native path has no active wall-property
correction, no wall-viscosity state consumption, no roughness correction and
no length-based wall-property extension. C1/C2 are fully developed laminar
constant-wall-temperature/constant-heat-flux branches; C3 is the native
Petukhov/Gnielinski circular-tube branch. Those identities and their result
semantics remain unchanged.

There is an unresolved repository contract discrepancy which this receipt
does not silently resolve:

* `nusselt_selector.py` R8 dispatches `2300 <= Re < 3000` to a blocked
  transition state and dispatches `Re >= 3000` to C3.
* `src/hexagent/correlations/flow.py` and the adjacent
  `src/hexagent/correlations/service.py` classify `2300 <= Re <= 10000` as
  transitional and require `Re > 10000` for turbulent flow.
* The TASK-007 documentation records the latter conservative transition
  policy while also recording the C3 correlation range from 3000.

The TASK026 stage path is therefore identifiable, but the native selector and
the repository-wide historical document/service semantics are not at parity.
An active wall correction cannot be bound to an ambiguous native base without
a separate TASK026 semantic correction. This acquisition does not modify that
contract.

```ini
NATIVE_SELECTOR_DOCUMENT_PARITY=UNRESOLVED
NATIVE_BASE_BINDING_STATUS=BLOCKED_SEMANTIC_DISCREPANCY
NATIVE_BASE_BINDING_BOUND=false
NATIVE_BASE_CORRELATION_CHANGED=false
LEGACY_TUBE_RESULT_SEMANTICS_CHANGED=false
```

Audited native files and their pinned SHA-256 values are recorded in the
machine-readable evidence. The temporary historical design reference named by
the implementation is not a repository source artifact and is not promoted.

## 3. Primary source acquisition

### 3.1 Official Sandia/Aria report

The following official report was acquired from the public OSTI endpoint and
reviewed from the downloaded bytes:

| Field | Evidence |
| --- | --- |
| Source | `SANDIA-ARIA-2016-FILM-GRADIENT-AUDIT` |
| Report | *SIERRA Multimechanics Module: Aria User Manual — Version 4.40* |
| Authors | Patrick K. Notz, Samuel R. Subia, Matthew M. Hopkins, Harry K. Moffat, David R. Noble, Tolulope O. Okusanya |
| Revision | `SAND2016-4159`, printed 2016-05-02 |
| Public access | `https://www.osti.gov/servlets/purl/1262728` |
| Exact bytes | SHA-256 `1300bf8605e3a9f7f64a7e91bb4cc39c9b60f6ec551f8a1bab8f9fab0c6844bc` |
| Rights evidence | Cover states “Approved for public release; further dissemination unlimited”; the PDF is not vendored |
| Reviewed locations | §34.1.1 classification, §34.1.2 Types 72–74, §34.2.4, §34.2.10, and §4.1.203 p113 |

The report gives the following source-specific evidence:

* Type 72 is Gnielinski for turbulent gas flow in a smooth circular tube.
  Its stated dependencies are `K`, `D_h`, `Re`, `Pr`, and `f`; the stated
  range is `3000 < Re < 5000000` and `0.5 < Pr < 2000`. It does not define a
  wall-property correction for the circular-tube target.
* Type 73 is a modified Gnielinski relation for turbulent flow in an annulus
  with the inner wall heated and the outer wall insulated. It includes
  annulus ratio and wall-state inputs and declares a gas-or-liquid scope, but
  its geometry and boundary-condition semantics are annulus-specific.
* Type 74 is the corresponding annulus relation with the inner wall
  insulated and the outer wall heated. It is also annulus-specific.
* §34.2.4 documents the film-gradient correction feature for pipe and
  annulus Types 72–74, and §34.2.10 documents a gas-oriented exponent
  parameter. These manual controls do not, by themselves, authorize a
  liquid circular-tube transfer to the native TASK026 C3 identity.
* §4.1.203 is an input/interface description. The equation/domain/combination
  fields required for the current liquid circular-tube target are not bound
  there.

The official report is consequently `VERIFIED_SOURCE` for the stated Aria
correlation taxonomy and source-specific Type 72–74 behavior, but it is not a
transferable authority for the current target. The earlier R1 record's
statement about §4.1.203 being an interface location remains true; this
receipt adds the deeper §34.1 audit without rewriting the historical record.

### 3.2 Other reviewed candidates

| Candidate | Available evidence | Disposition for current target |
| --- | --- | --- |
| Sieder–Tate 1936, DOI `10.1021/ie50324a027` | Bibliographic primary identity only; publisher full text/equation pages and a rights-cleared review copy were not acquired | `CANDIDATE`; no lawful complete equation/domain/transfer package |
| Goncalves, Costa & Bagajewicz 2019 | Public author/university copy; selected base relations and a separate laminar relation were reviewed | `VERIFIED_SOURCE` for its stated scope; no explicit extension compatible with native TASK026 C3 |
| Martin & Gnielinski 2000 | Author copy; property normalization for external tube-bundle crossflow | Not transferable to internal circular-tube TASK026; no Bell/TASK026 transfer rule |
| Existing `REPO-TUBE` authority | Pinned C1/C2/C3 identities and native no-wall-correction contract | `REVIEWED_AUTHORITY` as unchanged base only |

No search result, abstract, blog, textbook recollection, library behavior or
secondary reproduction is used as numerical authority. In particular, no
remembered Sieder–Tate exponent and no generic neutral correction is adopted.

## 4. Transferability decision

The required target package must bind the exact source equation and all
coefficient/exponent values, source and rights identity, native base identity,
Re/Pr/property-ratio/fluid/geometry/roughness/development/thermal-boundary
domains, heating and cooling branches, bulk and fluid-facing wall states, a
source-defined combination rule, and direct transfer evidence. The acquired
materials do not bind that complete tuple.

| Required transfer field | Evidence at this revision | Status |
| --- | --- | --- |
| Source correlation family and revision | Sieder–Tate body not acquired; Sandia families are source-specific | `UNBOUND` |
| Exact TASK026 base binding | R8 target is identifiable, but repository transition semantics are discrepant | `BLOCKED_SEMANTIC_DISCREPANCY` |
| Internal circular-tube problem | Sandia Type 72 is circular but gas/no wall correction; Types 73/74 are annular | `UNBOUND` |
| Exact correction equation | No target-compatible equation bound | `UNBOUND` |
| Coefficients/exponents | No target-compatible coefficient set bound | `UNBOUND` |
| Reynolds domain | Candidate domains do not transfer to the exact target | `UNBOUND` |
| Prandtl domain | Candidate domains do not transfer to the exact target | `UNBOUND` |
| Property-ratio domain | Candidate ratio is annulus/source-specific; no target transfer | `UNBOUND` |
| Fluid family | Liquid branch appears only in annulus source context; water transfer not established | `UNBOUND` |
| Geometry/diameter/roughness | Circular target is known; correction source geometry/roughness transfer is absent | `UNBOUND` |
| Length/development | Native target is developed/no thermal-development correction; source transfer limits absent | `UNBOUND` |
| Thermal boundary | CWT/CHF target metadata known; source-compatible wall correction branch absent | `UNBOUND` |
| Heating/cooling branches | No target-compatible source branch rule | `UNBOUND` |
| Bulk state definition | Required `TUBE_FLUID_BULK_STATE` is named, but source mapping is absent | `UNBOUND` |
| Fluid-facing wall state | Required `TUBE_FLUID_WALL_INTERFACE` is named, but source mapping is absent | `UNBOUND` |
| Metal-vs-fluid surface mapping | No alias authorized | `UNBOUND` |
| Base combination rule | No source rule for replace/multiply/compose with TASK026 | `UNBOUND` |
| Direct transfer evidence | No validated direct transfer to this target | `UNBOUND` |

Therefore:

```ini
SELECTED_PRIMARY_SOURCE_ID=NONE
SELECTED_PRIMARY_SOURCE_CLASS=NONE
SELECTED_PRIMARY_SOURCE_REVISION=NONE
SELECTED_PRIMARY_SOURCE_LOCATION=NONE
SELECTED_PRIMARY_SOURCE_RIGHTS=NONE
PRIMARY_SOURCE_BOUND=false
CORRECTION_EQUATION_BOUND=false
CORRECTION_COEFFICIENTS_EXPONENTS_BOUND=false
RE_DOMAIN_BOUND=false
PR_DOMAIN_BOUND=false
PROPERTY_RATIO_DOMAIN_BOUND=false
FLUID_FAMILY_DOMAIN_BOUND=false
GEOMETRY_DOMAIN_BOUND=false
ROUGHNESS_DOMAIN_BOUND=false
LENGTH_DEVELOPMENT_DOMAIN_BOUND=false
THERMAL_BOUNDARY_DOMAIN_BOUND=false
HEATING_COOLING_BRANCHES_BOUND=false
TUBE_CORRECTION_BULK_STATE_ID=UNBOUND
TUBE_CORRECTION_WALL_STATE_ID=UNBOUND
BULK_STATE_DEFINITION_BOUND=false
WALL_STATE_DEFINITION_BOUND=false
WALL_STATE_MAPPING_AUTHORITY_BOUND=false
COMBINATION_RULE_BOUND=false
TRANSFERABILITY_ESTABLISHED=false
OUT_OF_DOMAIN_POLICY=BLOCKED
EXTRAPOLATION_POLICY=FORBIDDEN
```

The failure is an authority/transferability failure, not evidence that a
particular correction is numerically wrong. The current native C3 remains
usable only under its existing no-wall-correction contract; this receipt does
not turn that omission into an active correction.

## 5. Resolution and governance

```ini
TUBE_WALL_CORRECTION_RESOLUTION_RESULT=BLOCKED_NO_TRANSFERABLE_PRIMARY_AUTHORITY
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
SELECTED_CORRECTION_PROPOSAL_CREATED=false
```

Unresolved authority fields are:

```text
NATIVE_BASE_SEMANTIC_DISCREPANCY
SOURCE_CORRELATION_FAMILY
TARGET_COMPATIBLE_EQUATION
COEFFICIENTS_OR_EXPONENTS
RE_DOMAIN
PR_DOMAIN
PROPERTY_RATIO_DOMAIN
FLUID_FAMILY_DOMAIN
GEOMETRY_DOMAIN
ROUGHNESS_DOMAIN
LENGTH_DEVELOPMENT_DOMAIN
THERMAL_BOUNDARY_DOMAIN
HEATING_COOLING_BRANCHES
BULK_STATE_DEFINITION
WALL_FLUID_STATE_DEFINITION
WALL_STATE_MAPPING
BASE_COMBINATION_RULE
DIRECT_TRANSFER_EVIDENCE
SIEDER_TATE_FULL_TEXT_RIGHTS_CLEARED_REVIEW_COPY
```

This receipt does not start shell-side correction research, alter the
material authority layers, change TASK026, add an equation or coefficient,
introduce a factor of one, run a wall solver, perform numeric qualification,
or change any dependency. The next gate is:

```ini
NEXT_GATE=REVIEW_TUBE_WALL_CORRECTION_BLOCKER_OR_PROVIDE_COMPLETE_PRIMARY_TRANSFER_AUTHORITY
```
