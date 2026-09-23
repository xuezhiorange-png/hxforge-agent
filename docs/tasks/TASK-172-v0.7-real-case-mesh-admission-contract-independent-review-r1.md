# TASK-172 v0.7 — Real-Case Mesh Admission Contract Independent Review R1

Task: `TASK172_V0_7_REAL_CASE_MESH_ADMISSION_CONTRACT_INDEPENDENT_REVIEW_R1`
PR: #277 (`OPEN_DRAFT`)
Authorized predecessor / reviewed R104 head: `dccb51da09f1c7f730b51d20341786645fa4d8a5`
Result: `BLOCKED_REAL_CASE_MESH_ADMISSION_CONTRACT_INDEPENDENT_REVIEW`

## Decision

The R104 candidate is substantively fail-closed about synthetic-to-real
quantitative transfer, and its supported topology and physical-to-cell
structural contract are consistent with the reviewed TASK170/TASK171 boundary.
All 14 transfer rows were independently adjudicated. However, the review cannot
promote R104 to contract-level `REVIEWED_AUTHORITY` because (1) the declared
canonical hashes for R104 evidence, transfer matrix, extension and registry do
not reproduce under the repository's shared `hexagent.canonical_json` rules;
(2) the admission predicate does not explicitly gate every separately
UNBOUND policy slot and gives no definition that makes its broad alias
`mesh_profile_authority_valid` cover them; and (3) the headroom row attributes
a requirement to TASK172 that TASK172 does not state.

R104 is not edited. This review records an append-only correction requirement;
it creates no numerical mesh authority and changes no production behavior.

```ini
R104_CANDIDATE_CONTENT_REPLAYED=true
R104_LIFECYCLE_REMAINS=PROPOSED_AUTHORITY_REVIEW_PENDING
REAL_CASE_MESH_ADMISSION_CONTRACT_REVIEWED_AUTHORITY=false
MESH_AUTHORITY_REAL_CASE_GENERALIZATION_BOUND=false
PRODUCTION_MESH_SELECTION_CONTRACT_BOUND=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
```

## Baseline, provenance, and independent hash replay

The fresh PR-head reference and fetched `refs/pull/277/head` both equal the
authorized SHA. PR #277 is open and Draft. The R104 commit's direct parent is
`8703d17e88b9215b755d402bd4686d36f14ad673`, matching its declared predecessor.
The commit changes the registry plus only the three R104 candidate artifacts.
Removing `r104_extension` and restoring the predecessor registry root yields
the exact predecessor registry payload; R1–R103 payloads and extension values
are unchanged.

Independent direct-file SHA-256 replay:

| Artifact | Recomputed SHA-256 | R104 binding | Result |
|---|---|---|---|
| R104 document | `8154066139f6587be3f627e1d73c882d5719a53a1c828f22a3f04024de2ee73c` | same | PASS |
| R104 evidence file | `2a9f16b7eda50e568dd627bba27fc5d137d83ac80c11baabec8f9729a53a7cc4` | same | PASS |
| R104 transfer-matrix file | `06bf948f6508a5cafa120d5d8be6928e4d35ef7f6ee1f09b34cd16f96fc53c65` | same | PASS |

The canonical-hash claims do **not** reproduce. Recalculation used the current
shared helper `hexagent.canonical_json.canonical_sha256`, which applies the
repository's RFC 8785 serialization, NFC normalization, non-finite-number
rejection, and declared excluded-hash-field behavior. The predecessor registry
root independently reproduces as `d1849d3f...ffd362` under that same helper.

| Payload | R104-declared canonical hash | Shared-helper recomputation | Result |
|---|---|---|---|
| R104 evidence | `3b01d5642e0f28c440a4409902fbd916dd1ac5ada5e83653c1cc31e2cdc90d2d` | `2164dcfcdc585281238598d6bc271bbe015b72ce97fa5cc5326a888993457135` | MISMATCH |
| R104 transfer matrix | `991e4024e2bfed5f49eaff453f6a564d0a165036174ed6b06a8901038589509a` | `5b5e92f7346b22cd1de0e5c28caa0ef67e211df91febb70d3354f9ed3f94e14a` | MISMATCH |
| R104 extension | `da7dc27f1e0094fc2880522593697bfc4eb31ba6ff676f6125540e3f9c54e44d` | `e035372e976e1ede05482c30c59c0d8a3defd4c3bfc802c87321144ba3f1d8bc` | MISMATCH |
| R104 registry root | `e69689e4960bad3ddb7ba961134cf27b6532cb118af8d614c8c31ea789771887` | `00353f88e0c6c5aba94f2043403e41208014e769a05c8461ffada76169af41d7` | MISMATCH |

