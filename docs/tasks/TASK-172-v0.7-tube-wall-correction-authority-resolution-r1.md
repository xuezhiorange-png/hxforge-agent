# TASK172 R1 — tube wall-correction authority resolution

## 1. Receipt and scope

This is a documentation-only physical-authority resolution for Draft PR277.
It audits the active tube-side wall-property correction requested for TASK172;
it does not implement or approve a correction. The historical R1 proposal and
the R3–R5 semantic audits remain immutable. This receipt adds a bounded source
disposition and transferability decision; it does not modify TASK026 or any
material, shell-side, numerical or mesh authority.

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_AUTHORITY_RESOLUTION_R1
PR=277
PREVIOUS_HEAD_SHA=57a70e1c7eee22526a719c09e7a6d71a715e0f47
MODE=PHYSICAL_AUTHORITY_RESOLUTION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
SUBJECT_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
SOURCE_RESEARCH_SCOPE=TARGETED_NATIVE_BASE_AND_WALL_PROPERTY_TRANSFER_AUDIT
RESULT=BLOCKED
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The effective TASK172 ledger remains exactly:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The model-level material entry authority remains closed, but case-level
material authority remains absent and fail-closed. This resolution does not
change that state:

```ini
MODEL_LEVEL_MATERIAL_ENTRY_AUTHORITY_STATUS=CLOSED
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=true
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROPERTY_BODY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
ACTUAL_MATERIAL_CASE_ACCEPTED=false
CASE_LEVEL_FAIL_CLOSED_GATE_ID=TASK172-CASE-LEVEL-MATERIAL-AUTHORITY-ADMISSION
CASE_LEVEL_FAIL_CLOSED_GATE_RUNTIME_IMPLEMENTED=false
```

## 2. Native TASK026 boundary

The native base is audited from the repository's reviewed TASK026 selector and
its TASK-007 correlation contract:

* `tube_laminar_cwt@1.0.0` is the circular-tube, fully developed, laminar,
  constant-wall-temperature branch with `Re < 2300` and `Pr > 0.6`.
* `tube_laminar_chf@1.0.0` is the corresponding circular-tube, fully
  developed, laminar, constant-heat-flux branch with `Re < 2300` and
  `Pr > 0.6`.
* `tube_turbulent_gnielinski@1.0.0` is the circular-tube turbulent branch
  selected by the R8 implementation for `3000 <= Re <= 5e6` and
  `0.5 <= Pr <= 2000`. Its implementation uses the inherited Petukhov
  friction relation and Gnielinski Nusselt relation. The source contract's
  earlier regime summary describes a conservative transition region through
  `Re <= 10000`; this receipt does not resolve or change that historical
  selector/document discrepancy.
* The native base uses the tube inside diameter as its characteristic length.
  The current production input has no roughness correction, no implemented
  thermal developing-flow correction and no length-based wall-property
  extension. Those omissions are not silently filled by this receipt.
* The laminar branches declare constant-wall-temperature or constant-heat-flux
  boundaries. The turbulent branch declares both. Heating/cooling is listed
  as both in the source metadata, but the current selector has no active
  wall-property branch.
* Native properties are located on the supplied bulk-property input used by
  `compute_single_phase`; `wall_temperature_k` and `wall_viscosity_pa_s` are
  optional carriers in the broader correlation model, not an active TASK026
  wall-correction authority.
* The native definitions explicitly set `requires_wall_viscosity=False`, and
  the TASK-007 wall-property policy says that no viscosity correction is
  implemented. No neutral `factor=1` is an active correction.

The exact repository boundary is:

| Native item | Location | Resolution treatment |
| --- | --- | --- |
| Selector and regime dispatch | `src/hexagent/exchangers/shell_tube/tube_side_thermal/nusselt_selector.py` | Reused unchanged as the target base; no wall correction added |
| Single-phase assembly | `src/hexagent/exchangers/shell_tube/tube_side_thermal/single_phase.py` | Reused unchanged; no wall state is consumed |
| Correlation metadata and equation objects | `src/hexagent/correlations/tube.py` | Reused unchanged; C1/C2/C3 remain native identities |
| Frozen correlation contract | `docs/tasks/TASK-007-tube-annulus-correlations.md` and `docs/CORRELATIONS.md` | Explicit no-wall-correction boundary retained |
| TASK026 historical design reference | `/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md` in legacy code references | Not a repository source artifact; no unverified content is promoted |

