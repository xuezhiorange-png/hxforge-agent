# TASK173 Provider-Quantization Enclosure Independent Review R1

**Result:** `FAIL_TASK173_CELL_ROOT_PROVIDER_QUANTIZATION_ENCLOSURE_INDEPENDENT_REVIEW`

**Task:** `STAGE3_TASK173_CELL_ROOT_PROVIDER_QUANTIZATION_ENCLOSURE_INDEPENDENT_REVIEW_R1_RETRY_AFTER_HASH_CONTRACT_RECOVERY`

**Reviewed head:** `4736d65288f706e3fc1c3348255afdfc3cb389ef`
**PR:** #283, OPEN / Draft
**Reviewer:** Codex / GPT-6, fresh thread `01a10c3e-8a69-7383-8760-e24db6982f3f`
**Independence:** `SELF_APPROVAL=false`; `CANDIDATE_AUTHOR_SELF_APPROVAL=false`

This was the same substantive review retried after recovery of the canonical hash contract. The prior attempt stopped at artifact integrity and produced no A–R finding. No enclosure implementation, Sizing, candidate Rating, production mesh, TASK175, PR readiness, or merge action was performed.

## Integrity and replay

The reviewer independently verified the exact Git archive, manifest, all 1,412 Git-tree paths, raw byte lengths, SHA256 digests, Git blob identities, and source-head membership. Artifact integrity passed. The immutable review bundle SHA256 is `6df43fdbe8ff4f6e090276970dd34d6969f245309fb09722da70e7f37d3f3d8c`; manifest SHA256 is `fb3155556517bdd3f3d0ba2fe537f4770cc742a009e03a3a903ffa56cd520b5d`.

In a writable copy of the exact snapshot, the reviewer executed the committed replay script using the locked environment. Authority hash, qualification-matrix hash, and all eight enclosure-event hashes matched. The reviewer inspected the script and `src/hexagent/canonical_json.py`, independently checked the preimages, and confirmed RFC 8785/JCS, `rfc8785==0.1.4`, recursive exclusion of `canonical_hash` and `mutable_review_comments`, NFC normalization, and SHA256. The previous `acade14b…` value is reproducible with Python's compact sorted `json.dumps`; this explains the serializer difference without faulting the earlier reviewer.

## Substantive verdict

The authority candidate remains unchanged and pending. The review fails because its transient enclosure representative can participate in an outer-boundary decision without a rule bounding the resulting uncertainty. This is distinct from point-root tolerance: the existing `1e-6 W` valid-point contract is not relaxed, and the eight event-local residual/span/floor calculations replay.

### Findings

1. **`TRANSIENT_OUTER_BOUNDARY_DECISION_UNCERTAINTY_NOT_BOUND`** — A transient `_solve_cell` enclosure representative can flow through `_valid_trajectory` into `_outer_trial`, affect feasibility/terminal classification, and update the outer bisection bracket and selected shooting enthalpy. Candidate provenance retains transient event hashes, but the authority does not state a decision-bound or fail-closed rule for uncertainty crossing those classifications. Zero enclosures in the final accepted n=1 mesh does not address this control-flow effect. Evidence: candidate projection `downstream_propagation` and `qualification_binding`; runtime `src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py` lines 1815–1819, 2053–2104, 2237–2268, 2304–2385.

2. **`ACCEPTED_TRAJECTORY_ENCLOSURE_UNCERTAINTY_PROPAGATION_NOT_BOUND`** — The candidate defines local duty/wall floors and downstream mesh classification, but does not fully bind how an enclosure-influenced downstream face state affects subsequent constitutive evaluations, accepted-trajectory observables, and final physical uncertainty. The transient-event sum of `0.000026550124 W` is deterministic provenance, but spans distinct trial enthalpies/supports and is not established as one accepted trajectory's physical uncertainty. Evidence: candidate projection `uncertainty_model`, `existing_roundoff_floor_combination`, `downstream_propagation`; runtime `task173_integrated_rating/service.py` lines 1210–1234, 1780–1784, 2132–2140, 2365–2399, 2617–2623.

