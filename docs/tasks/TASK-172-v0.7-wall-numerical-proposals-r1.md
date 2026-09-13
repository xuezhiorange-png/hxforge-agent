# TASK172 R1 — wall and numerical proposals

Companion to the [entry package](TASK-172-v0.7-entry-authority-closure-r1.md)
and [source registry](TASK-172-v0.7-authority-registry-r1.json).
All new rules below are **PROPOSED_AUTHORITY**, pending independent review.
No equation is implemented and no numerical parameter is selected.

## 1. Wall source/compatibility matrix

| Surface/correction | Source | Base correlation | Domain | Heating/cooling | Wall-state definition | State / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| Cylindrical resistance and areas | REPO-WALL; DOE HT-02 Eqs2-7/2-8/2-10 inherited by TASK037 | Exact cylindrical resistance, not a film correlation | Native area/material/conductivity/fouling authorities | Signed heat transfer; no new branch coefficient | Inner and outer metal area bases distinct | Inherited REVIEWED_AUTHORITY only; no two-surface solve supplied |
| Two-sided surface network | V07-T172-WALL-SURFACE-STATE-R1; REPO-WALL/REPO-TOPOLOGY | Resistance continuity, with supplied qualified films | TASK171 topology; passive radial wall; approved constant material k and local applicability | q positive HOT to COLD, side assignment explicit | Bulk, fluid-facing, metal inner/outer, and fouling contact nodes distinct | PROPOSED_AUTHORITY; WALL-SURFACE-NETWORK-REVIEW |
| Tube active property correction | V07-T172-TUBE-WALL-CORRECTION-R1; REPO-TUBE, SIEDER-TATE, SANDIA | Native TASK026 Gnielinski/laminar contract unchanged | New Re/Pr/ratio/geometry domain UNBOUND | Both branches UNBOUND | Tube fluid-facing boundary, not automatically metal | PROPOSED_AUTHORITY specification only; numerical authority OPEN |
| Shell active property correction | V07-T172-SHELL-WALL-CORRECTION-R1; REPO-BELL, GONCALVES, MARTIN | Native TASK166 Bell unchanged | Transferable Bell Re/Pr/ratio/layout domain UNBOUND | Transferable heating/cooling branches UNBOUND | Shell fluid-facing boundary, not automatically outer metal | PROPOSED_AUTHORITY specification only; numerical authority OPEN |

### 1.1 What was actually verified

TASK037 `schema.py`, `authority.py` and `engineering.py` at the pinned base
bind `R3_FROZEN`, review comment 5461369330, native public inside area and
the cylindrical outside/inside transform. Material conductivity is tied to
material ID, evaluation temperature/context and applicability authority hash.
It is **not** evidence that one k value is valid at every future segment state.
Fouling is source-bound on its respective area basis; no anonymous zero is
authorized. These inherited semantics are retained, not replaced.

```ini
TASK037_PROVIDES_TWO_SURFACE_WALL_TEMPERATURE_SOLUTION=false
TASK037_PROVIDES_VISCOSITY_CORRECTION=false
GNIELINSKI_WALL_VISCOSITY_EXTENSION=BLOCKED
BELL_WALL_VISCOSITY_EXTENSION=BLOCKED
```

