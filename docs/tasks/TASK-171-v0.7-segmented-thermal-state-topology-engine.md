# TASK171 — segmented thermal-state and topology interface engine

## Authority and scope

Base: `65f36220263bd49903d186025da23e1d76c69c7e` (TASK170 merged).
Tracking authority: [Issue #274](https://github.com/xuezhiorange-png/hxforge-agent/issues/274),
recording the user's explicit TASK171-only implementation authorization.
Predecessor exact-main CI: `34676994583`, completed/success.
Profile: `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`, implementation
`task171.v1`. Reviewed IDs: `V07-T171-TOPOLOGY-R4-V1`,
`V07-T171-CELL-COMPARTMENT-R4-V1`, `V07-T171-CONSERVATION-R4-V1`.
Review receipt: `TASK170-R4-INDEPENDENT-ENTRY-REVIEW-R5`; reviewed document
SHA256: `ecf01cb2b019a7b43a4dd6241890893fb4238a0a11dec4a1c4e91d780c9e08ca`.
Runtime binds machine constants, never reads Markdown for admission.
The canonical authority-profile hash binds the receipt/document identities,
reviewed IDs, predecessor classes and deferred topology set into every result.

Only steady, single-phase, Newtonian fixed-tubesheet, E-shell, one shell pass,
one straight-through tube pass and explicit countercurrent paths are admitted.
Existing native single-segmental/geometry gates remain mandatory. Neither
family vocabulary nor a successful native geometry implies thermal admission.
Both tube-hot and shell-hot assignments are supported. There is no implicit
return, branching, cycle, parallel-tube redistribution or pass inference.

TASK171 implements structure and exact conservation bookkeeping, not an HTC,
property, wall, pressure-loss, convergence, Rating or Sizing solver. No new
empirical relation, tolerance, fluid profile or dependency is introduced.

## Public boundary and native replay

`segmented_thermal_state_topology.validate_request(raw)` accepts an exact dict:

- `definition`: exact immutable `Definition` with explicit mesh and mapping bindings;
- `baffle_request`: existing TASK024 public raw request, retaining native TASK020,
  TASK021 and TASK022 objects in their producer-defined representations;
- `area_request`: existing TASK025 public raw request;
- `native_identity`: expected native configuration/layout/bundle/baffle/area IDs/hashes;
- `bookkeeping`: explicit `Bookkeeping` or `None`.

TASK024 public validation replays its authority foundation and geometry.
TASK025 public validation replays native area authority. Expected identities,
layout binding and active heat-transfer length versus mapped axial span must
match. TASK037's existing `compute_outer_to_inner_area_ratio` supplies the
existing cylindrical area-basis transform; TASK171 checks the exact product
of public inside area and that public ratio, without a second surface formula.
No reconstructed private area or new rounding tolerance is used. Area basis
transformation is not a wall-temperature solution. Native request authority
failures retain a typed TASK171 upstream failure with no partial topology.

Project mapping/mesh references are explicit source-bound definitions, not
reviewed numerical presets. Their source hash must bind the replayed baffle
geometry. Evidence, revision and identity are required and included in the
request identity; missing authority cannot become an implicit mesh default.
The test-only values are expressly not production numerical authority.

## Structural invariants

Physical coordinates and stream-travel coordinates are distinct. Travel is
monotonic along each declared path; wall matching uses physical support, not
array index. Shell inlet/end ownership follows the explicit shell direction.
Reciprocal shared-face connectivity has one inlet/outlet, complete reachability
and no disconnected cycles, orphan cells, cross-stream mass edges or branches.

Each cell belongs to one physical interval; cells completely partition each
interval on each path. Different stream meshes require an explicit common wall
intersection map. Wall subareas sum exactly on their own inner/outer bases to
interval and native totals. No averaging, interpolation or constitutive mixing
is inferred. Refinement changes mesh/cell identity, not physical hardware IDs.

Bell events are unresolved structural references. Native plate indices locate
baffle/window/leakage-geometry records; adjacent plates locate central regions;
the explicit shell path locates inlet/outlet end zones. Bypass and layout-row
reference records retain whole-geometry support. The row reference's multiplicity
is **one reference to the native position set**, not a calculated Bell crossed-row
count or the physical tube count. No local Bell row estimator is implemented.
All records use `source_relation_role=STRUCTURAL_REFERENCE_ONLY` and
`producer_status=UNRESOLVED`. Event keys and native geometric supports enforce
once-only ownership independent of numerical mesh. Duplicate, missing, relocated
or mesh-created events fail closed. Native formula semantics are unchanged.

State locations distinguish upstream/downstream faces, cell means, compartment
mixed states and inner/outer wall surfaces. All future producer slots remain
UNRESOLVED. Mixed-state schema does not authorize a mixing law. Wall surfaces
bind tube/shell side independently of hot/cold roles.

## Conservation and identity

Optional observations provide source-bound face enthalpy (J/kg), positive mass
flow (kg/s) and signed wall heat rate (W). Exact steady mass equality is a
structural prerequisite. A shared face has one observation. Each wall event
appears once per side; positive q means hot to cold. Hot residual is enthalpy
flux decrease minus q; cold residual is enthalpy flux increase minus q. The
global residual is hot-minus-cold residual sum, cancelling the shared wall terms.
No absolute-q, cp substitution, property call or outlet solving is performed.

Fraction arithmetic implements exact terminating-decimal sums/products; no
ambient Decimal context, epsilon or numerical convergence decision is involved.
`VALIDATED` is structural status only. Bookkeeping is `COMPUTED_NOT_ASSESSED`,
`NOT_REQUESTED` or `UNAVAILABLE`; a nonzero energy residual is not auto-rejected
against an invented tolerance and a zero residual is not rated CONVERGED.

Shared `hexagent.canonical_json` owns canonical JSON/SHA256. Semantic decimal
lexemes are normalized; repeated records are sets ordered by canonical keys.
Flow meaning resides in explicit connections. Result identity binds version,
definition, native identities and optional observations/residuals. Result
contains a canonical immutable topology snapshot. Hardware ownership hash and
mesh identity are separate. Required review/native/mapping nodes feed a run
node and result node; self edges, duplicates and cycles fail closed. Native
producer IDs are never rewritten.

Structural resource limits (4096 records, bounded depth/string size) are raw
admission safety limits, not default mesh count, convergence or mesh adequacy.
Invalid raw/model-constructed objects yield typed BLOCKED without fake output.

## Verification and deferred work

Tests under `tests/exchangers/shell_tube/segmented_thermal_state_topology/`
use explicit synthetic meshes with native public validation. They cover role
swap, interval/cell/wall partition, refinement identity, native/event tampering,
connectivity failures, source-binding absence, unlocated states, exact enthalpy
bookkeeping, canonical ordering/context and provenance cycles. They are unit/
integration contracts, not independently approved Golden values. CI manifest
registers the test file in both existing Python runtimes.

Local-first policy: no intermediate push/CI. Local targeted and final legacy
regressions, lock, lint, format, mypy and manifest checks precede final commit/
push. Exact final PR-head CI and counts are recorded on the Draft PR after
execution; CI status is not embedded as a self-referential source identity.

Local evidence (2026-09-12): 53 TASK171 tests passed independently on Python
3.11.15 and 3.12.13. The final full-suite validation snapshot passed 6854 tests,
with 3 skips and 19 warnings (including 3 passing generated CI self-test probes
left by the preceding run). The registered manifest remains exactly 256 files;
generated probes are not committed. Lock check/sync, repository-wide Ruff,
format, strict mypy (440 source files), manifest and diff checks passed.
The full suite includes TASK020–024, TASK160–162, TASK166–169 and canonical/
provenance regressions; no existing source or Golden expectation was edited.

Full regression ran in a separate local clone with identical implementation/
test bytes and local-only validation snapshots: existing tests require a clean
tracked tree, a real `.git` directory, non-`/tmp` source paths and configured
TASK164 dual-runtime executables. These prerequisites were satisfied without
changing legacy tests. Validation snapshot commits are not published or release
authority. The development branch remained uncommitted/unpushed until local
validation completed. Both real runtimes produced result hash
`6c5329f8c952832b7d46be807c595b80a98dfa7a1db342b0211830c5996af485`
and full canonical result-byte SHA256
`a800295a385b1b4b93fafaeca0a9479c0bdd7b0f5675515dba2483c2e8548bf6`
for the explicit split/multiple-interval fixture. This is repeatability evidence,
not an independent engineering Golden oracle.

TASK172 still owns property/wall/cell-mean/reconstruction/numerical closure.
TASK174 still owns detailed hydraulic allocation and FIV. TASK173/175 are not
started. U-tube, floating head, extra passes, cocurrent and alternate topology
remain unsupported. N=1 equivalence is not required for TASK171 and remains
required for TASK175 release. TASK170 receipts and legacy Golden expectations
are unchanged. Ready/Merge and subsequent tasks require separate authorization.