The R104 document explicitly names the existing `hexagent.canonical_json`
contract for mapping identity, and no separate R104 canonicalization rule is
authorized. These are integrity/linkage failures, not a judgment that the
document's direct-file SHA values are wrong. They must be corrected through a
separately authorized append-only correction; this review does not rewrite
R104.

## Frozen authority and R103 scope replay

Independent source replay used:

| Authority | Independently reviewed artifact | SHA-256 |
|---|---|---|
| TASK170 v0.7 freeze | `docs/tasks/TASK-170-v0.7-scope-source-golden-freeze.md` | `5fc00303e3a74a850b22f89a4c56bbad1b269f39d6a32e652b56b19402b22de0` |
| TASK171 implementation/interface | `docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md` | `62d03bb1d95ee647870b62d2c5a8bafbff4df2fa215c6d282c379a4876311943` |
| TASK171 R4 topology/cell/conservation package | `docs/tasks/TASK-170-v0.7-task171-entry-authority-r4.md` | `ecf01cb2b019a7b43a4dd6241890893fb4238a0a11dec4a1c4e91d780c9e08ca` |
| R5 independent review receipt | `docs/tasks/TASK-170-v0.7-final-review-receipt-r5.md` | `7889a78daa521d2e8b207a953b89ad2ff76bb31c88c1b747043392251b29fbdd` |
| TASK172 mesh model contract | `docs/tasks/TASK-172-v0.7-mesh-convergence-contract-r1.md` | `3577f64cc5280d7988068c145fe3e495d58d6548392c6fb7329df070b077cf7c` |
| R98 independent review | `docs/tasks/TASK-172-v0.7-mesh-cell-scale-numerical-acceptance-extension-independent-review-r1.md` | `0e3fbb2204f0335201a577fba29cc7210467b7648d10fee0658a449ec67a2aad` |
| R102 canonical-reference correction | `docs/tasks/TASK-172-v0.7-continuous-reference-oracle-scipy-canonical-envelope-binding-correction-r1.md` | `300eee99502beb815bf72a64b57d2c66a771c8d2cf795e5fa8148ac875c5e5d8` |
| R103 final mesh qualification | `docs/tasks/TASK-172-v0.7-mesh-convergence-final-qualification-r1.md` | `4ab8c5c6ae1a7f499feaa2411c701d57c0b75b5aef4533e27991c187d019d431` |

R103 independently replays as `PASS_MESH_CONVERGENCE_QUALIFICATION`,
`REVIEWED_AUTHORITY`, scope `FROZEN_SYNTHETIC_FIXTURE_PROFILE_ONLY`. Its six
fixture matrix, cell sequences, thresholds and resource-cap results are
qualification evidence for that frozen profile. R103 did not create a
production Rating, a real case, or a production cell reconstruction operator.
R98 `C_round=1.0` remains fixed training/holdout mesh-cell-scale authority only.
R102's SciPy GL1024 reference and empirical `U_Q` remain synthetic-reference
qualification authority, not a requirement for online real-case reference
calculation.

An independent repository search across reviewed TASK170–TASK172 documents,
the authority registry, and production mesh/topology source found no complete
reviewed real-case production mesh admission/selection authority. TASK171
supplies structural topology/cell invariants only; its 4096 raw-record guard is
not a numerical-cell cap. TASK172 binds criterion/status schemas, not real-case
initial counts, split operators, thresholds, headroom or caps.

## Topology, mapping, identity, and admission review

The candidate's supported physical topology is consistent with the R5
reviewed entry scope: steady, single-phase, Newtonian, fixed tubesheet, E-shell,
one shell pass, one declared straight-through tube pass, explicit opposing
countercurrent paths, and native accepted geometry with existing native
single-segmental/Bell compatibility gates. U-tube, floating head, additional
passes, branching/reversing paths, cocurrent, alternate families, two-phase or
transient service, and effects outside the admitted model remain excluded or
deferred. No wording was found that converts a family token or numerical mesh
into physical topology authority.

