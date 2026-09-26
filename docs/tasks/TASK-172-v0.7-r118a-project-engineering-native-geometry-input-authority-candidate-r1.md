# TASK172 R118-A — Project Engineering Native Geometry Input Authority Candidate

## Decision and boundary

R118-A constructs one project-internal, case-design-bound candidate input bundle for the later TASK020 → TASK021 → TASK022 → TASK024 → TASK025 chain. It is proposed for independent review only. It does not execute any of those producers, persist a case revision, create a case/configuration/geometry identity, or approve the candidate.

| Field | Value |
|---|---|
| Task | `TASK172_V0_7_R118A_PROJECT_ENGINEERING_CASE_NATIVE_GEOMETRY_INPUT_AUTHORITY_CANDIDATE_R1` |
| Bundle | `V07-T172-PROJECT-ENGINEERING-NATIVE-GEOMETRY-INPUT-BUNDLE-R1` |
| Lifecycle | `PROPOSED_AUTHORITY_REVIEW_PENDING` |
| Case design | `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-DESIGN-R1` |
| Profile | `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1` |
| Predecessor | `b83849212703ea7c94366dbdb207a3f2d4d915f7` |
| Scope | R116-reviewed internal geometry authorities and the exact R117 case-design scope only |

The case class remains `PROJECT_DESIGNED_ENGINEERING_REFERENCE_CASE`. This is a project design, not a test/synthetic/benchmark fixture and not an external as-built or measured case. No standard, vendor, client, site, manufacturer, drawing, mechanical adequacy, or code-compliance claim is made. `NO_STANDARD_CLAIM=true`; all values below are explicit design choices or frozen bindings, not defaults.

## Predecessor and frozen authority replay

The authorized PR #283 predecessor was fetched and matched the exact authorized HEAD. The corrected R117 case-design file/canonical identity, R117 evidence file/canonical identity, `r117_extension`, and pre-R118A registry root replayed to the authorized values. The corrected TASK022 `maximum_position_count` binding resolves to `V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-RULE-R1`; unknown and invalid reviewed-source bindings are both zero.

R117 snapshots are inputs and were not changed:

| Runtime authority | Exact authority ID | Snapshot identity |
|---|---|---|
| Tube geometry | `V07-T172-INTERNAL-TUBE-GEOMETRY-R1` | catalog record `e98cd8639bc2e1bfcfbd2664bbd4779cbf5983b9e06ca5540178bf49d5ee524d`; runtime snapshot `ad70e011946ce47e81fdfd5abe7b6376beeb4f4f438bc83e92a703d6f9ee23e2` |
| Tube layout rule | `V07-T172-INTERNAL-TUBE-LAYOUT-RULE-R1` | runtime snapshot `a4f7383fc5cd865592a766be245aae0ba063136970e905d56681314cac600319` |
| Shell/bundle rule | `V07-T172-INTERNAL-SHELL-BUNDLE-GEOMETRY-RULE-R1` | runtime snapshot `cb3bd64b809a3460a0e205650927585a61b46713bb565d45b480387fd7702df8` |

The R115/R116 geometry values, approved-by/at provenance, authority scope, and runtime snapshots remain byte-for-byte unchanged. R116 reviewed lifecycle does not turn this R118-A input bundle into an approved bundle.

## Native schema completeness audit

The machine-readable matrix at [the R118-A native input completeness matrix](evidence/TASK-172-r118a-native-input-completeness-matrix-r1.json) enumerates required native caller fields, nested authority fields, current R117 state, binding class, candidate value/projection, evidence, and consumer. It was built from the current TASK014, TASK020, TASK021, TASK022, TASK024, and TASK025 models/parsers/contracts—not from the shortened R117 input summary.

Counts include each native top-level request field and the exact caller-owned nested fields. Composite upstream objects are listed as one field and linked to their frozen authority or future native producer; their internal frozen snapshot fields are not duplicated as caller inputs. TASK014's case-revision projection is separately recorded and is not counted in TASK020–025 totals.

| Stage | Required input rows |
|---|---:|
| TASK020 | 18 |
| TASK021 | 13 |
| TASK022 | 16 |
| TASK024 | 23 |
| TASK025 | 28 |
| **Total** | **98** |

