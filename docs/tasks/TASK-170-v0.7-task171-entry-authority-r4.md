# TASK170 R4 — TASK171 entry authority package

## 1. Review boundary and candidate registry

```ini
TASK_ID=TASK170_V0_7_TASK171_ENTRY_AUTHORITY_R4
PACKAGE_ID=HXFORGE-TASK171-ENTRY-R4
PACKAGE_VERSION=1
DOCUMENT_STATUS=PROPOSED_AUTHORITY
SOURCE_BASE_SHA=24099402697a6bc71be3ee112cc87d31e6341a2d
PREVIOUS_HEAD_SHA=de1e8616b6671e69be707591cb3c964f9ca94af5
PR_NUMBER=273
REVIEW_STATUS=PROPOSED_AUTHORITY
APPROVED_BY=
APPROVAL_EVIDENCE=[]
TASK171_ENTRY_REVIEW_PENDING=true
TASK171_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_ADMISSION_ENABLED=false
TASK171_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This package proposes a deliberately narrow **interface entry contract**, not
an executable thermal model or approval. “Admitted” below means the proposed
domain after independent approval and separate implementation authorization.
No topology is enabled by committing this document. Only these three R3 entry
blockers are addressed; all three remain pending reviewer decision:

| Authority candidate ID | Blocker addressed | Normative sections | Status |
| --- | --- | --- | --- |
| V07-T171-TOPOLOGY-R4-V1 | SEG-TOPOLOGY-REVIEW | 2–3 | PROPOSED_AUTHORITY |
| V07-T171-CELL-COMPARTMENT-R4-V1 | SEG-CELL-COMPARTMENT-INTERFACE | 4–5 | PROPOSED_AUTHORITY |
| V07-T171-CONSERVATION-R4-V1 | SEG-CONSERVATION-DISCRETIZATION-REVIEW | 6–7 | PROPOSED_AUTHORITY |

Each record inherits the package version, source base, empty approval fields,
applicability in §2, source mapping in §8 and limitations in §9. Its review
identity is the candidate ID plus exact Git blob of this document at the PR
revision reviewed. A reviewer must bind that immutable revision/blob and the
source revisions, not a mutable branch name. No production authority hash is
invented; future runtime serialization/schema is implementation design, not
implicitly supplied by a Markdown file. R3 source registry remains immutable.

## 2. Initial topology profile and deferred domain

Profile `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1` proposes: steady-state,
single-phase, Newtonian, FIXED_TUBESHEET, E-shell, exactly one shell pass and
one straight-through tube pass, two explicitly identified stream paths with
opposing physical inlet ends, and native TASK020–024 accepted geometry.
Single-segmental baffles and native Bell-compatible geometry restrictions
remain inherited; no family, layout, clearance or source gate is relaxed.

The tube path is a declared bundle-level thermal path, not a claim that a
bundle contains one tube. Actual tube identities/count/area remain TASK021
authority. Collapsing parallel physical tubes into that path requires an
explicit membership and area map. It does not authorize equal-flow or
equal-temperature distribution, a mixed-cell constitutive model, or local
HTC evaluation. Those closures must be reviewed before numerical use.

The shell path is a declared bulk thermal bookkeeping path. It is not the
literal trajectory of every crossflow/leakage/bypass parcel. It must not
be used to infer local mixing or split mass flows. TASK174 owns those
hydraulic/state coupling decisions. Missing explicit maps blocks admission.

| Topology | R4 proposal disposition | Reason / next review |
| --- | --- | --- |
| Fixed-tubesheet straight 1×1 countercurrent as above | Proposed initial interface domain | No return connection; explicit area/path/compartment authority still required |
| U_TUBE, including a legacy one-pass token with valid pairing | BLOCKED_PENDING_FUTURE_REVIEW | Pairing is not a thermal return/leg map; no inferred U-return |
| FLOATING_HEAD straight-through | DEFERRED_PENDING_TOPOLOGY_REVIEW | Vocabulary retained; not included merely because legacy geometry supports it |
| Additional tube or shell passes; split/branched/reversing paths | BLOCKED_PENDING_FUTURE_REVIEW | Requires separate connectivity and thermal mapping |
| COCURRENT, non-E shell, alternate baffle family | DEFERRED_PENDING_TOPOLOGY_REVIEW | No implicit countercurrent substitution |
| Two-phase, transient, external leakage, shaft work, axial wall conduction or ambient heat loss required | OUTSIDE_INITIAL_ENVELOPE | No silent omission of a required physical effect |

Vocabulary remains FIXED_TUBESHEET/U_TUBE/FLOATING_HEAD; vocabulary membership
is not admission. No runtime topology repair, pass reversal, pairing inference,
flow redistribution or geometry search is allowed.

## 3. Topology graph schema and invariants

The proposed logical schema uses these fields; none is an implemented API:

| Identity/field | Meaning and binding |
| --- | --- |
| exchanger_topology_id | Versioned graph identity; binds case, selected profile and exact native TASK020–024 IDs/hashes |
| stream_id | Exactly one hot or cold stream authority; fluid identity is not approved by topology |
| flow_path_id | Directed connected path belonging to exactly one stream |
| physical_segment_id | Immutable physical geometry interval identity, derived from accepted geometry, never a numerical array index |
| numerical_cell_id | Discretization identity scoped to mesh version, stream and physical_segment_id |
| physical_compartment_id | Physical region identity with source role and geometry references; distinct from cell and interval |
| hot_side_assignment / cold_side_assignment | Explicit stream-role mapping, distinct and exhaustive for the two streams |
| tube_side_assignment / shell_side_assignment | Explicit side mapping, a bijection to those streams; never assume hot means shell |
| physical_coordinate_interval | SI-metre interval in an explicitly oriented shell/exchanger reference frame; endpoints bind native geometry |
| fluid_path_coordinate_interval | SI-metre travel coordinate on the named path, monotonically increasing with fluid travel |
| upstream_connection / downstream_connection | Typed inlet/outlet port or cell-face ID on that same directed path |
| wall_interface_id | Shared heat-transfer event identity, with separate inner/outer area references and participating cell faces/regions |

Each admitted path has exactly one physical inlet and one physical outlet.
Every internal face has exactly one upstream and one downstream cell, with
reciprocal connections and consistent stream identity. All cells must be
reachable from the inlet and lead to the outlet: no orphan, disconnected
heat-transfer cell, branch, unintended cycle, zero-length interval or implicit
return path. Wall links are a separate edge type; they do not form fluid
connections. Hot and cold streams meet only through declared wall interfaces,
never by mass exchange. Provenance edges are separate from both graphs.

Physical coordinates increase along the declared shell reference orientation,
not necessarily hot flow. Each stream's cell ordering follows its fluid path.
The admitted two physical inlet ports lie at opposite ends; the wall map pairs
co-located physical surfaces, not equal array indices. Inlet/outlet labels on
each cell always follow actual flow. Both outlet states are unknown fields;
reference outlets must never become boundary conditions or initialization.

Canonical enumeration of IDs is a reporting concern, not flow semantics.
Input permutation must not change graph meaning. Changed connectivity, side
assignment, native authority, area ownership or mesh mapping changes the
corresponding semantic identity. Native producer identities are never rewritten.

## 4. Numerical cells versus geometry intervals

NUMERICAL_CELL, PHYSICAL_GEOMETRY_INTERVAL and BELL_PHYSICAL_COMPARTMENT_OR_EVENT
are different types; ID equality or a default 1:1 map is invalid.

Every cell belongs to exactly one physical interval. Each active physical
interval maps to one or more cells on each represented stream. The cell
intervals form a non-overlapping, complete partition of that interval; shared
faces have one identity. Cells cannot straddle an interval boundary. Intervals
come from explicit geometry/event boundaries, not a uniform mesh assumption.
Point-like baffles/events attach to a canonical physical face/event identity,
not twice to the two adjacent intervals. A compartment may reference multiple
intervals; an interval may reference multiple region roles. This incidence map
does not allocate DP, mass split, conductance or mixing weights.

Lengths and inside/outside transfer areas have separate ownership ledgers.
Summing owned subareas recovers the native physical surface area on its own
basis; do not equate inside and outside areas. Non-transfer surfaces are
explicitly classified, not silently included or discarded. Every physical
transfer surface is covered once by wall interfaces on each side. Mismatched
stream meshes require an explicit common wall-interface intersection map;
no interpolation or state averaging is inferred by the mapping contract.

Mesh splitting changes cell IDs and numerical resolution only. Mesh merging
cannot cross a physical interval boundary or erase an event. Physical interval,
hardware, catalog member, baffle and native result identities remain unchanged.
If an input lacks the necessary geometry subdivision authority, reject the map;
do not manufacture geometric dimensions to make it complete.

## 5. Bell compartment and event interface

Every event record contains event ID, compartment ID/type, native geometry
ID/hash, physical location/support, source relation role, incidence references,
geometry-derived multiplicity, and authority/evidence references. Multiplicity
is a geometric/source-derived count, not a caller-free number. Whole-state
relations retain whole-state scope; an unavailable local evaluator is marked
unavailable, not populated with a divided whole-exchanger result.

| Physical role | Ownership evidence/interface | Not authorized by TASK171 |
| --- | --- | --- |
| Central crossflow | Accepted baffle spacing intervals, central-region identity and native row-count basis | Creating an independent Bell factor for every subcell |
| Window | Baffle/window identity, cut orientation/geometry and source-counted occurrence | Window event at every mesh face |
| Inlet/end zone | Physical inlet-end region and inlet spacing authority | Repeating end loss per cell |
| Outlet/end zone | Distinct physical outlet-end region and outlet spacing authority | Inferring it from the last array index |
| Baffle location | One physical plate/face ID, adjacent-region references | New plate on refinement |
| Leakage geometry | Exact shell–baffle and tube–hole clearance/area authority, linked to affected physical region | A new resolved leakage fluid path or guessed leakage mass fraction |
| Bypass geometry | Native shell/bundle/sealing-strip geometry and source role | A local bypass coefficient or split-flow solver |
| Tube rows/crossed rows | Native layout and relation-specific row/count ownership, including whole-path counts where required | Recounting all rows in every cell or converting global counts to local ones by division |

```ini
MESH_SPLIT_CREATES_PHYSICAL_EVENT=false
MESH_MERGE_DELETES_PHYSICAL_EVENT=false
BELL_EVENT_MULTIPLICITY_DERIVED_FROM_GEOMETRY=true
BELL_EVENT_MULTIPLICITY_DERIVED_FROM_CELL_COUNT=false
```

Forbidden: whole exchanger DP / cell count; whole correction repeated per cell;
per-cell end loss; mesh-generated window or baffle events. Event references may
appear in several incidence lists without creating multiple owners or multiple
evaluations. A physical region is not automatically a perfectly mixed volume.

TASK166 retains its whole-state formula authority. TASK171 supplies ownership
and unresolved producer slots only. TASK174 must independently qualify local
state selection, leakage/bypass treatment and detailed aggregation before
executing them. No local Bell equation or new empirical physics is proposed.

## 6. State location and conservation semantics

| State field category | Required location semantics |
| --- | --- |
| inlet/outlet temperature, enthalpy, pressure, mass flow | Upstream/downstream **face** along named fluid travel; a shared internal face carries one conservative flux identity |
| cell mean temperature/enthalpy/properties | Explicit CELL_MEAN tag plus definition/evaluation authority; not implicitly arithmetic face average or perfectly mixed outlet |
| physical compartment mixed state | Separate optional COMPARTMENT_MIXED tag, requires mixing authority; unavailable in this entry package |
| wall inner/outer temperature | Declared physical surface/interface ID and area basis; unresolved producer slot until TASK172 closure |
| wall heat-transfer rate | Oriented interface event, SI W; not a temperature or per-cell copy of total duty |

No unlocated generic temperature/enthalpy may feed a correlation. A future
property snapshot must bind location, state and property authority; R4 does not
approve any property backend/fluid profile. Cell-mean closure, face reconstruction,
quadrature and local conductance evaluation remain unselected implementation/
numerical authority, not implicit defaults.

For the admitted steady no-external-leak stream, mass flow in equals mass flow
out at each control volume. Bell internal leakage/bypass terminology denotes
intra-shell redistribution/corrections, not external mass disappearance or
cross-wall transfer. A resolved split-stream model would require a new reviewed
network; this package cannot manufacture one from Bell correction factors.

Use enthalpy-based conservation with a consistent stream reference state.
Define q_j positive from the declared hot stream to cold through interface j.
Each interface has one owner, is counted once on the hot side and once on the
cold side with opposite signs. For cells, the structural balance is:

```text
hot:  mass_flow * (h_upstream - h_downstream) = sum(owned q_j)
cold: mass_flow * (h_downstream - h_upstream) = sum(owned q_j)
```

These are conservation identities under §2 assumptions, not implemented solver
equations or a new HTC relation. No silent substitution with constant cp times
temperature difference is allowed. At shared faces the same enthalpy flux is
used by both adjacent cells, so internal fluxes cancel in a global balance.
No double-counted wall transfer remains in the combined two-stream balance.
This defines residual structure only; numerical acceptance thresholds are UNBOUND.

An interface contains its declared participating cells and physical support;
subdivision partitions its area without duplicating heat rate. A negative
q_j is reported with its sign, never absolute-valued or silently reoriented;
admissibility of a temperature-cross/reversal state needs subsequent thermal
authority. No numerical PASS is issued from this interface schema alone.
No axial wall storage/conduction, external heat source, kinetic/potential energy
or shaft-work model is introduced. Cases requiring omitted effects fail closed
against the stated model envelope rather than being claimed physically complete.

## 7. Mesh and legacy separation

Mesh refinement changes resolution, not hardware, manufacturable dimensions,
physical events or multiplicity. Native geometry and event ownership replay
exactly across a mesh change; mesh/cell identities intentionally change.
Mesh count, refinement threshold, maximum mesh, convergence tolerance and
error estimator remain UNBOUND under GAP-NUM. Conservation bookkeeping is not
proof of spatial accuracy or a convergence algorithm.

```ini
N1_LEGACY_NUMERICAL_EQUIVALENCE_REQUIRED_FOR_TASK171_ENTRY=false
N1_LEGACY_BRIDGE_REQUIRED_FOR_TASK175_RELEASE=true
TASK171_ENTRY_AUTHORITY_EQUALS_FULL_GAP_SEG_CLOSURE=false
```

N=1 finite volume is not automatically Magazoni MODEL_2. No tolerance is changed
to claim equivalence. The release bridge requires its independent relation,
area, property and boundary review. Full Bell aggregation, U-tube/additional
passes, Golden data and numerical mesh tolerances are not entry prerequisites
for this narrow interface, but remain prerequisites for their actual use.

## 8. Source mapping and authority classification

No new external research is used. Exact source revisions, access/licensing and
retrieved-byte hashes remain in the [R3 registry](TASK-170-v0.7-authority-registry-r3.json).
This package references them without copying publications or promoting status.

| Candidate / content | Exact inherited/source mapping | Classification and transfer limit |
| --- | --- | --- |
| TOPOLOGY: native geometry identity | R3-INHERIT-GEOMETRY, pinned base; TASK020 configuration; TASK021 layout/pairing; TASK022 bundle; TASK024 baffle native schema/results | Existing REVIEWED_AUTHORITY only for geometry; thermal graph is PROJECT INTERFACE/GOVERNANCE CONTRACT, not external geometric or empirical law |
| TOPOLOGY: opposite inlet paths | R3-MSL-FV, MSL4.1.0 commit 8ae3d35c24e519cb2996cab20f3b13daf2b0c50a, HeatExchanger.mo BasicHX lines328–350, R3 audit §3.1 | VERIFIED_SOURCE example of explicit reversed wall connections; no adoption of its defaults, wall approximation or shell mixing |
| CELL-COMPARTMENT: physical Bell roles | R3-INHERIT-BELL; TASK166 source/relation ledger; R3-GONCALVES §2.1 Eqs55–57,68,70,72–73, R3 audit §3.2 | SOURCE-DERIVED PHYSICS: scoped region/count roles only. Proposed owner/incidence types are PROJECT INTERFACE/GOVERNANCE CONTRACT; no local Bell allocation derived |
| CONSERVATION: local flux balance | R3-MSL-FV Interfaces.mo PartialDistributedVolume lines852–903; Pipes.mo lines471–490, same immutable revision | SOURCE-DERIVED PHYSICS: steady mass/enthalpy balance. Explicit face/event bookkeeping is PROJECT INTERFACE/GOVERNANCE CONTRACT. No MSL default discretization is selected |
| CONSERVATION: surface bases | R3-INHERIT-WALL; TASK037 cylindrical resistance, DOE Vol2 Eqs2-7/2-8/2-10 | Existing area/conduction scope retained, not an inner/outer wall-temperature solution |
| All three: canonical graph/mesh IDs and future raw schema | Package §§3–7; TASK170 R2 coordinate and taxonomy boundary, R3 §3 and §10 | IMPLEMENTATION DESIGN constrained by proposed contract; future bounded schema/canonicalization requires its own review, no runnable authority emitted |

Project ownership choices prevent double counting and ambiguous interpretation;
they introduce no empirical coefficient, constitutive law or engineering
tolerance. They still require independent approval. New records stay
PROPOSED_AUTHORITY; existing geometry/Bell authority does not automatically
approve the thermal graph built on top of it.

## 9. Task boundary and gap status

TASK171 may only implement reviewed thermal-state/topology and conservation
interfaces after separate authorization. TASK172 owns property/wall/numerical
closure; TASK174 owns detailed hydraulics and operability; TASK173 requires
both before complete Rating/Sizing; TASK175 owns approved Golden/parity/release.
Unresolved producer slots cannot be populated by fabricated values or become
recommendations. Reviewing this package alone does not approve a solver slice.

All R3 gap states remain unchanged: SEG/PROP/WALL/NUM/DP/FIV PARTIALLY_CLOSED,
REF OPEN. No broader research or automatic closure occurs. The three TASK171
entry blockers now have concrete proposals; they remain pending independent
review rather than being replaced by full GAP-SEG or Golden closure demands.

## 10. Independent-review checklist and decision record

For **each candidate ID**, reviewer must record APPROVE/REJECT/CHANGES_REQUIRED,
reviewer identity, exact package revision/blob, source revisions, scope,
evidence references and any remaining objection. Empty fields mean pending;
CI, document authorship and observed numerical output are not approval evidence.

- [ ] Confirm §2 straight-through domain is sufficient and explicitly narrower than family vocabulary.
- [ ] Reject U-return, extra passes and unreviewed floating-head admission before graph construction.
- [ ] Verify reciprocal connected paths, opposing physical boundaries and no array-index semantics.
- [ ] Verify interval coverage, native area bases, explicit parallel-tube membership and no inferred mixing.
- [ ] Verify central/window/end/baffle/leakage/bypass/row ownership is physical and independent of mesh count.
- [ ] Verify refinement/merging preserves hardware/event identities and cannot repeat a whole-state Bell relation.
- [ ] Verify face/mean/mixed/wall state tags and the unselected reconstruction/constitutive boundary.
- [ ] Verify enthalpy signs, shared-face cancellation and once-only wall ownership without guessed cp.
- [ ] Verify N=1 is deferred to TASK175, not waived or required for this interface entry.
- [ ] Confirm no numerical preset, empirical relation, fluid approval or Golden oracle is introduced.
- [ ] Decide each of the three entry blockers individually; no blanket all-GAP switch.

Validation of this documentation change: doc-only diff, links and status fields,
unchanged R3 registry/gap states, no dependency/code/test changes, and full CI
on the final PR head. These are document checks, not runtime implementation
tests or proof of thermal closure. PR273 remains Draft; no self-approval.