The mapping schema carries cell/mesh/refinement identity, physical support and
intervals, fluid-path intervals, compartment and hot/cold path IDs, inner/outer
area, length, local geometry binding and event ownership. Its invariants follow
TASK171: native event boundaries are immutable, cells partition already
admitted supports, area/length totals are conserved under the admitted exact
representation, direction is explicit, countercurrent pairing is not inferred
from array order, and refinement changes numerical cells only. This is a
structural mapping contract, not a numeric production mesh policy.

The profile/instance identity schema binds case/configuration/geometry/topology,
profile and sequence identities, cell boundaries/count, mapping hash,
authority hash set and parent mesh lineage. It uses the existing shared
canonical JSON system in its stated design. The schema is structurally
adequate, but canonicalization **validation fails** because the declared R104
artifact/registry hashes do not match that system (Finding R104-HASH-01).

No hidden real-case numerical default was found: R104 leaves the initial mesh,
refinement operator, convergence threshold, headroom, resource cap, reference
policy, wall acceptance and normalized descriptor unbound. The historical
`1,2,...,128`, `[3,6,...,96]`, `1e-2...1e-5`, `0.01` thresholds, synthetic cap
128, and `C_round=1.0` are identified as synthetic-only or additional-authority
items, not production defaults. Case-level material/property/HTC/wall/numerical
authority gates remain distinct from mesh admission. Existing TASK171 error
codes and TASK172 model-status/failure vocabulary are mapped by layer; R104
creates no runtime enum.

## Independent 14-row transfer adjudication

All 14 rows were reviewed individually; row details and source basis are in
the linked machine-readable matrix. Thirteen rows have supportable dispositions.
The headroom row's disposition remains fail-closed
(`ADDITIONAL_AUTHORITY_REQUIRED`), but its basis says TASK172 requires a
headroom criterion. TASK172 mesh contract §11 requires a future criterion to
bind consecutive evidence, sequence, metrics, precision floor and failure
disposition; it does not specify headroom. R104 can propose a new, still-unbound
headroom slot as contract design, but it must not attribute that requirement to
existing TASK172 authority (Finding R104-XFER-07).

The other transfer conclusions are scope-correct: synthetic sequences,
thresholds, selection objective, caps and reference producer stay
validation-only; `C_round` needs additional authority; `U_Q` transfers only its
empirical/non-formal limitation and a future case-specific propagation
obligation; wall extrema and determinism transfer as case-bound observable and
identity requirements only; failure vocabulary transfers as existing
contract/status shape without implying a production enum or implementation.

## Findings requiring correction

### R104-HASH-01 — canonical hash claims do not follow shared project semantics

Severity: HIGH.
Artifacts: R104 evidence, transfer matrix, `r104_extension`, and registry root.
Independent finding: direct file SHA values reproduce, but all four declared
canonical hashes differ from `hexagent.canonical_json.canonical_sha256`. R104
therefore does not satisfy canonical identity/linkage under the referenced
project contract.
Required correction: an append-only correction must state the exact
canonicalization procedure and bind recomputed evidence, matrix, extension and
registry-root hashes. Do not rewrite R104 history.

### R104-PREDICATE-02 — independently unbound policy operands are not explicit gates

Severity: HIGH.
Artifact/section: R104 evidence `contract.mesh_admissible_formula_bound` and
document “Explicit production admission predicate”.
Independent finding: the formula names `convergence_rule_bound` and
`resource_policy_bound`, but R104 separately records
`headroom_rule_bound=false`, `reference_policy_bound=false`,
`wall_acceptance_rule_bound=false`, `normalized_real_case_mesh_descriptor_bound=false`,
`production_reference_oracle_required=UNBOUND`, and real-case `C_round` as
`ADDITIONAL_AUTHORITY_REQUIRED`. R104 does not define `mesh_profile_authority_valid`
or `convergence_rule_bound` as a composite that is false whenever each of these
slots is unresolved. Current admission remains false, but the future predicate
shape does not prove that each declared unbound operand necessarily blocks.
This is a fail-closed contract ambiguity, not authorization to select a value.

Required correction: define the relevant composite validity semantics or
explicitly gate every applicable policy decision. For a policy that is not
applicable to a case/profile, require an authority-bound `NOT_APPLICABLE`
disposition rather than treating absence as true. Include rounding applicability
in the resolved numerical/mesh profile decision. Do not add numeric thresholds,
counts, caps or tolerances.

### R104-XFER-07 — headroom basis overstates existing TASK172 authority