Every required row is either bound to an exact reviewed authority/profile, explicitly designed in this candidate, identified as a native contract constant without a separate reviewed-profile claim, not applicable under the selected topology/authority mode, or an output that only the named native producer may derive. No required input is left silently blank. Stream/property/material/thermal authorities and topology/case-bound runtime closure remain explicitly deferred outside R118-A; this geometry bundle does not make those downstream gates pass.

## Explicit project design inputs

The complete values, units, rationale, source class, and evidence pointers are machine-readable in the R118-A evidence. The following are the single selected candidate—not a scan, optimizer, catalog snap, remembered typical, or fixture reuse:

| Input | Candidate value | Design rationale / limitation |
|---|---:|---|
| TASK020 orientation | `HORIZONTAL` | Explicit reference-case orientation from TASK020's closed enum. It does not infer baffle orientation, nozzle location, gravity behavior, or mechanical adequacy. |
| TASK020 front/rear tokens | `T172_FRONT`, `T172_REAR` | Opaque internal-generic project tokens; they do not encode a standard/vendor identity. |
| TASK020 shell token | `E` | Bound from reviewed profile `V07-T171-STRAIGHT-COUNTERCURRENT-ENTRY-R4-V1`, whose scope is E-shell; TASK171 native replay requires `component_tokens.shell == "E"`. This token expresses the already reviewed topology only and does not establish TEMA compliance. |
| TASK021 tube-center envelope diameter | `0.45 m` | Explicit placement envelope, distinct from shell ID, bundle diameter, and baffle diameter. |
| Layout origin / axis | `CENTER_ON_LATTICE_POINT` / `PRIMARY_AXIS_X` | Explicit case selections permitted by the frozen R116 layout rule. |
| Exclusion zones / U-tube pairing | `[]` / `null` | No nozzle/pass lane is invented. Empty zones mean no exclusion geometry is defined by this case input, not that a physical nozzle is absent. U-tube pairing is inapplicable to straight-through tubes. |
| Caller shell inside diameter | `0.500 m` | Project-selected caller value; no catalog lookup, nearest-size choice, or automatic sizing. |
| Bundle peripheral allowance | `0.010 m` | Project choice, 0.00365 m above the reviewed 0.00635 m minimum. It is not equal to the rule minimum. |
| Required radial clearance | `0.010 m` | Project choice, 0.00365 m above the reviewed 0.00635 m rule minimum. It is not a manufacturing/mechanical criterion. |
| Active axial span / tube lengths | `0–6 m`; internal flow `6 m`; heat-transfer `6 m` | One consistent project-selected straight support. TASK025 will derive areas/volume/perimeter/diameters from actual native upstream outputs and this explicit length authority. |
| TASK025 geometry authority mode | `INTERNAL_ARITHMETIC_FROM_LENGTH` | Explicit case-level selection of the native accepted geometry-from-length mode; it does not select a thermal or hydraulic solve method. |
| Baffles | 4 single-segmental, `0.006 m` thick; 5 equal `1.2 m` spaces | Explicit one-case geometry candidate. The spacing sequence sums to the 6 m span; each occupied thickness interval is inside that span and disjoint from its neighbors. |
| Baffle cut fraction | `0.25657` | Explicit project design selection. With the candidate baffle diameter and R116 triangular row spacing, the native cut-chord formula places the cut between adjacent tube-center rows; the nearest-row distance exceeds the proposed tube-hole radius. No alternatives were searched or ranked. |
| Baffle cut orientation sequence | `BOTTOM`, `BOTTOM`, `BOTTOM`, `BOTTOM` | Explicit project-design sequence in baffle-index semantic order. All four candidate baffles intentionally use BOTTOM orientation; no automatic alternation, lexical sorting, or inference from equipment orientation is applied. |
| Shell-to-baffle diametral clearance | `0.003 m` | Explicit project geometry input; baffle diameter is then `0.497 m` from the native diametral-clearance relation. |
| Tube-to-baffle-hole diametral clearance | `0.001 m` | Explicit project geometry input; hole diameter is `0.02005 m` from tube OD plus clearance. This is only a prospective geometric relation, not fabrication approval. |

