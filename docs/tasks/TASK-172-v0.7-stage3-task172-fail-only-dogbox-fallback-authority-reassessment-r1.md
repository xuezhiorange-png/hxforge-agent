# TASK172 fail-only dogbox fallback authority reassessment R1

## Decision

`PASS_FAIL_ONLY_DOGBOX_FALLBACK_AUTHORITY_CANDIDATE_PENDING_INDEPENDENT_REVIEW`

This is an evidence-based reassessment of the already executed candidate characterization under the adjudicated platform-native result identity contract. It is not production approval or implementation. The proposed authority is `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R1`, lifecycle `PROPOSED_AUTHORITY_REVIEW_PENDING`, `AUTHORITY_ACCEPTED=false`.

The predecessor label `BLOCKED_PORTABILITY` was based on requiring cross-platform exact result hashes. The subsequent identity-contract adjudication established that this was not a pre-existing contract requirement. The candidate evidence is therefore reassessed against same-environment exact replay plus cross-platform engineering-semantic portability; no numerical experiment was repeated.

## Evidence lineage and frozen authority

- Reused candidate characterization HEAD: `86849841a5314f6ee82eebc117ece8f969829e06`; its exact-head CI was run `36962301921` (50 jobs: 45 success, 5 skipped, 0 failed/cancelled; final gate success; all four Python/Linux shards within 540 seconds).
- Current reassessment source HEAD: `dc2eac0cf39d73645cab170673dbfdd6ed065886`.
- Since the candidate characterization HEAD, no candidate-relevant TASK172 production source, candidate harness, or its three fixtures changed. R94/R98, dependencies, `uv.lock`, and workflows are unchanged. Intervening repository changes are the two platform-native identity adjudication evidence files; registry remains unchanged.
- The separately reviewed identity-contract evidence hash is `d9c44837a38bc66a6372e32b3d7a5dfba7a8a09ca049dc29dab06fa968b3d7b2`. It sets result identity scope to `PLATFORM_NATIVE_RESULT_IDENTITY`, requires exact replay within a fixed environment, and does not require cross-platform exact result hashes.
- The reused candidate characterization evidence hash is `15f43a15896081839a6607b7bf45c4834b3273a55c704ba8835eb8ea2edf9e58`.
- R94 hash remains `81ae446af5e0009ce85c5fcb89d80534f9e2eaf36942b9d3a35aa0ff10a86aec`; R98 hash remains `54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78`; `C_round=1.0`.

## Proposed narrow authority overlay

Primary execution remains R94 TRF unchanged: linear loss; `ftol=1e-6`; `xtol=gtol=1e-12`; 2-point Jacobian; `diff_step=1e-5`; `max_nfev=6`; callback cap 24; exact trust-region solver; current deterministic seed, x-scale, and residual scaling.

The only proposed fallback trigger is a normally completed R94 solve whose request identity and request hash replay are valid, whose typed blocked result and blocked-result hash replay are valid, and whose sole failure is `BLOCKED_RESIDUAL_ACCEPTANCE`. Any other solver, resource, property, correlation, initialization, domain, physical, or identity/hash blocker bypasses fallback and remains fail-closed.

When triggered, the candidate runs dogbox from the original deterministic R94 algebraic seed—not the primary final iterate—with `max_nfev=6` and callback cap 24. Provider, request, properties, constitutive equations, correlations, wall model, state identities, R98 equations and operation-specific bounds remain unchanged. A candidate is usable only if it materializes as a valid Task172 local-result projection and independently passes the original R98 checks, request/result hash and ID replay, support/cell/wall identity replay, and property-snapshot identity replay. Dogbox failure, nonconvergence, resource exhaustion, another blocker, negative heat rate, invalid ordering, or residual failure remains a hard failure; diagnostic last iterates are never accepted.

Baseline-valid R94 results bypass fallback and are returned unchanged. The candidate evidence checks preservation of type, request/result identity, numerical outputs, residuals, property snapshots, and solver provenance. This is a fail-only overlay, not a global dogbox profile or R94 replacement.

## Reused characterization outcomes