3. **`COMPLETE_ENDPOINT_REQUEST_IDENTITY_REPLAY_NOT_ESTABLISHED`** — The stored endpoint request projections are compact diagnostic projections, not complete native candidate Task172 request-hash preimages. The pinned source head does not contain the candidate request/runtime modules used by the external runner; the committed Task172 projection at `task172_local_runtime/service.py` lines 121–189 follows the reference contract and includes fields not preserved in the diagnostic projection. The reviewer verified all 16 result hashes and the recorded request/result bindings, but could not independently replay the full candidate request identities required by Q15. This is not evidence that the recorded hashes are wrong; the replay preimage/contract is absent from the reviewed snapshot.

4. **`FULL_FIVE_CASE_N1_TRAJECTORY_EVIDENCE_NOT_PRESERVED`** — The five n=1 cases retain summaries and mesh hashes, but not the complete final cell/face states and identities required to inspect all 25 paired support closures and the H2 numerical-hole recovery trace. Stored summaries match the raw diagnostic log; they are not a complete independently replayable trajectory. Evidence: `qualification.qualification_matrix.cases` in the candidate evidence and the exact-head bundle contain no final cell/face payloads.

5. **`TASK174_CANONICAL_REDUCTION_FIX_NOT_PRESENT_AT_REVIEWED_HEAD`** — Captured H1 arithmetic supports grouped replay (`end_zone=inlet+outlet`, then `total=central+window+end_zone`) with zero differences and records the legacy flat difference `1E-47 Pa`. However, the committed TASK174 validator at `src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration/service.py` lines 132–140 still performs the flat four-term reduction, while native TASK166 groups end-zone and total at `bell_delaware/pressure_drop.py` lines 164–165. The claimed correction/regression resides only in the dirty parent implementation and cannot establish the reviewed source-head runtime. No tolerance is added or proposed here.

## A–R disposition

| Review item | Result |
|---|---|
| A. Existing point-root contract | PASS |
| B. Enclosure semantic status | PASS |
| C. Q1–Q15, including complete request replay | FAIL (Q15 not independently established) |
| D. Provider-coordinate exhaustion | PASS for the 32 captured endpoint coordinate pairs |
| E. Representative endpoint | PASS |
| F. Full-span duty uncertainty | PASS, 8/8 |
| G. Wall uncertainty | PASS, 8/8 |
| H. Existing/effective local floors | PASS for captured arithmetic |
| I. Mesh precision semantics | PASS |
| J. Transient outer-search effect | FAIL |
| K. Transient vs accepted uncertainty | FAIL |
| L. Outer-boundary decision uncertainty | FAIL |
| M. Accepted-trajectory uncertainty | FAIL |
| N. Uncertainty aggregation | FAIL |
| O. Energy balance | FAIL overall; inherited formula unchanged, enclosure sufficiency unbound |
| P. TRAIN/HOLDOUT identity and selection integrity | PASS |
| Q. Five complete n=1 trajectories | FAIL (summaries preserved, complete cell/face payloads absent) |
| R. Eight enclosure events | FAIL overall (event arithmetic/hashes replay; complete request identities not replayable) |
| Reference n=1 dormant behavior | PASS, limited to observed n=1 only; no full reference identity claim |
| TASK174 canonical reduction | FAIL to verify at reviewed head (correction absent from committed source) |
| Scope containment | PASS |

The eight event hashes, 16 endpoint result hashes, residual signs, q/PH adjacency, representative selections, full duty/wall spans, and local floor arithmetic independently replayed. The relevant pinned-source focused tests passed: 19 passed, 42 deselected. These checks do not cure the substantive authority/evidence findings above.

## Review lifecycle and next gate

The locked candidate projection remains `PROPOSED_AUTHORITY_REVIEW_PENDING` with `authority_accepted=false`; no candidate or qualification artifact was amended. Effective lifecycle remains pending and authority acceptance remains false.

```text
REVIEW_DECISION=FAIL
EFFECTIVE_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_PROVIDER_QUANTIZATION_ENCLOSURE_REVIEW_FAILURE
NEXT_GATE_EXECUTED=false
```

The exact machine-readable receipt, reviewer report identity, bundle hashes, replay results, A–R statuses, and findings are in `docs/tasks/evidence/TASK-173-v0.7-cell-root-provider-quantization-enclosure-independent-review-r1.json`.
