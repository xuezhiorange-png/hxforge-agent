# TASK172 fail-only original-seed dogbox fallback candidate adjudication R1

Result: `BLOCKED_PORTABILITY`. This is a diagnostic review of a proposed architecture, not a production solver correction or a new accepted numerical authority.

## Scope and frozen authority

- PR #283 remains Open/Draft; evaluated candidate-test HEAD: `86849841a5314f6ee82eebc117ece8f969829e06`.
- Authorized source HEAD: `a1473d4336ecc67564aa0b4cf0c0511d21a3aaeb`.
- R94 profile hash remains `81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec`.
- R98 overlay hash remains `54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78`; `C_round=1.0`.
- Production source, TASK172 acceptance, R98 bounds, constitutive equations, property domain, TASK173 root logic, R3 endpoint rule, zero-q rule, mesh policy, dependencies, lockfile, and workflows are unchanged.
- The proposed identity `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-CANDIDATE-R1` is diagnostic-only; it is not accepted authority.

## Candidate evaluated

The test-side candidate runs frozen R94 TRF first (6 `nfev`, 24 callback cap). It invokes dogbox only after a replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE`, starts dogbox from the original deterministic R94 seed, and keeps the same request, property provider, equations, and original R98 bounds. The tested fallback budget was dogbox 6 `nfev` / 24 callbacks, the lowest tested tier. No production source implements this path.

On local macOS/Python 3.14.5, all six fixed n=32 requests were residual-acceptance holes under baseline TRF; dogbox from the original seeds produced replay-valid candidate result projections satisfying all three unchanged R98 bounds for 6/6. Repeated dogbox runs reproduced each local candidate result hash/ID. Total observed fallback work was 23 `nfev` and 92 callbacks.

On Linux CPython 3.11.16 and 3.12.14, for both PR-head and merge-ref, those same six requests were already `VALID_TASK172_RESULT` under baseline TRF. Therefore the fallback was correctly bypassed 6/6 times. The Linux TRF hashes match exactly across all four CI environments, but differ from the local dogbox hashes for all six same-input requests. Final classifications and R98 acceptance agree (`VALIDATED`/PASS); the chosen solver path, accepted numerical values, property snapshot identities, and result hashes do not.

## Valid-result preservation and portability

The preservation corpus contains 68 fixed request projections: 13 predecessor n=16 upper-target requests, 25 fresh n=8 requests, 25 fresh n=16 requests, and 5 n=32 outer-iteration-23 requests. It includes the previously identified valid request `fd9287e7200cc1fa723ecfeef31067d907a484bf18558b05a8488e5ed6e90cb9`.

| Runtime | Baseline valid | Residual blockers in corpus | Fallback on baseline-valid | Baseline hashes preserved | Candidate result hashes matching local reference |
|---|---:|---:|---:|---:|---:|
| macOS 3.14.5 | 68/68 | 0 | 0 | 68/68 | 68/68 |
| PR-head Linux 3.11.16 | 66/68 | 2 | 0 | 66/66 | 0/68 |
| PR-head Linux 3.12.14 | 66/68 | 2 | 0 | 66/66 | 0/68 |
| merge-ref Linux 3.11.16 | 66/68 | 2 | 0 | 66/66 | 0/68 |
| merge-ref Linux 3.12.14 | 66/68 | 2 | 0 | 66/66 | 0/68 |

The two Linux corpus holes are `75d7541da1252b4669b21f9a4a626dacb2d6a93c7c994146708e34262eee628a` and `9f61f89277ee66227cc7b700e8d43c2f8edc935f4adda162fe36ad85d090b7c2`; dogbox recovered both under original R98 at 4 `nfev` / 13 callbacks each. Their fallback result identities also differ from the local baseline-valid results for the same requests.

Thus the bypass safeguard works within each runtime, but the candidate's branch condition is environment-sensitive: a request can become a baseline TRF result on Linux and a dogbox fallback result on macOS. Across the 68 same-input corpus requests, none of the Linux final candidate hashes matched the local reference hashes. This is not a safe portable result-identity outcome under the reviewed cross-runtime numerical profile evidence, which recorded equal selected numeric-output matrix hashes across Python 3.11/3.12/3.14. The current candidate therefore does not satisfy the required cross-platform result identity condition.

## Historical n=16 upper endpoint

For request `22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970`, local baseline was `BLOCKED_RESIDUAL_ACCEPTANCE`; dogbox returned a valid candidate with `q=703.6847988973881 W` and `F(111.3949198456 W)=-592.2898790517881 W`. Linux baseline was already valid and bypassed fallback; its valid result gave `F=-592.2898790517623 W`. R3 authority was unchanged and its endpoint-hole trigger does not apply to the Linux valid endpoint. These observations are characterization only; neither extrapolation nor a blocked diagnostic was used as a physical result.

## Validity, identity, and bounded work

- Six local candidate projections replayed result hash and ID from the candidate result, support/cell identities, and property snapshot identities; repeated clean dogbox runs matched their full result projection.
- The four Linux candidate reports agreed exactly with each other for the 68 final result hashes and all six fixed target requests.
- Baseline-valid requests returned the original baseline object and did not call fallback. Synthetic non-residual blocker and invalid identity/hash tests also preserved the original blocker and did not invoke fallback.
- A per-request upper bound would be 12 `nfev` and 48 callbacks (R94 6/24 plus dogbox 6/24). This is bounded, but bounded work does not resolve the cross-platform branch/result identity split.
- No global dogbox profile or alternative architecture was evaluated or endorsed.

## Decision

The candidate demonstrates local 6/6 residual-hole recovery while preserving R98, but fails the required portable baseline classification/result identity evidence: all six n=32 inputs are fallback cases locally and bypass cases on Linux, and same-input output hashes diverge across macOS and Linux. The two additional Linux corpus holes reinforce that R94 residual-acceptance classification is runtime-sensitive. Do not implement this fallback under the proposed authority yet.

Recommended next gate: `STAGE3_TASK172_NUMERICAL_PROFILE_PORTABILITY_REASSESSMENT`. It should first adjudicate the supported-runtime numeric-output/result-identity contract and a portable solver-path policy. This receipt does not authorize production correction, a mesh rerun, Ready, Merge, or TASK175.

Machine evidence: `docs/tasks/evidence/TASK-172-stage3-task172-fail-only-original-seed-dogbox-fallback-portability-and-validity-adjudication-r1.json`.

## Validation and lifecycle

- Candidate harness CI run `36962301921` was exact on test-harness HEAD `86849841a5314f6ee82eebc117ece8f969829e06`: 50 jobs, 45 success, 5 skipped, 0 failed/cancelled; all four PR-head/merge-ref Python 3.11/3.12 shards passed within the 540-second runtime budget.
- Local focused TASK172/TASK173 tests, full shell-tube suite, HTTP/API tests, Ruff, format check, CI-scope mypy, manifest D==M, pip-audit, lock check, locked sync, and duplicate-key audit passed. The HTTP/API suite reported 21 passing tests. Pip-audit found no known vulnerabilities and skipped only the unpublished local package.
- The checked-in lockfile remains unchanged (SHA-256 `4783f2a07cd28b5a5c46402101f0570d3060f464fe850c63fc7ad5e069e68464`), with `urllib3==2.8.0` and `requests==2.34.2`.
- Repository changes for this closeout are limited to this adjudication record and its machine evidence. The candidate harness already present on the PR changes tests/fixtures only; no production code, dependency, lockfile, workflow, R94/R98 authority, or registry change was made.
- The evidence commit's own exact-head CI receipt is recorded in PR metadata after that run; no follow-up repository commit is needed for the CI run ID.

Lifecycle: no production mesh was run, no TASK173 production result was minted, mesh admission remains false, TASK175 was not performed, and the PR remains Draft. Next gate is `STAGE3_TASK172_NUMERICAL_PROFILE_PORTABILITY_REASSESSMENT`.
