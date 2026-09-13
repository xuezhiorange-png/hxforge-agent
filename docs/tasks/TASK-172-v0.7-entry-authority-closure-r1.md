# TASK172 R1 — property, wall and numerical entry review package

## 1. Decision and immutable boundary

```ini
TASK_ID=TASK172_V0_7_ENTRY_AUTHORITY_CLOSURE_R1
DOCUMENT_STATUS=PROPOSED_AUTHORITY_REVIEW_PENDING
BASE_MAIN_SHA=04d7aac8adcda13edd27d6c9511019a05ee08d96
SOURCE_CONFLICT_POLICY=FAIL_CLOSED
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
NEW_AUTHORITY_SELF_APPROVAL=false
IMPLEMENTATION_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

Tracking: [Issue #276](https://github.com/xuezhiorange-png/hxforge-agent/issues/276).
This is a documentation-only, bounded evidence audit of three entry blockers,
not a claim to have exhausted the literature. The audit was conducted on
2026-09-12. No new property runtime, wall solve, root solve, mesh refinement
engine, dependency or engineering test vector has been implemented by this task.
No fluid, numerical preset or Golden is approved.

The [registry](TASK-172-v0.7-authority-registry-r1.json) binds sources, access
results, immutable revisions, byte hashes, proposal identities and review gaps.
The [wall/numerical annex](TASK-172-v0.7-wall-numerical-proposals-r1.md) supplies
the other two required matrices. All new packages are PROPOSED_AUTHORITY;
VERIFIED_SOURCE means the specified pages were read, not applicability approved.
Only inherited, pinned repository contracts are REVIEWED_AUTHORITY, and only
within their historical scope. PARTIALLY_CLOSED denotes that inherited scope;
it does not grant new runtime admission. No entry blocker is CLOSED.

### Decision matrix

| Sub-package | State | Evidence available | Remaining decision |
| --- | --- | --- | --- |
| Water profile | PARTIALLY_CLOSED | Native DEF/fingerprint and snapshot contracts; official EOS/transport sources and checkpoint proposal | Joint admission/phase exclusion, backend qualification and independent review |
| Wall surfaces | PARTIALLY_CLOSED | TASK037 resistance/area authority; TASK171 located interfaces | Review two-sided network, film/fouling convention and local material applicability |
| Tube correction | OPEN | Native uncorrected correlation; lawful discovery and official software manual | Complete transferable equation/domain and base-correlation review |
| Shell correction | OPEN | Native Bell source; crossflow normalization source | Bell-compatible supplement and transferability review |
| Numerical profile | PARTIALLY_CLOSED | TASK171 residual bookkeeping and inherited canonical contract | Residual reduction, method qualification, error allocation and stopping criteria |
| Mesh convergence profile | PARTIALLY_CLOSED | TASK171 exact geometry/event invariants | Refinement estimator, comparison norm, termination/cap study and review |

### Exact remaining entry blockers

| Parent | Outstanding evidence/review IDs |
| --- | --- |
| PROP-PROFILE-REVIEW | WATER-DOMAIN-AND-PHASE-QUALIFICATION; WATER-BACKEND-CHECKPOINT-QUALIFICATION; WATER-PROFILE-INDEPENDENT-REVIEW |
| WALL-CORRELATION-AND-SURFACES | WALL-SURFACE-NETWORK-REVIEW; TUBE-WALL-CORRECTION-AUTHORITY; SHELL-WALL-CORRECTION-AUTHORITY |
| NUM-PROFILE-REVIEW | LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION; NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW; MESH-CONVERGENCE-QUALIFICATION |

Reviewers can approve/reject individual proposals without restarting the audit.
An approval must identify the proposal canonical hash, exact admitted domain,
evidence and reviewer; it cannot silently fill an UNBOUND field. TASK172 remains
unimplemented even if a future review accepts part of this package. TASK174,
TASK173 and TASK175 are not started or researched here.

## 2. Inherited TASK171 interface

[TASK171](TASK-171-v0.7-segmented-thermal-state-topology-engine.md) at the base
supplies topology, physical intervals, cell and wall IDs, state locations and
COMPUTED_NOT_ASSESSED conservation bookkeeping. Its reviewed entry profile
remains steady, single-phase, Newtonian, fixed-tubesheet, E-shell, 1x1
straight-through, countercurrent with explicit geometry/path/area/event mapping.
Hot/cold assignment is independent of tube/shell assignment.

Native axial endpoints and every TASK024 baffle-plane center delimit physical
intervals. Mesh refinement is confined to those intervals; it cannot insert or
erase a baffle, window or end event. TASK172 cannot relax this condition, add
physical cuts, reverse paths or substitute array ordering for connectivity.
Property snapshots must bind the native topology/result identity, cell or
face identity, physical support, stream, side, location and profile hash.
CELL_MEAN is not an arithmetic average by default. COMPARTMENT_MIXED has no
producer without separate mixing authority. A wall state does not resolve
Bell compartment mixing. N=1 legacy equivalence remains a release bridge,
not an assumption about this new constitutive model.

## 3. Property proposal and matrix

Candidate: `V07-T172-WATER-PROPERTY-PROFILE-R1`, version v1.
This requalifies `V07-WATER-HEOS8-QUALIFICATION-R3` and the separate
`V07-WATER-POINT1MPA-CHECK-R3` from the
[R3 registry](TASK-170-v0.7-authority-registry-r3.json). Their historical hashes
and review states are unchanged; this package creates a distinct proposal,
not an approval or an in-place revision of those records.
Initial candidate scope is **pure ordinary water, HEOS 8.0.0, stable liquid**;
both streams may reference this same profile but retain distinct states.
This narrows scope, not approval: SUPPORTED_FLUID_PROFILE=false until reviewed
qualification exists. Glycol/water, mixtures, oils, refrigerants, salts and
other backend fluids remain unsupported by this proposal.

```ini
COOLPROP_CALL_SUCCESS_IS_AUTHORITY=false
BACKEND_CAPABILITY_IS_SUPPORTED_PROFILE=false
GLYCOL_WATER_SUPPORTED=false
COMBINED_UNCERTAINTY=UNBOUND
```

| Requirement | Source / review state | Proposed production rule | Unresolved blocker |
| --- | --- | --- | --- |
| Fluid/composition | CP-WATER; VERIFIED_SOURCE | Canonical Water, pure ordinary substance, no composition override or INCOMP alias | Independent profile review |
| Backend/version | CP-WATER/CP-TRANSPORT/CP-LICENSE; VERIFIED_SOURCE | HEOS 8.0.0, commit `ae81610e7d23efc57f9d051c8e70a4d66e87537f`; bind actual binary/build fingerprint as well | Qualification receipt for installed builds |
| rho, cp, h | IAPWS95; VERIFIED_SOURCE | One EOS, same state and profile; no per-property table substitution | Domain and checkpoint review |
| mu | IAPWS-MU; VERIFIED_SOURCE | R12-08 formulation using the same EOS density; enforce Eq9 domain | Backend reproduction and phase qualification |
| k | IAPWS-K; VERIFIED_SOURCE | R15-11 general formulation, same EOS/transport state; enforce Eq14 domain | Backend reproduction and phase qualification |
| Pr | Native consistent snapshot / project proposal | Derive cp*mu/k in consistent SI units from that one snapshot only | Future precision policy, not a second property source |
| T/P/phase | IAPWS95 §5; MU §2.4; K §2.4 | State-dependent intersection, not backend maxima | Certified stable-liquid and exclusion predicates |
| Reference | IAPWS95 §3; REPO-PROP | DEF plus native reference fingerprint, no in-solve mutation | Check DEF reproduction and state-purity during qualification |
| Uncertainty | EOS §6; transport §2.5; IAPWS-H | Preserve property-, state-, path- and convention-specific evidence | Combined propagation UNBOUND |
| Verification | IAPWS official check tables, registry checkpoint IDs | Separate formulation reproduction, cross-check and admission tests | No automatic tolerance from printed digits |
| Lifecycle | Project governance proposal | Missing/unreviewed profile or identity mismatch blocks before evaluation | Independent approval and later implementation authorization |

### 3.1 Domain is an intersection, not a false liquid rectangle

The source facts are deliberately compact; the registry points to full pages.
[IAPWS95](https://iapws.org/technical-guidance/release/IAPWS-95.download)
§5 bounds stable-fluid validity by melting and the stated upper region; §6
provides state-dependent uncertainty, not statistical confidence. §3 fixes
the saturated-triple-point energy/entropy convention. Its §7/Table7 verifies
single-phase quantities; Table8 is a saturation check, not liquid admission.

[Viscosity](https://iapws.org/technical-guidance/release/viscosity.download)
Eq9 and [conductivity](https://iapws.org/technical-guidance/release/ThCond.download)
Eq14 have different pressure-dependent upper-temperature branches and a melting
boundary. Their extrapolation remarks do not authorize extrapolation here.
Both §2.5 uncertainty conventions are retained rather than collapsed into a
global percentage. Viscosity program verification is **§4/Table4**, not §2.8;
the latter discusses simplified use. This corrects the location for this new
package without rewriting R3 history.

Proposed state-admission predicate, with no implemented evaluator:

1. Exact reviewed profile/backend/reference identity and pure composition.
2. IAPWS95 stable-fluid validity AND MU Eq9 AND K Eq14 AND qualified backend
   implementation domain.
3. Independently qualified stable-liquid phase: exclude solid, saturated,
   two-phase, vapor, metastable, critical and supercritical states. Never impose
   a liquid phase on an otherwise inadmissible state to make a call succeed.
4. Profile-specific critical-neighborhood and phase-boundary exclusion rule.
   Its quantitative margin/classifier certification is UNBOUND. Until it is
   bound, this proposal admits **no production state**, not all states outside
   an undefined neighborhood. A diagnostic backend phase string is insufficient
   proof against metastability/solid regions.
5. Finite, mutually consistent properties; no partial snapshot or silent fallback.

T_min/T_max/P_min/P_max are **UNBOUND production scalars** in the registry.
The source's piecewise predicates are located, but neither a rectangular
safety envelope nor near-critical margin is invented. This is an explicit
incomplete state-dependent profile proposal (option B), not a complete water
admission claim. The next review needs a certified domain/exclusion map, not
another search for the EOS itself. Backend `Water.json` advertises a wider
temperature ceiling than the source's normal stable-fluid domain; it cannot
override it. Branch boundaries, including source-specific triple-point
conventions, must retain their own provenance; no silent constant unification.

### 3.2 Reference state and snapshot consistency

The existing provider's `_force_def_reference_state` explicitly restores DEF
under a lock during construction; `_verify_configuration` checks it thereafter.
This is an observed legacy behavior, **not** a TASK172 authorization to call
`set_reference_state` during solving. Inherit the reference-sensitive fingerprint
including version/git revision and native probe values; bind it as an opaque
native identity, not as a newly invented full-backend verification guarantee.
The old Tier-1 fluid list is not the new supported-fluid registry.

Proposed lifecycle: qualification records the controlled DEF baseline and build
identity; each evaluation verifies identity and unchanged configuration. Missing
baseline, probe failure or changed fingerprint fails closed. No hidden reset,
offset fit or cross-request mutation may repair a mismatch. Legacy initialization
is documented and unchanged; its suitability for the future isolated profile
must be explicitly approved. No new profile evaluation is performed in the
source audit; existing property calls in unchanged legacy regression tests are
separate regression evidence, not qualification of this proposed profile.

One located state owns rho/cp/h/mu/k, with profile hash, composition, reference,
backend and independent T/P inputs. No interpolation, averaging, constant-cp
substitution or mixing rule is implied. [AN1](https://iapws.org/public/documents/x2LDq/Advise1.pdf)
distinguishes absolute enthalpy uncertainty from uncertainty of a difference
between particular states. Do not sum absolute h errors or automatically apply
RSS to a small exchanger duty. Backend reproduction and numerical evaluation
errors remain separate from formulation uncertainties.

### 3.3 Future qualification plan (not executed, not Golden)

The literal **independent source** checkpoints in the registry were visually
checked against the PDF pages. They are proposed reference data, not approved
test tolerances or HXForge-generated expected values.

| Check ID | Source and purpose | Required future observation |
| --- | --- | --- |
| WATER-EOS-T300-RHO996556 | IAPWS95 Table7 first row | rho/T input, independently tabulated pressure; explicitly handle source low-pressure cancellation caveat; this is not a cp checkpoint |
| WATER-MU-T298-RHO998 | R12-08 §4/Table4 | Viscosity at tabulated density, matching source critical-enhancement convention; do not silently disable a backend term |
| WATER-K-T298-RHO998 | R15-11 §2.8/Table4 | Conductivity with the source's stated enhancement condition |
| WATER-LIQUID-T298-P01 | SR6-08 Table8, 298.15 K column | rho/cp/mu/k cross-check; approximate supplementary equation is NOT identical HEOS oracle; separately qualify h from the source's g and s relation |
| WATER-REFERENCE-DEF | IAPWS95 §3 and native fingerprint | Reference convention, locked version/build, unchanged fingerprint and compatible enthalpy differences |
| WATER-DOMAIN-NEGATIVE | Source predicates plus reviewed exclusion map | Saturation, metastable, solid, critical, out-of-range, wrong composition and fingerprint change must fail admission |

[SR6-08](https://iapws.org/technical-guidance/release/LiquidWater.download)
Table8 also contains 260 K and 375 K at 0.1 MPa: these are not positive
stable-liquid admission fixtures. Printed precision exceeds physical accuracy.
Its pressure-specific approximation cannot qualify the full pressure-varying
profile. The 298.15 K column is a candidate cross-check only. The h relation
is independently source-defined, but numerical h/Delta-h expectations and their
acceptance bands remain to be approved; no solver-produced oracle fills them.

Future qualification must bind source bytes/units, exact input type, independent
expected value, equation variant, source uncertainty, implementation error
allocation, runtime version/build and reference fingerprint. Compare both
supported Python runtimes with the same profile. Round-trip consistency is
useful but not independent accuracy evidence. Thresholds remain UNBOUND until
precision/domain review; no default approximate-equality tolerance is allowed.

## 4. Review and verification boundary

The registry contains source-role distinctions: inherited repository authority,
verified primary source, verified official implementation metadata, and
discovery-only unavailable full text. Readable code is implementation mapping,
not independent engineering applicability. No downloaded publication is vendored.
Public access is not assumed to grant redistribution rights. Inaccessible ACS
full text is recorded as such; no snippet supplies a coefficient. The PDF review
used original-page rendering for domains, tables and ambiguous equation layout.

Local validation checks JSON/schema-required fields, unique IDs, source binding,
canonical hashes, relative links, documentation-only diff and whitespace;
repository Ruff/format and final regression precede publication. Exact final
PR-head CI evidence belongs in the Draft PR receipt, avoiding a self-referential
head hash in this document. Green CI does not approve the package. TASK170/171
historical files, production code, tests, dependencies and Golden expectations
remain unchanged. A reviewer must explicitly resolve every outstanding row;
receipt completeness alone is not TASK172 entry completion.