```ini
NATIVE_TUBE_CORRELATION_ID=tube_turbulent_gnielinski@1.0.0; tube_laminar_cwt@1.0.0; tube_laminar_chf@1.0.0
NATIVE_TUBE_CORRELATION_CHANGED=false
LEGACY_TUBE_RESULT_SEMANTICS_CHANGED=false
NATIVE_WALL_CORRECTION_IMPLEMENTED=false
LEGACY_WALL_CORRECTION_REUSED=false
```

The proposed correction would be an extension around the exact native base;
it is not permitted to replace the native correlation, change its coefficients
or widen its envelope.

## 3. Source acquisition and disposition

The audit distinguishes discovery, source verification and transferability.
No candidate reaches `PROPOSED_AUTHORITY` because the exact transfer package is
incomplete.

| Candidate | Source class and access | What was actually available | Disposition |
| --- | --- | --- | --- |
| `SIEDER-TATE-1936` | Primary publication, DOI `10.1021/ie50324a027`; publisher access path is recorded in the registry | Bibliographic identity and discovery of a wall/bulk-viscosity treatment; the publisher full text/equation pages and a rights-cleared review copy were not acquired for this repository | `CANDIDATE`; `SIEDER_TATE_AUTHORITY=INSUFFICIENT` |
| `GONCALVES-2019` | Public author/university copy, copyrighted; registry source `GONCALVES` | Reviewed sections provide their selected base tube relations and a separate laminar Sieder/Tate relation; they do not establish a transfer rule to the native TASK026 turbulent selector | `VERIFIED_SOURCE` for its stated equations only; not transferable |
| `SANDIA-SAND2016-4159` | Official public report, registry source `SANDIA` | Section 4.1.203 documents a Gnielinski film-gradient correction interface, but the cited location does not provide the complete equation, coefficients, domains and TASK026 combination rule required here | `VERIFIED_SOURCE` for interface evidence only; not transferable |
| `MARTIN-GNIELINSKI-2000` | Author copy, copyrighted; recorded by the existing wall proposal | External crossflow normalization with its own state and branch semantics; it is not an internal circular-tube extension and no Bell or TASK026 transfer is shown | Discovery/cross-check only; rejected for this target |
| `REPO-TUBE` | Existing reviewed repository authority | Exact native C1/C2/C3 identities, selector, domains and explicit no-wall-correction policy | `REVIEWED_AUTHORITY` as unchanged base only |

The ACS publisher path is retained as a source locator, not as evidence that
the inaccessible full text may be copied. A third-party scan or a search
snippet cannot supply equation, rights, domain or transfer authority. The
official Sandia report is usable as a public interface description, but an
interface feature is not a numerical correction permission.

No source was selected:

```ini
SELECTED_CORRECTION_SOURCE_ID=NONE
SELECTED_CORRECTION_SOURCE_CLASS=NONE
SELECTED_CORRECTION_SOURCE_REVISION=NONE
SELECTED_CORRECTION_SOURCE_LOCATION=NONE
SELECTED_CORRECTION_SOURCE_RIGHTS=NONE
SIEDER_TATE_TRANSFER_AUTHORITY=UNAVAILABLE
```

## 4. Transferability matrix

The following matrix is the decision record for the active tube correction.
`UNBOUND` is an evidence result, not a proposed default. The native base
identity being known does not make an external correction transferable.