## TASK014 / TASK020 revision candidate

TASK020 requires a `CaseRevisionAuthority` with a committed/superseded/archived status. R118-A supplies a deterministic *projection candidate* whose payload and domain-snapshot hashes are calculated by the repository's TASK014 `compute_payload_hash` and `compute_domain_snapshot_hash` over the actual machine-readable candidate payload/identity/provenance. It does not persist or commit a TASK014 `CaseRevision`; `CASE_ID` remains `UNBOUND`.

The candidate revision ID is `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-DESIGN-R1-REV-1`. The proposed downstream TASK020 status is `committed` only as a post-TASK014-validation-and-commit target. The candidate request is non-executable until TASK014 actually materializes the matching revision and the applicable lifecycle gates are completed. If R118-C changes the native identity/payload, the native TASK014 hashes and TASK020 binding must be recomputed; no stale projection is authoritative.

TASK020's intended mode is `INTERNAL_GENERIC`; accordingly `standard_system_id=null` and `requested_rule_pack_identity=null`. The front/rear tokens remain opaque project tokens. The shell token is `E`, bound from the reviewed TASK171 E-shell profile because the TASK171 native topology contract rejects any other shell token. This expresses the reviewed E-shell topology; it makes no TEMA, ASME, vendor-equivalence, or other standard claim. The TASK171 source/profile compatibility check is static only; TASK171 replay and TASK020 validation/materialization are not invoked.

The TASK014 case-revision object remains a candidate projection only: `status_proposal_only="committed"` is a future eligibility target after native TASK014 validation and commit, not persisted lifecycle state. `TASK014_NATIVE_CASE_REVISION_MATERIALIZED=false` and `TASK014_NATIVE_CASE_REVISION_COMMITTED=false`. The first R118-C execution stage is `TASK014_NATIVE_CASE_REVISION_MATERIALIZATION_AND_VALIDATION`; only its accepted immutable result may supply the TASK020 `CaseRevisionAuthority`. The future native dependency order is TASK014 revision → TASK020 configuration → TASK021 layout → TASK022 bundle geometry → TASK024 baffle geometry → TASK025 tube-side geometry. No stage is executed by this correction.

## Prospective layout and geometry coherence

The only layout dry-run was in memory, using the unchanged approved tube and layout snapshots plus the candidate envelope/origin/axis and empty exclusion list. It did not create a `TubeLayout`, layout hash, or `LAYOUT_ID`.

| Check | Prospective result |
|---|---:|
| Effective center radius | `0.2123 m` (> 0) |
| Enumeration rectangle capacity | `713` (≤ 10,000) |
| Accepted candidate positions after envelope and empty-zone filtering | `253` (> 0) |
| Maximum accepted tube-center radius | `0.20790796040565414532539714780598484862428037121921 m` |
| Bare bundle diameter = 2 × (maximum center radius + OD/2) | `0.43486592081130829065079429561196969724856074243842 m` |
| Bundle outer-envelope diameter = bare diameter + 2 × allowance | `0.45486592081130829065079429561196969724856074243842 m` |
| Shell radial clearance | `0.02256703959434585467460285219401515137571962878079 m` |
| Margin above proposed 0.010 m required clearance | `0.01256703959434585467460285219401515137571962878079 m` |
| Margin above R116 rule minimum 0.00635 m | `0.01621703959434585467460285219401515137571962878079 m` |

For the proposed baffle clearances, baffle diameter is `0.497 m`, baffle radius is `0.2485 m`, and hole diameter is `0.02005 m`. The maximum tube-hole outer radius from the centerline is `0.21793296040565414532539714780598484862428037121921 m`, leaving `0.03056703959434585467460285219401515137571962878079 m` to the baffle perimeter. The nearest lattice-row center is `0.01099756153674844976679141122274747436104176034035 m` from the cut chord; the proposed hole radius is `0.010025 m`, leaving positive `0.00097256153674844976679141122274747436104176034035 m` separation. The four occupied axial intervals are `[1.197,1.203]`, `[2.397,2.403]`, `[3.597,3.603]`, and `[4.797,4.803] m`, inside `[0,6] m` and non-overlapping.

