# TASK173 Provider-Quantization Transient Decision Enclosure R2 Independent Review R1

**Result:** `FAIL_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_INDEPENDENT_REVIEW`

**Task:** `STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2_INDEPENDENT_REVIEW_R1`

**Reviewed head:** `9172befb3566f9acb47488232f1dc01959297606`
**Runtime source:** `b1b9d676c693e09d740c47b642198b5e4f543409` (`b0cfbdb7c4a9c3136fda317723fb5eab30c40e1e`)
**PR:** #283, OPEN / Draft
**Reviewer:** Boole (OpenAI GPT-6 / Codex), reviewer context `01a10e1e-4b7c-7082-b2f8-e7547ea9b6cf`
**Independence:** `REVIEWER_CONTEXT=FRESH`; `SELF_APPROVAL=false`; `CANDIDATE_AUTHOR_SELF_APPROVAL=false`

## Decision

The R2 candidate is **not accepted**. Its recorded numerical data and endpoint identities are substantially replayable, and the transient-only/accepted-path separation is coherent on the five recorded cases. However, the qualification runner is not control-flow equivalent to the production outer solver at precision-floor and resource-exhaustion branches, despite control-flow parity being a hard review requirement. In addition, the two committed replay entrypoints cannot execute from the mandated reviewed HEAD: both stop at an exact runtime-HEAD guard before replaying their evidence.

The R2 candidate projection, qualification evidence, runtime, and prior R1 review were not modified. This review did not implement the R2 policy, run full Sizing, execute TASK175, or change PR readiness/merge state.

## Exact-artifact integrity and replay

The immutable bundle was materialized from exact Git objects, with the runtime source taken from `b1b9d676c693e09d740c47b642198b5e4f543409` and review/evidence files from `9172befb3566f9acb47488232f1dc01959297606`. All 311 manifest entries matched source commit, Git blob, mode, raw byte length, and raw SHA-256. The archive members matched the materialized bytes.

```text
ARTIFACT_FILE_INTEGRITY=PASS
REVIEW_BUNDLE_FILE_COUNT=311
REVIEW_BUNDLE_SHA256=c6dcde773e8554369de3db2c25bf16f1cd9a1b5c5c03d47d92106083c409b45d
MANIFEST_SHA256=f273708d8f1d8af88e0ebd8a6d2975bbf7460f3779522f2d321a443ed209b6b3
```

The authority and qualification-matrix canonical hashes were independently confirmed from the committed projections. Supplemental replay using the committed runtime models and native identity functions verified 16 event hashes, 57 endpoint request/result identities, 16 continuation hashes, 8 outer-decision certificates, and 5 accepted-trajectory hashes. This supplemental replay does not make the required committed entrypoints executable at the reviewed HEAD.

The required commands were run exactly from the reviewed checkout:

```text
R2 replay: FAIL
RuntimeError: RUNTIME_HEAD_MISMATCH:9172befb3566f9acb47488232f1dc01959297606

H2 replay: FAIL
AssertionError: RUNTIME_BASELINE_MISMATCH:9172befb3566f9acb47488232f1dc01959297606:24fb55837e7cbb52dfa0a21f3e6e7a365f37a237
```

The qualification runner requires the current `HEAD` to equal the runtime snapshot head `b1b9d676…`; the H2 replay likewise requires the runtime commit/tree tuple rather than accepting the specified descendant review head whose runtime paths are unchanged. Therefore `R2_REPLAY_ALL_PASS=FAIL_AT_REVIEWED_HEAD`, even though the stored replay-verification object and supplemental native-model replay pass.

## Findings

### `QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_DIVERGENCE`

The required parity audit fails. In production `task173_integrated_rating/service.py`, outer midpoint collapse is handled by checking the terminal tolerance and temperature ULP floor, then returning or raising the corresponding structured `Stage3Failure`; outer iteration/resource exhaustion also has a distinct structured `Stage3Failure` code. In the qualification runner, the analogous midpoint-collapse path raises a generic `RuntimeError("OUTER_BOUNDARY_PRECISION_FLOOR_REACHED")`, and iteration exhaustion raises a generic `RuntimeError` rather than the production failure. These paths did not occur in the five recorded cases, but the review explicitly requires parity for precision-floor and resource-exhaustion branches, not only agreement on observed trajectories.

Evidence locations: production outer solver at `src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py:2638` and qualification outer loop at `docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py:932`.