| Transfer dimension | Required target meaning | Evidence at this revision | Result |
| --- | --- | --- | --- |
| Source correlation family | Exact source family and revision | Sieder–Tate equation/domain not lawfully acquired; Sandia is interface-only | `UNBOUND` |
| Target TASK026 family | Exact C1/C2/C3 branch and version | Native IDs are known and unchanged | `BOUND_FOR_TARGET_ONLY` |
| Internal/external flow | Same internal circular-tube physical problem | Sieder–Tate discovery is internal-tube related; no complete transfer package; Martin is external crossflow | `UNBOUND` |
| Laminar/turbulent/transitional regime | Branch-specific applicability | Candidate source domains and branch mapping are incomplete; TASK026 transition remains blocked | `UNBOUND` |
| Reynolds domain | Exact lower/upper limits and inclusivity | No lawfully reviewed correction limits | `UNBOUND` |
| Prandtl domain | Exact limits and basis | No lawfully reviewed correction limits | `UNBOUND` |
| Wall/bulk property ratio | Exact ratio, orientation and range | No complete equation/ratio authority acquired | `UNBOUND` |
| Fluid family | Liquids/Newtonian/water or broader family | Candidate data and transfer scope not complete; no water-only transfer proof | `UNBOUND` |
| Geometry | Circular tube, diameter basis and roughness | Native geometry is circular tube/inside diameter; candidate transfer domain absent | `UNBOUND` |
| Roughness | Smooth/rough condition and bound | Native path has no active roughness variable; candidate scope absent | `UNBOUND` |
| Length/development | Fully developed or entrance/developing applicability | Native developing correction is not implemented; candidate limits absent | `UNBOUND` |
| Thermal boundary | CWT/CHF and assumptions | Native branches are known; candidate combination and boundary applicability absent | `UNBOUND` |
| Heating branch | Fluid being heated | No complete candidate branch rule bound | `UNBOUND` |
| Cooling branch | Fluid being cooled | No complete candidate branch rule bound | `UNBOUND` |
| Bulk state | Exact fluid state used for bulk viscosity | TASK172 names a located bulk state, but candidate source definition is absent | `UNBOUND` |
| Wall-fluid state | Exact fluid-facing wall state used for wall viscosity | Candidate source definition is absent | `UNBOUND` |
| Metal-vs-fluid surface | Whether metal surface may stand in for fluid wall state | No source supports that alias for this correction | `UNBOUND` |
| Base combination rule | Replace, multiply, or otherwise combine with TASK026 | No source-defined compatible rule | `UNBOUND` |
| Output identity | Corrected Nu/h and canonical/provenance binding | No correction identity or output authority issued | `UNBOUND` |
| Source rights | Lawful review/use/redistribution boundary | Sieder–Tate full text not acquired; other sources have limited rights/scope | `UNBOUND` |
| Transfer evidence | Direct validation or explicit source compatibility | No direct transfer evidence | `UNBOUND` |

Since at least one key field is `UNBOUND`—in fact source, equation, domains,
state mapping and combination rule are all incomplete—`TRANSFERABILITY_ESTABLISHED`
is false. The matrix rejects:

* an external crossflow correction transferred to internal tube flow;
* a generic handbook or remembered factor applied to Gnielinski;
* a `factor=1` omission presented as an active correction;
* the TASK034 shell pressure-drop wall term reused for tube heat transfer;
* a metal surface temperature silently substituted for fluid-facing wall
  temperature;
* a clean-surface node alias used to invent a missing correlation state.

## 5. Wall-state dependency

The existing wall-state proposal distinguishes:

* `TUBE_FLUID_BULK_STATE` — located fluid bulk state;
* `TUBE_FLUID_WALL_INTERFACE` — fluid-facing tube wall state;
* `TUBE_METAL_INNER_SURFACE` — solid-metal surface state.

If a future source requires viscosity at the fluid wall, the correction must
consume `TUBE_FLUID_WALL_INTERFACE`. The clean-surface alias to
`TUBE_METAL_INNER_SURFACE` is a reviewed passive-network surface identity; it
does not by itself prove that a source's wall-fluid property evaluation may use
the metal temperature. No candidate source in this audit provides that exact
mapping.

```ini
TUBE_CORRECTION_BULK_STATE_ID=UNBOUND
TUBE_CORRECTION_WALL_STATE_ID=UNBOUND
WALL_STATE_MAPPING_AUTHORITY_BOUND=false
WALL_STATE_MAPPING_REQUIRED=TUBE_FLUID_BULK_STATE_TO_TUBE_FLUID_WALL_INTERFACE
METAL_TEMPERATURE_SUBSTITUTION_AUTHORIZED=false
```

The source package needed to bind these fields must define the bulk and wall
temperature/property locations, state producers, physical support, and how
those states are combined with the exact TASK026 base. That package is absent;
no wall-temperature solve is started here.

## 6. Required authority shape and fail-closed decision

A future transferable proposal must bind every field below in one canonical
source record. This receipt intentionally leaves them unbound:

```ini
AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
AUTHORITY_VERSION=r1
COMPONENT_SCOPE=TUBE_SIDE_FILM
BASE_CORRELATION_AUTHORITY_ID=UNBOUND
CORRECTION_EQUATION=UNBOUND
CORRECTION_SOURCE_ID=UNBOUND
SOURCE_REVISION=UNBOUND
SOURCE_LOCATION=UNBOUND
SOURCE_RIGHTS=UNBOUND
RE_DOMAIN=UNBOUND
PR_DOMAIN=UNBOUND
PROPERTY_RATIO_DOMAIN=UNBOUND
FLUID_FAMILY_DOMAIN=UNBOUND
GEOMETRY_DOMAIN=UNBOUND
THERMAL_BOUNDARY_DOMAIN=UNBOUND
HEATING_BRANCH=UNBOUND
COOLING_BRANCH=UNBOUND
BULK_STATE_DEFINITION=UNBOUND
WALL_STATE_DEFINITION=UNBOUND
COMBINATION_RULE=UNBOUND
OUT_OF_DOMAIN_POLICY=BLOCKED
EXTRAPOLATION_POLICY=FORBIDDEN
```