These are candidate arithmetic/invariant checks, not a TASK022 geometry result or TASK024 baffle result. No mechanical/code adequacy, manufacturability, thermal performance, pressure-drop, or production mesh conclusion follows.

## TASK025 caller-input/output separation

The candidate mirrors the exact TASK025 native object shape: `internal_flow_authority.start_plane` and `.end_plane`, and `heat_transfer_authority.start_plane` and `.end_plane`, each contain a `ReferencePlanePair` object with `start` and `end` members. Both start/end values use the corresponding canonical native pair. The two length hashes were replayed with the native hash functions and are unchanged. `profile_id=profile-001` is accepted by the native `SUPPORTED_PROFILE_IDS` constant, but no separate reviewed engineering-profile authority was found; the matrix classifies it as `NATIVE_CONTRACT_CONSTANT_ONLY`, not as an already-bound reviewed profile.

The candidate defines the two length authorities as `6 m` and explicitly selects the native `INTERNAL_ARITHMETIC_FROM_LENGTH` geometry authority mode. This is a geometry derivation mode only, not a solve method. It proposes that every position accepted by the eventual TASK021 layout participates in both straight-through tube geometry paths, with no inactive position. Actual position IDs and the participation hash cannot exist until TASK021 produces its native layout, so those are classified `DERIVED_ONLY_BY_NATIVE_PRODUCER`; R118-A does not invent position IDs.

TASK025's physical tube count, flow area, wetted perimeter, hydraulic diameter, internal volume, and heat-transfer surface area are native-derived outputs, not R118-A caller inputs. No historical v0.1 `4.85 m` / `8 tubes` fixture values are reused.

## Validation boundary and lifecycle

Prospective schema/compatibility checks cover TASK020's request parser, TASK021 authority/envelope parsers and enumeration, TASK022 caller-shell canonical hash and containment arithmetic, TASK024 candidate authority hashes and structural invariants, TASK025 native length-hash replay, and a field-by-field completeness scan. Upstream-consuming TASK022/TASK024/TASK025 producers are not called because they require native configuration/layout/bundle results that this phase is expressly forbidden to materialize.

`R118A_INPUT_AUTHORITY_CANDIDATE_PRESENT=true`; `INDEPENDENT_REVIEW_COMPLETE=false`; `CODEX_SELF_APPROVAL=false`. `TASK020_CONFIGURATION_MATERIALIZED=false`, `TASK021_LAYOUT_EXECUTED_AS_AUTHORITY=false`, `TASK022_BUNDLE_GEOMETRY_EXECUTED_AS_AUTHORITY=false`, `TASK024_BAFFLE_GEOMETRY_EXECUTED=false`, `TASK025_AREA_LENGTH_EXECUTED=false`; `CASE_ID`, `CONFIGURATION_ID`, and `GEOMETRY_ID` remain `UNBOUND`. Production mesh profile and reference-policy applicability remain unresolved. No property/material/HTC binding, TASK172 implementation, TASK174 solve, TASK173 rating/sizing, or TASK175 release acceptance occurred.

The historical local full regression is not relabeled: R115 was NOT_CLEAN (7 failed, 70 errors, 9 skipped); R116 final-head local full regression was NOT_EXECUTED; R117's final-head local full regression was NOT_CLEAN (7 failed, 70 errors, 9 skipped). Those are predecessor runs, not R118-A. The predecessor GitHub CI was independently counted as 50 total jobs: 45 success, 5 skipped, 0 failed at `b83849212703ea7c94366dbdb207a3f2d4d915f7` (run `36232499969`). R118-A validation and exact-final-head CI are reported separately in the final receipt.

The shell-token correction is recorded in the R118-A E-shell topology-binding correction receipt. The registry update is append-only; prior R118-A correction and R1–R117 records remain unchanged. The historical two duplicate keys in the registry are preserved; no historical repair is authorized. No production code, existing test, dependency, lockfile, or workflow is changed. The next gate is `R118B_INPUT_AUTHORITY_INDEPENDENT_REVIEW_ONLY`; R118-A stops here.