The admitted [Goncalves source](https://www.ou.edu/class/che-design/pub-papers/Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf)
§2.1 Eqs36–39 and §2.2 Eq75 have no requested active wall-property multiplier.
Eq77 is a different laminar relation, not permission to augment Eq75. Native
TASK166 supplements retain their existing roles; no supplement is silently
repurposed. This is an audit of the selected contract, not a claim that no
Bell variant anywhere contains a wall correction.

[Sieder and Tate, 1936](https://doi.org/10.1021/ie50324a027) is bibliographically
identified; the publisher PDF returned HTTP403 in this audit. No lawful full
equation/domain copy was obtained. No remembered exponent or coefficient is
transcribed. [Sandia SAND2016-4159](https://www.osti.gov/servlets/purl/1262728),
§4.1.203 p113, documents a Gnielinski film-gradient correction interface but
does not give the required complete numerical/domain authority there. It is
a verified official implementation description, not approval of transfer to
TASK026. A library/manual feature name cannot close this blocker.

[Martin/Gnielinski 2000](https://publikationen.bibliothek.kit.edu/1000034867/2579184),
Appendix9.2 p1160 EqA13, normalizes external crossflow HTC measurements with
a property correction; it uses a bulk arithmetic inlet/outlet mean and an
outer-surface wall state. It is not an internal-pipe extension or a demonstrated
Bell-compatible supplement. Its different liquid ratio branches are visible
in the source, but no branch number is adopted without transfer/domain review.
The KIT author copy is copyrighted, not assumed openly licensed.

### 1.2 Surface-state proposal

**SOURCE-DERIVED PHYSICS:** inherited cylindrical resistance and film heat-flow
relation; steady energy continuity. **PROJECT INTERFACE/GOVERNANCE:** named
surface identities, q orientation, ownership and missing-authority behavior.
**IMPLEMENTATION DESIGN DEFERRED:** local film/state evaluation, mapping of
bulk states to constitutive states, numerical solve and quantization.

Each node binds state ID, TASK171 wall interface, physical support, stream/side
where applicable, area basis, temperature producer and material/fouling source.
The proposed network, ordered tube bulk to shell bulk, is:

| Node | Meaning and admission condition |
| --- | --- |
| TUBE_FLUID_BULK_STATE | Located fluid state; no implicit cell-average closure |
| TUBE_FLUID_WALL_INTERFACE | Fluid-facing boundary used by an approved tube correlation |
| TUBE_FOULING_METAL_INTERFACE | Required only with explicitly admitted inner fouling; contact assumption must be bound |
| TUBE_METAL_INNER_SURFACE | Actual metal inner temperature, inside area basis |
| TUBE_METAL_OUTER_SURFACE | Actual metal outer temperature, outside area basis |
| SHELL_FOULING_METAL_INTERFACE | Required only with explicitly admitted outer fouling |
| SHELL_FLUID_WALL_INTERFACE | Fluid-facing boundary used by an approved shell correlation |
| SHELL_FLUID_BULK_STATE | Located shell fluid state; not automatically a mixed compartment |

For a clean interface, fluid-facing and metal nodes may be explicitly aliased
only by a reviewed clean-surface authority. For fouled service, the fluid/fouling
and fouling/metal boundaries remain separate. The existing area-based fouling
resistance does not specify deposit thickness, roughness, contact resistance or
a changed flow area. Those cannot be inferred. If the intended correlation
needs such data, its applicability is BLOCKED. No new contact/lumped resistance
is inserted. Ideal thermal contact, where chosen, requires an explicit reviewed
node-alias assumption rather than a concealed numerical equality.

For proposal review, let s=+1 when tube is hot, and s=-1 when shell is hot.
Let Q_ts=s*q, with q retaining TASK171's HOT-to-COLD sign. For a passive series
branch, propose `T_left - T_right = Q_ts * R_branch` in tube-to-shell order;
the same heat rate traverses every branch. Film R uses the film's own area;
area-normalized fouling R uses its declared inside/outside area. The inherited
cylindrical metal R is not a thin-wall approximation. This is an algebraic
network proposal derived from the inherited laws, not an approved local solver.
Zero and reversed heat require signed consistent handling, never abs(q).

With qualified positive branch resistances and fixed supplied bulk states,
the passive network places surfaces between the bulks; use this only after
review of the no-source/no-storage/radial assumptions. It does not establish
monotonicity of the nonlinear property/correlation residual or justify Brent.
Temperature-dependent k_wall is not admitted. Constant k must have a source,
evaluation basis and applicable local temperature domain; an evaluation point
alone is not that domain. Extending the whole-area TASK037 result to local
supports needs a reviewed mapping and cannot use whole resistance/cell count.

### 1.3 Correction proposal admission fields

Each tube/shell record separately requires exact equation/version, all
coefficients and exponents, Re/Pr and wall-to-bulk ratio domain, fluid family,
geometry/roughness/length constraints, thermal boundary conditions, bulk
location definition, wall-fluid location definition, heating/cooling branches,
base correlation identity and combination rule. These are individually UNBOUND
in the registry where not established. Reading an alternative formula is not
permission to widen the native correlation domain or change legacy results.
`factor=1` is not active correction. Missing tube or shell authority prevents
full TASK172 closure even when surface bookkeeping is reviewable.

## 2. Numerical profile and ownership matrix

`V07-T172-NUMERICAL-PROFILE-R1` is a non-executable method/decision specification.
TASK172 owns local constitutive state/property/wall coupling and its residual
interfaces. TASK173 owns assembling and solving a full Rating boundary problem,
Sizing, candidates and recommendation; no level below creates that orchestration.

| Level / owner | Unknowns / inputs | Residual | Proposed method | Bounds | Initialization | Convergence | Failures / review |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 supplied-state property / TASK172 | Given located T/P and profile; derived rho/cp/h/mu/k | Identity/domain and any qualified consistency residual | Direct backend evaluation, not a new HX nonlinear solve; backend internals remain backend-owned | Approved phase/domain predicate | Exactly supplied state, no guessed state | Snapshot validity distinct from iterative convergence; reproduction tolerance UNBOUND | Property/profile/fingerprint failure; PROPOSED |
| L2a supplied-coefficient wall / TASK172 | Given bulk states, areas, film coefficients, material/fouling; surface temperatures and q | Branch heat-rate continuity | Direct series evaluation only after network assumptions approved | Passive bulk-temperature hull intersected with approved fluid/material domains | Direct evaluation, no iterate | Residual reported; acceptance policy UNBOUND | Invalid resistance/area/domain/surface reversal; PROPOSED |
| L2b property/correction wall coupling / TASK172 | Wall-fluid temperatures, coefficients and property states | Common heat rate versus each branch's constitutive heat rate | Scalar bracket method only after scalar reduction/continuity/sign-change proof; otherwise METHOD_UNBOUND | Every trial must remain in all property/material/correlation domains, including intermediate states | Deterministic domain endpoints if proven valid and bracketed; else NO_BRACKET, not random search | Wall/property residual norms and thresholds UNBOUND | No bracket, nonfinite, domain excursion, stagnation, oscillation, exhaustion; PROPOSED |
| L3 cell constitutive coupling / TASK172 | Explicit face states and wall mappings, unresolved cell mean/reconstruction | Signed hot/cold enthalpy residual and local heat-transfer residual | METHOD_UNBOUND until state reconstruction/coupling reviewed; do not assume scalar | TASK171 support plus qualified states | Only same-solve supplied/previous state under reviewed ordering | Local tolerance/scale UNBOUND | Missing reconstruction, invalid map or closure; PROPOSED |
| L4 countercurrent boundary / TASK173; TASK172 interface only | Exchanger terminal unknowns with opposing inlet boundaries | Global duty and outlet/boundary residual | Exchanger algorithm DEFERRED; no Brent assumption | Explicit topology and physical/domain bounds | No Golden outlet or previous user's solution as seed | Global acceptance belongs to TASK173 authority | Interface definition only; no full Rating authorized |

### 2.1 Method source versus engineering authorization

[Brent's author-hosted book](https://maths-people.anu.edu.au/brent/pd/rpb011i.pdf),
Chapter4 §§1–3 pp47–53 (scanned spreads), was read for sign-changing bracketing,
interpolation safeguards, bisection and rounding qualifications. The chapter's
tolerance analysis distinguishes error in a computed function from the intended
mathematical function. No book example tolerance or iteration number is an
HXForge preset. Full chapter implementation is not transcribed or claimed
reviewed. Public author hosting is not an inferred redistribution license.

Before selecting a scalar method, a reviewer must approve the actual residual,
its scalar reduction, continuity on the entire valid interval, bracket evidence,
root-selection/uniqueness policy and finite-precision safeguards. A sign change
across a phase boundary or singularity is not a valid bracket. Bisection is a
safeguard inside a valid bracket, not fallback for missing physical authority.
Vector residuals need their own method review. No SciPy default is imported.

Deterministic initialization may use only supplied physical states, reviewed
domain bounds and earlier states within the same solve. No hidden cache seed,
random seed, reference outlet or unapproved extrapolation. If a bracketed profile
is later selected, endpoint ordering, update ordering and canonical state IDs
must be fixed; this proposal does not guess a search grid or relaxation factor.

### 2.2 Residuals and distinct statuses

| Residual | Location/units and owner |
| --- | --- |
| Property-state | Exact identity/domain checks plus any approved EOS consistency comparison with named input/output units; TASK172, not a generic dimensionless error |
| Wall heat-flux continuity | Compare branch heat **rates** in W; fluxes first use their own areas; TASK172 |
| Inner/outer wall temperature | Each distinct surface's update/residual in K; no collapse to one wall temperature; TASK172 |
| Segment heat transfer | Constitutive wall rate versus owned wall event, W; TASK172 |
| Hot/cold enthalpy | TASK171's signed m_dot*Delta-h minus owned q, W; TASK172 evaluates constitutive closure without changing bookkeeping |
| Global duty | Sum on explicit exchanger boundary, W and an approved scale; TASK173 |
| Boundary/outlet | Opposing inlet boundary compatibility and solved outlet state, K or J/kg explicitly; TASK173 |

The proposal requires separate WALL_ITERATION_STATUS, PROPERTY_COUPLING_STATUS,
MESH_CONVERGENCE_STATUS and ENERGY_CLOSURE_STATUS. Neither zero bookkeeping
residual nor a converged local iteration means engineering acceptance. Norms,
scales, zero-duty rules, absolute/relative bands and tolerances remain UNBOUND;
no runtime may evaluate a numeric PASS with these missing.

Nonfinite values, invalid properties, domain excursion, no bracket, surface
inconsistency and unmet resource caps fail closed immediately. Stagnation and
oscillation require recorded state/residual history; exact detection window,
progress measure and threshold remain UNBOUND and must be reviewed before
the algorithm is executable. Do not claim detection is implemented by listing
the failure name. Last iterates are diagnostics only, never a valid closure.

MAX_ITER/MAX_MESH, if later selected, are explicit resource/safety caps, not
proof of engineering accuracy. Reaching them without separately demonstrated
convergence is NOT_CONVERGED/BLOCKED. Local raw record caps inherited from
TASK171 likewise do not prove mesh adequacy. Under-relaxation is NOT_SELECTED;
no factor, maximum iteration count, temperature band or library default is set.

### 2.3 Error-budget review ledger

| Error contribution | Evidence / missing work | Combination rule |
| --- | --- | --- |
| Reference/data | Source precision and coverage convention, no exchanger Golden selected here | Keep per-observable identity; not automatically stochastic |
| Property formulation | IAPWS state/path-specific uncertainty | Propagation through actual qualified states needed |
| Correlation | Native domain plus missing active correction authority | Systematic model discrepancy is not random noise |
| Discretization | TASK171 mesh/hardware separation | Order, asymptotic regime and estimator NOT_ESTABLISHED |
| Iteration/root | Brent prerequisites and computed-function rounding caveat | Residual-to-output sensitivity and bracket error study required |
| Serialization/quantization | Shared canonical contract and native producer precision | Determine rounding floor/error propagation for new states |

Combined uncertainty is UNBOUND. No automatic RSS, arbitrary safety fraction,
or equation-reproduction tolerance reused as root tolerance. A later precision
study must show numerical error does not dominate the relevant accepted
engineering uncertainty, with documented sensitivity and margin. Missing active
correlation/domain authority prevents final allocation. Inherited v0.6 acceptance
ceilings remain unchanged and do not solve this missing numerical budget.

## 3. Mesh convergence proposal

`V07-T172-MESH-CONVERGENCE-PROFILE-R1` defines review obligations, not a
production refinement engine or default mesh.

Compare quantities on common **physical supports**, not cell list indices:
terminal enthalpies/temperatures, total wall duty, interval/interface duty sums,
wall-surface extrema and conservation residuals. Compare only quantities with
approved producers. TASK174 hydraulic outputs cannot be fabricated to complete
this comparison. Different meshes need explicit conservative intersection maps;
interpolation or averaging remains unapproved.

A future explicit refinement plan must identify each parent cell, ordered child
partition and mesh/source hash; children exactly cover the parent within the
same physical interval. No mandated doubling/default cell count is proposed.
Native endpoints/baffle boundaries, areas, wall/event identities and hardware
ownership remain immutable across the comparison. Coarsening across an event
boundary is rejected. A new mesh cannot create Bell event multiplicity or
divide whole-exchanger DP/corrections by cell count.

Termination requires separately approved comparison norm, precision-aware
criterion, refinement sequence and evidence of adequacy. These and maximum
refinement remain UNBOUND. Exhaustion or invalid state returns MESH_NOT_CONVERGED;
two similar runs alone do not establish asymptotic convergence. Actual mesh
rule/threshold approval is still an entry blocker, not something CI can supply.

## 4. Independent review checklist

- Check each proposal hash and exact source scope; distinguish inherited
  physics, new project interface choices and deferred implementation design.
- Approve/reject water domain/exclusion and checkpoint plan separately from
  software availability. No mixture or numerical tolerance is implied.
- Review wall-film/fouling contact locations, material temperature applicability
  and local area mapping; do not treat TASK037 resistance as a wall solver.
- Obtain full tube correction authority and an independently compatible shell
  supplement; do not transfer crossflow or pipe factors by name.
- Prove residual properties before choosing a solver; bind sensitivity/error
  study, distinct statuses, detection rules and resource-cap disposition.
- Review mesh comparisons without changing TASK171 physical intervals/events.
- Record approval identity/evidence explicitly. All current approved_by fields
  are null and approval_evidence arrays empty. Even subsequent source approval
  does not authorize implementation, Ready, Merge or downstream tasks.