The identity preimage must include the authority/version, exact native base
identity, source revision/location/rights, equation and all coefficients,
every applicability domain, state mapping, combination rule, provenance,
case/configuration/geometry binding and lifecycle status. A change to any of
those fields must create a new identity. An ID/hash-only record without the
equation and required body is not admission.

The following are mandatory blockers:

```text
missing source or lawful review copy
missing exact correction equation
missing coefficient or exponent
missing Re, Pr or property-ratio domain
missing fluid, geometry, roughness or development domain
missing heating/cooling semantics
missing bulk or fluid-facing wall state definition
missing exact TASK026 base binding
missing source-defined combination rule
source/hash, authority/hash or state mapping mismatch
out-of-domain or extrapolation
caller assertion, hidden default or legacy correction reuse
```

No numeric qualification is performed. There is no selected equation,
coefficient, exponent, correction factor, wall iteration, root solve,
relaxation, residual threshold or numerical tolerance in this receipt.

## 7. Resolution

The native TASK026 base is sufficiently identified to preserve it, but no
source-qualified active wall-property correction is transferable at this
revision. The result is therefore:

```ini
CORRECTION_EQUATION_BOUND=false
CORRECTION_COEFFICIENTS_EXPONENTS_BOUND=false
RE_DOMAIN_BOUND=false
PR_DOMAIN_BOUND=false
PROPERTY_RATIO_DOMAIN_BOUND=false
FLUID_FAMILY_DOMAIN_BOUND=false
GEOMETRY_DOMAIN_BOUND=false
THERMAL_BOUNDARY_DOMAIN_BOUND=false
HEATING_COOLING_BRANCHES_BOUND=false
BASE_CORRELATION_BINDING_BOUND=false
COMBINATION_RULE_BOUND=false
TRANSFERABILITY_ESTABLISHED=false
OUT_OF_DOMAIN_POLICY=BLOCKED
EXTRAPOLATION_POLICY=FORBIDDEN
TUBE_WALL_CORRECTION_RESOLUTION_RESULT=BLOCKED
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

This is not a claim that no wall-property correlation exists in the
literature. It is a bounded finding that the current repository does not hold
the lawful, exact and transfer-reviewed package required to extend its native
TASK026 path. The next step must supply or independently review such a package;
it must not lower the evidence bar or change TASK026 in this PR.

## 8. Governance and next gate

The resolution changes no historical payload, source identity, material layer,
shell correction, numerical profile, dependency, production code or TASK172
implementation state. The remaining blocker ledger is unchanged. The
deterministic next gate is an external/independent decision about this bounded
resolution or a new complete primary transfer package; no downstream work is
authorized by this receipt.

```ini
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
TASK172_IMPLEMENTATION_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=REVIEW_TUBE_WALL_CORRECTION_BLOCKER_OR_PROVIDE_COMPLETE_PRIMARY_TRANSFER_AUTHORITY
NO_STEP_IMPLIES_THE_NEXT=true
```

## 9. Evidence references

* [TASK-007 tube and annulus correlation contract](TASK-007-tube-annulus-correlations.md)
* [shared correlation summary](../CORRELATIONS.md)
* [TASK172 wall and numerical proposals](TASK-172-v0.7-wall-numerical-proposals-r1.md)
* [TASK172 physical authority semantic audit](TASK-172-v0.7-physical-authority-semantic-source-r5.md)
* [TASK172 authority registry](TASK-172-v0.7-authority-registry-r1.json)
* [Sieder and Tate bibliographic source](https://doi.org/10.1021/ie50324a027)
* [official Sandia SAND2016-4159 report](https://www.osti.gov/servlets/purl/1262728)
* [Goncalves author copy](https://www.ou.edu/class/che-design/pub-papers/Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf)

The linked external material is recorded according to the existing rights
boundary. No external PDF is vendored, and no bibliographic or interface-only
record is promoted to `REVIEWED_AUTHORITY` for this active correction.
