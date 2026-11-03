# TASK172 fail-only dogbox fallback authority independent review R1

```ini
TASK_ID=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_AUTHORITY_INDEPENDENT_REVIEW_R1
MODE=INDEPENDENT_AUTHORITY_REVIEW_ONLY
RESULT=FAIL_FAIL_ONLY_DOGBOX_FALLBACK_AUTHORITY_INDEPENDENT_REVIEW
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
REVIEWED_HEAD=04fd92450905a640bb3c228f982e31e7b1bd9b95
REVIEW_SOURCE=Fresh-context Codex sub-agent reviewer Popper; no inherited conversation context
SELF_APPROVAL=false
CANDIDATE_AUTHOR_SELF_APPROVAL=false
```

## Review object and evidence

The review was limited to `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R1`, proposed canonical hash `e72efc573a39710584bd342a6287655056525b3dc38e3e81bca100844b4f81f0`, and corrected candidate evidence hash `1e8b01c007b7b44abe9d7b12415ba95c54146b0ad7cf47eaf965e2a7e1ad3c9e`. The candidate and authority hashes were reproduced using the repository evidence convention (sorted-key compact JSON, excluding the evidence `canonical_hash` field for the evidence digest). The identity-contract evidence digest also reproduced as `d9c44837a38bc66a6372e32b3d7a5dfba7a8a09ca049dc29dab06fa968b3d7b2`.

The reviewer checked the proposed fallback overlay, lineage, platform-native identity contract, and summarized characterization evidence. No solver, numerical experiment, production mesh, or TASK175 action was run. The reviewer returned `BLOCKED_REVIEW_EVIDENCE_DEFECT` because the candidate lacked a required portability criterion. Under this task's rule that a candidate requiring substantive modification must receive `FAIL`, the final review disposition is `FAIL`.

## Finding

The already-adjudicated portability contract requires cross-platform numerical outputs to lie within a separately frozen, prospectively reviewed numerical-output envelope. It explicitly states that observed deltas are characterization, not tolerances. See the identity-contract adjudication, lines 16 and 101.

The candidate's `proposed_authority.portability` projection requires same-environment exact replay and lists semantic invariants, but does not define or bind a numerical-output envelope. Its recorded cross-platform deltas therefore cannot satisfy that inherited requirement. Adding an envelope would change the proposed authority projection and canonical hash; it is a substantive candidate change, not a clerical receipt correction. This review does not define that envelope or create an R2 candidate.

Consequently, the proposed authority is not accepted. The candidate lifecycle remains `PROPOSED_AUTHORITY_REVIEW_PENDING`; no implementation or next gate is authorized by this receipt.

## Checks that did not identify additional blockers

- The three CI lineages are distinct and exact-head verified: characterization HEAD `86849841a5314f6ee82eebc117ece8f969829e06` / CI `36962301921` SUCCESS; historical dogbox portability HEAD `8d8666826f222f052270ec7fa5d2e8111c853969` / CI `36965219941` SUCCESS, with its old `BLOCKED_PORTABILITY` conclusion superseded; identity-contract HEAD `dc2eac0cf39d73645cab170673dbfdd6ed065886` / CI `36973198114` SUCCESS.
- The candidate is a narrow overlay: R94 TRF primary remains 6 nfev / 24 callbacks; fallback is only for replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE`, starts from the original R94 deterministic seed, and uses dogbox 6 / 24. Baseline-valid calls bypass fallback. The candidate requires original R98 acceptance and fail-closed fallback behavior; no R94, R98, C_round, constitutive equation, or property-domain change is proposed.
- The evidence reports the six n=32 targets, the 68-request representative corpus, same-environment exact replay, seven non-residual guards, and matching n=16 final semantics. These do not replace the missing portability envelope and are not claimed to prove the full production domain.

## Validation

Local review-scope checks passed: focused TASK172/TASK173 tests (excluding the candidate characterization-matrix test to avoid repeating numerical characterization), Ruff, Ruff format check, CI-scope mypy, manifest D==M (259/259), pip-audit, `uv lock --check`, and `uv sync --locked --all-extras` (71 packages). The duplicate-key audit passed for the review, candidate, and identity-contract evidence JSON files. Locked dependency versions remain `requests==2.34.2` and `urllib3==2.8.0`; `uv.lock` SHA-256 remains `4783f2a07cd28b5a5c46402101f0570d3060f464fe850c63fc7ad5e069e68464`.

Exact-head CI is run after the review-receipt commit; its run ID and result are recorded in the PR closeout, without a follow-up repository commit.

## Disposition and boundaries

```ini
REVIEW_FINDING=NUMERICAL_OUTPUT_PORTABILITY_ENVELOPE_NOT_FROZEN
REVIEW_RESULT=FAIL
AUTHORITY_ID=V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R1
AUTHORITY_CANONICAL_HASH=e72efc573a39710584bd342a6287655056525b3dc38e3e81bca100844b4f81f0
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
CORRECTION_IMPLEMENTED=false
PRODUCTION_MESH_REEXECUTED=false
REAL_CASE_MESH_ADMISSIBLE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
FIXTURES_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILE_CHANGED=false
WORKFLOWS_CHANGED=false
REGISTRY_CHANGED=false
NO_NEW_NUMERICAL_EXPERIMENTS=true
STOP=true
```

The candidate must not be promoted or implemented from this review. Any revised portability bound requires a separately authorized candidate revision and independent review; neither is performed here.