Severity: MEDIUM.
Artifact/section: R104 transfer matrix row `one_later_headroom_level`.
Independent finding: the disposition is appropriately
`ADDITIONAL_AUTHORITY_REQUIRED`, but its transfer basis incorrectly states that
TASK172 requires headroom evidence. The reviewed TASK172 schema requires
consecutive evidence and other criterion fields, not a headroom count/slot.

Required correction: retain the unbound disposition, and describe headroom as
an R104 proposed project-contract slot or a possible future criterion—not as an
inherited TASK172 requirement. No value of one is transferable.

## Remaining real-case quantitative gaps

These remain unbound and are not closed by this review:

| Gap ID | Current status | Why unbound | Required evidence / dependency |
|---|---|---|---|
| `REAL-MESH-INITIAL` | UNBOUND | No reviewed starting resolution or case-bound profile rule | A separately reviewed real-case initial-mesh rule, after geometry/support normalization is decided |
| `REAL-MESH-REFINEMENT` | UNBOUND | TASK171 permits explicit subdivision within native intervals but selects no split operator/ratio | Reviewed deterministic operator preserving native events and support/area/length identity |
| `REAL-MESH-CONVERGENCE` | UNBOUND | R103's numerical thresholds are synthetic-only | Real-case observable/error budget, metrics and acceptance thresholds; depends on reference, wall and precision treatment |
| `REAL-MESH-HEADROOM` | UNBOUND | R103's later-level rule is fixture-specific; TASK172 does not require headroom | A separately justified real-case criterion, if selected; first correct R104's source attribution |
| `REAL-MESH-RESOURCE` | UNBOUND | Synthetic caps 32/64/128/256 do not generalize; 4096 is a raw-record guard | Scale/runtime/memory evidence and reviewed resource policy |
| `REAL-MESH-REFERENCE` | UNBOUND | R102 is a synthetic validation oracle, not a real-case reference producer | Authority-bound choice of reference comparison policy and, if used, case-specific producer/uncertainty propagation |
| `REAL-MESH-WALL-ACCEPTANCE` | UNBOUND | Wall observable identities are known; production comparison/stopping rule is not | Case-bound wall state producer, extrema metric, precision floor and accepted comparison rule |
| `REAL-MESH-ROUNDING` | UNBOUND | R98 `C_round=1.0` is limited to fixed synthetic training/holdout scope | Independent real-case applicability authority or an authority-bound alternative roundoff disposition |
| `REAL-MESH-NORMALIZATION` | UNBOUND | No approved cells-per-support/compartment or normalized-width descriptor | Geometry-normalized mesh descriptor or an explicitly reviewed case-specific non-normalized alternative |

These gaps do not authorize a mesh study or production implementation.

## Review conclusion and governance

```ini
R103_SYNTHETIC_SCOPE_INDEPENDENTLY_CONFIRMED=true
EXISTING_REVIEWED_REAL_CASE_MESH_AUTHORITY_FOUND=false
SUPPORTED_TOPOLOGY_REVIEW_PASS=true
PHYSICAL_TO_CELL_MAPPING_REVIEW_PASS=true
MESH_IDENTITY_SCHEMA_STRUCTURAL_REVIEW_PASS=true
CANONICALIZATION_REVIEW_PASS=false
R103_TRANSFER_MATRIX_ROW_COUNT=14
R103_TRANSFER_MATRIX_INDEPENDENT_REVIEW_COMPLETE=true
R103_TRANSFER_MATRIX_ALL_ROWS_PASS=false
NO_HIDDEN_DEFAULTS_REVIEW_PASS=true
UNBOUND_POLICY_SLOTS_PRESERVED=true
CASE_LEVEL_AUTHORITY_GATES_PRESERVED_REVIEW_PASS=true
TYPED_FAILURE_VOCABULARY_REVIEW_PASS=true
RESULT=BLOCKED_REAL_CASE_MESH_ADMISSION_CONTRACT_INDEPENDENT_REVIEW
REAL_CASE_MESH_ADMISSION_CONTRACT_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
MESH_AUTHORITY_REAL_CASE_GENERALIZATION_BOUND=false
PRODUCTION_MESH_SELECTION_CONTRACT_BOUND=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TASK173_SOLVE_PERFORMED=false
TASK174_SOLVE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

Next minimal gate: `AUTHORIZE_TASK172_REAL_CASE_MESH_ADMISSION_CONTRACT_CORRECTION_ONLY`.
It should correct the hash procedure/linkage, make every applicable unbound
policy operand fail closed, and correct the headroom source attribution. It must
not set any production mesh parameter or promote real-case generalization.