```text
QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY=FAIL
```

### `R2_REPLAY_ENTRYPOINT_RUNTIME_HEAD_GUARD_MISMATCH`

Both committed replay commands fail before replaying data because their head guards pin the runtime commit, while this review is required to execute them at the exact evidence head `9172bef…`. A self-contained review replay must support an evidence descendant when the bound runtime paths are unchanged, or otherwise explicitly provide a committed exact-head replay contract. No inline workaround or candidate edit was made.

### Review-input discrepancy: parent sizing package hash

The task text supplies `750c1f76953f46b63de90f2c21302160746e8904fc61227538397e69b8501a9`, which is 63 hexadecimal characters and therefore not a SHA-256 value. The exact committed package and R2 authority projection bind the 64-character value `750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9`. The committed candidate matches the committed package; this review preserves both literals as observed and does not silently normalize the prompt value.

## Substantive review matrix

| Area | Result | Review disposition |
|---|---|---|
| Artifact integrity and exact Git membership | PASS | 311/311 bundle entries verified. |
| Authority and matrix projection | PASS | Hashes match the committed projections. |
| R2/H2 committed replay entrypoints | FAIL | Both stop at runtime-head guards at the mandated review HEAD. |
| Supplemental events/endpoints/continuations/certificates/trajectories | PASS | 16 events, 57 endpoint request/result identities, 16 continuations, 8 certificates, 5 trajectories replayed with native model/hash helpers. |
| Runtime ancestry, source binding, and V3 provenance | PASS | Runtime commit is an ancestor; runtime paths match; V3 provenance hash recomputes. Historical byte equivalence was not required. |
| `a655…` to runtime-repair diff | PASS | Three paths; mypy edits are typing/narrowing changes with no observed schema/canonical-projection change; one test registration, no CI policy weakening. |
| Ordinary point-root contract and transient-only authority scope | PASS | `abs(F) <= 1e-6 W` remains; accepted-path enclosure is forbidden. |
| Q1–Q15, provider exhaustion, and actual endpoint branches | PASS on recorded events | All 16 event records replay; left/right continuations use their respective actual endpoint evaluations. |
| Outer-classification, terminal-tolerance, and action invariance | PASS on 8 recorded certificates | All recorded left/right decisions agree; representative branch does not decide action. |
| Qualification/production outer control-flow parity | **FAIL** | Precision-floor and resource-exhaustion handling differ as described above. |
| Transient diagnostics vs accepted physical uncertainty | PASS | Transient spans are provenance/decision diagnostics only. |
| Accepted trajectories and exact roots | PASS | Five trajectories, 25 accepted cells, zero accepted enclosures; H2 hole point remains blocked. |
| Full five-case and H2 hole evidence | PASS at data level | All five trajectory hashes and H2 blocked/neighbor identities replay. |
| TASK174 canonical grouped reduction/reference identity | PASS | Grouped replay and reference hash `ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419` verified; TASK166 formula unchanged. |
| Scope and resource caps | PASS | No accepted-path/nested/domain expansion or resource-cap increase found. |

The recorded case trajectories are TRAIN_A `.215`, TRAIN_B `.220`, H1 `.225`, H2 `.275`, and H3 `.350`; each contains five accepted cells and zero accepted provider enclosures. H2's blocked residual-acceptance point remains blocked, with both valid neighbors and the outer-trial cross-binding present in the supplemental replay.

## R1 finding closure and lifecycle

The R2 evidence addresses the five R1 findings at the data/contract level: two-branch outer-decision rules are stated; transient spans are excluded from physical acceptance; full endpoint projections are preserved and supplemental replayed; all five accepted trajectories and H2 hole evidence are present; and TASK174 grouped reduction is in the committed runtime. This does not cure the R2 qualification runner's control-flow mismatch or its replay entrypoint guards.

```text
REVIEW_DECISION=FAIL
EFFECTIVE_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
PRODUCTION_CODE_CHANGED_BY_REVIEW=false
PRODUCTION_R2_ENCLOSURE_IMPLEMENTED=false
SIZING_EXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_TRANSIENT_DECISION_ENCLOSURE_R2_REVIEW_FAILURE
NEXT_GATE_EXECUTED=false
```

Exact-head CI is run after this receipt commit; its run identity and outcome are returned separately with the final review receipt so the tested head is unambiguous.