- Six fixed n=32 target requests: macOS R94 had 6/6 replay-valid residual-acceptance blockers and original-seed dogbox recovered 6/6 under unchanged R98. Linux CPython 3.11 and 3.12 had 6/6 baseline-valid requests and correctly invoked fallback 0 times. The final six-way engineering-semantic comparison passes: `VALIDATED`, original R98 pass, heat-flow sign, physical wall ordering, property domain, and engineering authority all match. Local fallback used 23 total `nfev` and 92 callbacks.
- The 68-request preservation corpus is 13 predecessor n=16, 25 fresh n=8, 25 fresh n=16, and 5 n=32 outer-iteration-23 requests. macOS: 68/68 final validated and R98 pass; all 68 were baseline-valid, fallback invoked 0 times, and all 68 original result identities were preserved. Each Linux Python environment: 66 baseline-valid requests bypassed fallback with all 66 baseline identities preserved; the remaining 2 residual-acceptance cases recovered under original R98. Each environment finished 68/68 validated and R98-pass. The corpus is representative evidence, not proof of the entire production domain.
- Seven non-residual guard classes remain unchanged and invoke fallback zero times: nonconvergence, solver failure, solver resource exhaustion, property-temperature-domain exit, negative physical heat rate, physical wall ordering, and invalid request identity replay. Invalid residual-blocked identity and invalid blocked-result hash also invoke fallback zero times. Baseline-valid results are returned as the original object.
- Same-environment exact replay is supported by repeated local candidate projection/hash/ID replay and the Linux same-environment replay tests and reports. Within each Linux Python version, PR-head and merge-ref candidate report hash vectors match exactly. Cross-platform hashes need not match under the adjudicated platform-native identity scope; no rounding, quantization, tolerance-hash, or result-schema alteration is proposed.
- Historical n=16 upper request `22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970`: macOS baseline residual hole followed by candidate-valid result gives `F=-592.2898790517881 W`; Linux baseline-valid bypass gives `F=-592.2898790517623 W`. Both produce the existing valid-upper shell-capacity low-side physical classification. R3 authority and its trigger are unchanged.
- Proposed per-request maximum work is 12 `nfev` and 48 callbacks: frozen R94 6/24 plus conditional dogbox 6/24. This is a bounded tested budget, not a proof of a globally minimum budget.

## Authority disposition and boundaries

The evidence is sufficient to submit one proposed authority for independent review. It is not accepted authority. The proposed authority projection canonical hash is `e72efc573a39710584bd342a6287655056525b3dc38e3e81bca100844b4f81f0`; the corrected machine evidence canonical hash is `1e8b01c007b7b44abe9d7b12415ba95c54146b0ad7cf47eaf965e2a7e1ad3c9e`. The machine evidence distinguishes the candidate characterization CI (`36962301921`, HEAD `86849841a5314f6ee82eebc117ece8f969829e06`), dogbox portability predecessor CI (`36965219941`, HEAD `8d8666826f222f052270ec7fa5d2e8111c853969`, `BLOCKED_PORTABILITY` adjudication), and platform-native identity-contract closeout CI (`36973198114`, HEAD `dc2eac0cf39d73645cab170673dbfdd6ed065886`, CI `SUCCESS`, adjudication `PASS_PLATFORM_NATIVE_IDENTITY_CONTRACT`). No production source, tests, fixtures, numerical policy, authority registry, dependencies, lockfile, or workflow were changed by this reassessment. The existing diagnostic harness and fixtures are predecessor material and remain byte-identical; no candidate characterization was rerun.

Reassessment-local focused TASK172/TASK173 modules passed, excluding only the already-completed large candidate characterization test. Ruff, format (777 files), CI-scope mypy (450 source files), manifest D==M (259/259), `uv lock --check`, locked sync (71 packages), pip-audit, JSON duplicate-key audit, and `git diff --check` passed. The full shell-tube and HTTP/API suites were not repeated locally in this authority-only reassessment; the source-head exact-head CI passed, and a new exact-head CI is required on the evidence commit.

No production mesh was run, no TASK173 production result was created, `REAL_CASE_MESH_ADMISSIBLE=false`, and TASK175 was not performed. PR #283 remains Draft; Ready and Merge are unauthorized.

`NEXT_GATE=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_AUTHORITY_INDEPENDENT_REVIEW_R1`

This record does not execute or authorize that next gate. Stop here.
