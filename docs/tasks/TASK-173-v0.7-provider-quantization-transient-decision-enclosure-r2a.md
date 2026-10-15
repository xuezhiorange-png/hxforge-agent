# TASK173 Provider-Quantization Transient Decision Enclosure R2A

## Disposition

```text
TASK_ID=STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2A_PARITY_AND_REPLAY_CORRECTION_R1
RESULT=PASS_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2A_AUTHORITY_CANDIDATE
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
PREDECESSOR_HEAD=6a52882cc3bf9a31bd1827c36a78cab14b3d3d34
R2A_RUNTIME_HEAD=5bd19b1829f2fea7757c3efb3398e9aab17c8a3d
R2A_RUNTIME_TREE=64fc2c4b5e1776610aa8a5e39bf0666455648f73
AUTHORITY_ID=V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A
AUTHORITY_CANONICAL_HASH=25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e
AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
AUTHORITY_ACCEPTED=false
PARENT_SIZING_AUTHORITY_PACKAGE_ID=V07-T173-SIZING-AUTHORITY-PACKAGE-R2
PARENT_SIZING_AUTHORITY_PACKAGE_HASH=750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9
QUALIFICATION_MATRIX_HASH=f9d5a2a0c8a462fedea2715b4e5a759d36bb2426ca2603b318660960c7eea86d
```

R2 remains an immutable failed candidate. Its independent review identified
outer-control-flow divergence, an evidence-head runtime guard mismatch, and a
malformed parent package hash input. R2A addresses those findings without
changing the physical/numerical policy. The corrected 64-character parent
package hash is bound consistently to the reviewed package, R2, and R2A.

## Shared production outer solver

The former production `_solve_outer_boundary` body is now the shared private
`_solve_outer_boundary_from_trial(trial_at)` state machine. Production supplies
its native `_outer_trial` callback and delegates; R2A supplies only its
transient trial evaluator. The helper retains the original endpoint
classification, residual checks, monotonicity checks, 80-digit midpoint,
binary64 collapse disposition, terminal tolerance and ULP floor, blocker
propagation, and resource-exhaustion behavior. No numerical constants or
production decision semantics changed.

Focused helper regressions cover endpoint and midpoint classifications,
hard-blocker propagation, negative residuals, terminal success, all midpoint
collapse outcomes, and resource exhaustion. The Rating/TASK174 focused suite
passed with 81 tests. Ruff, format, mypy, manifest D==M, lock check, and
`git diff --check` passed on the runtime change. The shared-control-flow parity
runner reports:

```text
QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_SOURCE=SHARED_PRODUCTION_HELPER
QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY=PASS
qualification_independent_while_loop_count=0
MIDPOINT_COLLAPSE_STRADDLE_NEGATIVE_TEST=PASS
```

The runtime commit is `5bd19b1829f2fea7757c3efb3398e9aab17c8a3d`, directly
parented by the authorized review head. It contains only the shared-helper
refactor and its focused tests.

## Reference identity

The full native reference Rating replay completed successfully against the
runtime source bytes now committed at the R2A runtime head. Its captured output
and input binding are preserved in
`evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-reference-rating-identity.json`.
The replay receipt binds the raw shell-flow input bytes, native TASK174 result,
request identity, successful result identity, runtime commit/tree, and exact
stdout:

```text
REFERENCE_TASK174_RESULT_HASH=ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419
REFERENCE_TASK173_REQUEST_HASH=77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed
REFERENCE_TASK173_RESULT_HASH=fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
REFERENCE_TASK173_STATUS=VALIDATED
REFERENCE_RATING_CAPTURE_CANONICAL_HASH=e8ff2a8a3da42032231b4876fc5c59cabcf5f6fa735f5a25df0e3b7e7a79cac0
REFERENCE_RATING_CAPTURE_RAW_SHA256=1ab16eee5bb936490de6a7d76ac5a4fe247c3ba4b64f47408ade97f769bcd62d
```

The qualification/replay runners revalidate the receipt hash, raw input SHA,
native TASK174 replay, and native Task173 request hash. They do not launch a
second multi-hour full reference Rating replay.

## Frozen five-case qualification

The cases remain TRAIN_A `.215`, TRAIN_B `.220`, H1 `.225`, H2 `.275`, and H3
`.350`; no candidate was reselected. Each final accepted trajectory was rerun
from the beginning with transient enclosure disabled and contains five
`EXACT_VALID_POINT_ROOT` cells. Full face states, accepted cells, RatedCell
payloads, Task172 request/result identities, mesh projections, outer search,
energy closure, wall extrema, minimum approach, and numerical-hole receipts
are retained in the machine evidence.

