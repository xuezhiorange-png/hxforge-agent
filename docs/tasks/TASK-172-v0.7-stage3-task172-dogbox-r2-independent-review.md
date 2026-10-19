# TASK172 fail-only dogbox fallback R2 authority independent review

```ini
TASK_ID=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_R2_INDEPENDENT_REVIEW
MODE=INDEPENDENT_AUTHORITY_REVIEW_ONLY
RESULT=FAIL_FAIL_ONLY_DOGBOX_FALLBACK_R2_AUTHORITY_INDEPENDENT_REVIEW
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
REVIEWED_HEAD=717c2d07e676231fbcd3b4ea474a9bd5475b4320
REVIEW_SOURCE=Fresh-context Codex sub-agent reviewer Harvey; no inherited conversation context
SELF_APPROVAL=false
CANDIDATE_AUTHOR_SELF_APPROVAL=false
```

## Locked review object

The review was limited to authority `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R2`, proposed canonical hash `a3e04e95965d6432d4d54aa2dfed7bf5b9d5995ef98c4bbb7e87208545160318`, and R2 evidence hash `3ea204e2d1ae3a887fa8e001c3bb767d97b8b1632c9734df058783a90af0d6a9`. The reviewer made no candidate edits and ran no solver, numerical characterization, portability matrix, production mesh, or TASK175 work.

## Disposition

The R1 finding `NUMERICAL_OUTPUT_PORTABILITY_ENVELOPE_NOT_FROZEN` is closed: R2 prospectively declares the q/Twi/Two projection and owner-scoped limits, and explicitly says observed deltas did not select those limits. The reviewer verified the proposed authority and evidence hashes, the local raw-artifact hash references, the cited Linux JUnit provenance and matching Python 3.11/3.12 projections, the n=16 comparison, the 68-row maximum-bound proof, and the inherited fail-only architecture.

The review nevertheless fails on one remaining contract ambiguity. The q rule allows a `1e-8 W` absolute floor, while the exact-zero clause only specifies the case where both values are zero. For example, q values `0 W` and `1e-9 W` satisfy the stated absolute delta allowance, although one is exact physical zero and the other is nonzero. The seven recorded target comparisons do not exercise this boundary. The candidate therefore does not state whether cross-platform exact-zero status must match or whether a zero/nonzero pair within the floor is permitted. The reviewer requires that behavior to be explicit before accepting the portability contract.

This is a substantive authority clarification, not a receipt-only correction. Per the review mandate, the candidate was not modified and no new authority revision was created. R2 remains proposed and unaccepted.

## Verified controls and scope

The R2 evidence retains the fail-only architecture: unchanged R94 TRF primary at 6 nfev / 24 callbacks; fallback only for replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE`, using the original R94 deterministic seed and dogbox at 6 / 24; baseline-valid and non-residual blockers bypass fallback; fallback remains fail-closed; and the original R98 is independently required. The portability envelope is separate from solver stopping and R98 acceptance. No R94, R98, C_round, constitutive equation, property domain, production code, test, fixture, dependency, lockfile, workflow, or registry change was made.

Focused TASK172/TASK173 regression tests passed with the candidate characterization-matrix test excluded. Ruff, format, mypy, manifest D==M, pip-audit, and `uv lock --check` passed. Full shell-tube and HTTP/API suites were not run locally; exact-head CI is required after this review receipt commit.

```ini
R1_REVIEW_FINDING_CLOSED=true
R2_REVIEW_FINDING=EXACT_ZERO_Q_PORTABILITY_STATUS_UNSPECIFIED
AUTHORITY_ID=V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R2
AUTHORITY_CANONICAL_HASH=a3e04e95965d6432d4d54aa2dfed7bf5b9d5995ef98c4bbb7e87208545160318
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
CANDIDATE_MODIFIED=false
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
NEXT_GATE=OWNER_DIRECTION_REQUIRED_BEFORE_ANY_CANDIDATE_AMENDMENT
STOP=true
```