| Case | Cut | Candidate ID | Accepted n=1 duty (W) | Transient endpoint events / certificates | Accepted enclosures | Trajectory hash |
|---|---:|---|---:|---:|---:|---|
| TRAIN_A | 0.215 | `adeab5b1-a339-5eb3-aa66-011ffe49bac0` | 51992.108449169418 | 2 / 1 | 0 | `c865fabcd42658368fa3eb10a4e6edbd1124a1ba649dfc7cd650ae7bc7358843` |
| TRAIN_B | 0.220 | `e152cca9-fd5d-59ca-9b46-1df574eee841` | 51917.490892674400 | 6 / 3 | 0 | `b2e579624aae8a1a09a89c6236e3dc4ee40bf8aa952681ef884ee5f8ff179cfc` |
| H1 | 0.225 | `68a99368-a518-5482-b9df-4bc3357edea9` | 51840.916860226334 | 6 / 3 | 0 | `c76b049b491235066ed8ea8ae005c3e125b359b8fd8fc1dd91938c8ff1d1bf50` |
| H2 | 0.275 | `aa70248a-9f76-542d-bc77-1e935b9c32d4` | 50962.180300173039 | 2 / 1 | 0 | `52b93a79a30693a843fab7cb7575560ecebc3051512fdf987d6eef040aa839d0` |
| H3 | 0.350 | `f3e14759-e05b-5088-bfb5-b6e16e918267` | 49197.902092283937 | 0 / 0 | 0 | `73a0e5e199d452ba7e8a6dc7239c43f1f9bd857028c9722a6db9e9a1a444698a` |

There are eight transient enclosure decisions represented by 16 endpoint
continuations. All eight certificates prove classification and outer-action
invariance. Five valid-branch certificates additionally prove equal
midpoint-collapse dispositions and temperature ULP floors; the three
low-side certificates explicitly mark those fields `NOT_APPLICABLE`. No
nested enclosure occurred. Reference n=1 produced zero transient and zero
accepted enclosures.

The authority preserves the ordinary point-root contract
`F(q)=q-q_TASK172(q)`, VALID Task172 evaluations, and `abs(F(q)) <= 1e-6 W`.
Enclosure is permitted only for transient outer-search decision invariance.
Transient q/T spans are diagnostics/provenance only; accepted cell/mesh floors,
energy tolerance, and final physical uncertainty remain unchanged. Accepted
trajectories contain no provider enclosure.

## H2 numerical-hole addendum

H2 outer iteration 11 at shooting enthalpy
`107469.424689940170810546875 J/kg` retains the support-4
`BLOCKED_RESIDUAL_ACCEPTANCE` point at `8600.8670719301 W`. The blocked point
remains blocked. The exact request/result identities for the blocked point and
both valid neighboring points are captured and replayed; they are not provider
enclosure endpoints. The final R2A H2 evidence hash is
`df9c3ec6230f5c7261371dbf3194d70f63556441cb61756f88ea572d063c8e20`.

## Replay results

The R2A replay and the separate H2 replay both passed from the committed
runtime head. R2A replay verified the authority, qualification matrix,
16 event hashes, 57 endpoint request/result identities, 16 continuation
hashes, 8 outer-decision certificate hashes, and 5 trajectory hashes. H2 replay
verified all three blocked/neighbor endpoint identities and H2 outer-trial
cross-bindings.

```text
R2A_AUTHORITY_HASH=25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e
QUALIFICATION_MATRIX_HASH=f9d5a2a0c8a462fedea2715b4e5a759d36bb2426ca2603b318660960c7eea86d
EVENT_HASH_REPLAY_COUNT=16
ENDPOINT_REQUEST_RESULT_REPLAY_COUNT=57
CONTINUATION_HASH_REPLAY_COUNT=16
OUTER_DECISION_CERTIFICATE_HASH_REPLAY_COUNT=8
TRAJECTORY_HASH_REPLAY_COUNT=5
QUALIFICATION_STATUS=PASS
ALL_REPLAY_PASS=true
ALL_H2_HOLE_REPLAY_PASS=true
```

## Scope and next gate

```text
PRODUCTION_R2A_ENCLOSURE_IMPLEMENTED=false
TASK173_RATING_COMPLETE=true
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2A_INDEPENDENT_REVIEW_R1
NEXT_GATE_EXECUTED=false
```

R2A remains proposed and unaccepted pending fresh independent review. This
qualification does not implement provider enclosure in production, complete
TASK173 Sizing, or authorize TASK175, PR readiness, or merge.
