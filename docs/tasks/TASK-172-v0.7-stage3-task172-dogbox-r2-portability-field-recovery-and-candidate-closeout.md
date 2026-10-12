# TASK172 dogbox R2 portability field recovery and candidate closeout

```ini
TASK_ID=STAGE3_TASK172_DOGBOX_R2_PORTABILITY_FIELD_RECOVERY_AND_CANDIDATE_CLOSEOUT
MODE=MISSING_FIELD_RECOVERY_AND_R2_CANDIDATE_CLOSEOUT_ONLY
RESULT=PASS_DOGBOX_FALLBACK_R2_CANDIDATE_WITH_FROZEN_PORTABILITY_ENVELOPE_PENDING_INDEPENDENT_REVIEW
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
AUTHORIZED_SOURCE_HEAD=5485215071ffdaa9f75ea0a5562615c356305c91
```

## Decision and boundary

The R1 independent review finding is closed by the owner-directed R2 portability comparison policy. No solver, 68-row matrix, Linux characterization, production mesh, or TASK175 run was performed. The two historical raw macOS artifacts and the two named Linux JUnit producer artifacts supplied all seven missing q/Twi/Two projections.

The proposed authority is `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R2`, lifecycle `PROPOSED_AUTHORITY_REVIEW_PENDING`, `AUTHORITY_ACCEPTED=false`. It copies the R1 candidate projection, changes the authority ID to R2, and adds only the frozen portability comparison policy below. R1 and its failed review receipt remain unchanged.

## Frozen engineering-output portability policy

`PORTABILITY_COMPARISON_PROJECTION_ID=V07-T172-PORTABLE-ENGINEERING-OUTPUT-PROJECTION-R1`

The only cross-platform numerical fields are signed q, inner-wall temperature, and outer-wall temperature. Both native results must already be independently `VALIDATED` and pass the original R98 acceptance.

- q allowance: `max(1e-8 W, 1e-8 * max(abs(q_A), abs(q_B)))`; if both q values are exactly zero, both retain exact physical-zero semantics.
- Inner-wall and outer-wall allowances: `1e-8 K` absolute each; no relative temperature allowance.
- The limits are an owner-scoped TASK172 portability decision. The reviewed 1e-8 project numerical scales are design rationale only; R101 reference-precision semantics are not transferred. The observed corpus deltas did not select these limits.
- Residual vector, property snapshot numeric fields, HTC, Reynolds, Prandtl, J_mu, and solver trace are excluded from the cross-platform comparison projection. They remain present in native result provenance/hash and remain governed by their existing authorities and same-environment replay.
- The envelope is not R98 acceptance, residual tolerance, solver stopping, blocked-result recovery, property-domain widening, or result identity. No clipping, rounding, quantization, or tolerance hash is used.

## Recovered target comparison

Local fields came from the existing macOS raw JSON files whose SHA256 values match the registered values. Their six request hashes and the n=16 request hash match exactly. The recovered q values also match the already-adjudicated local dogbox-candidate q values. The source profile was the pre-existing `CANDIDATE_E_DOGBOX_REFERENCE`; actual observed work was at most 4 nfev / 16 callbacks for the six targets and 4 / 13 for n=16, below the proposed 6 / 24 fallback ceilings. This is field recovery from existing evidence, not a solver rerun.

Linux fields were parsed from `junit.xml` property `task172_fail_only_dogbox_candidate`, run `36962301921`, PR-head SHA `86849841a5314f6ee82eebc117ece8f969829e06`, artifacts `11208069238` (CPython 3.11) and `11209036072` (CPython 3.12). The seven engineering projections and Linux native result hashes are identical between the two Python versions.

| Request | Local q / Linux q (W) | Allowed q delta (W) | |ΔTwi| (K) | |ΔTwo| (K) | Result |
|---|---:|---:|---:|---:|---|
| `91c13f…` | 279.6428084422918 / 279.64280844231325 | 2.7964280844231325e-6 | 5e-14 | 0 | PASS |
| `946e8d…` | 278.4621115308888 / 278.4621115308767 | 2.784621115308888e-6 | 3e-14 | 0 | PASS |
| `0b1a13…` | 282.8367069664459 / 282.8367069664438 | 2.828367069664459e-6 | 0 | 0 | PASS |
| `5fd98b…` | 282.8351020677846 / 282.83510206779323 | 2.8283510206779323e-6 | 0 | 0 | PASS |
| `3ffebf…` | 281.7082529109981 / 281.70825291103137 | 2.8170825291103137e-6 | 0 | 4e-14 | PASS |
| `a52cda…` | 279.2674742343681 / 279.2674742343595 | 2.792674742343681e-6 | 0 | 7e-14 | PASS |

All six local baseline paths were residual-acceptance holes followed by the existing candidate dogbox path; Linux R94 results were valid and bypassed fallback. Every side independently passed R98 and physical guards. `TARGET_FULL_PROJECTION_PASS_COUNT=6/6`.

## Historical n=16 upper endpoint

Request `22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970`:

- q: local `703.6847988973881 W`, Linux `703.6847988973623 W`; allowed `7.036847988973881e-6 W`, delta `2.58e-11 W`.
- Twi: local `298.6487099252561 K`, Linux `298.64870992525607 K`; delta `3e-14 K`.
- Two: local `298.5685125716107 K`, Linux `298.56851257161065 K`; delta `5e-14 K`.
- All three envelope checks pass. The existing F values remain local `-592.2898790517881 W` and Linux `-592.2898790517623 W`; both final paths have the same existing valid-upper shell-capacity low-side semantics. R3 is unchanged.

## 68-request corpus maximum-bound proof

No rows were rerun. The pre-existing authoritative 68-row aggregate maxima are q absolute `3.8335201679728925e-10 W`, q relative `2.581475744081614e-13`, Twi `1.1368683772161603e-13 K`, and Two `1.7053025658242403e-13 K`. Each maximum is below its frozen absolute floor/limit, so the whole corpus passes by `PREEXISTING_AUTHORITATIVE_MAXIMUM_BOUND`: q `68/68`, Twi `68/68`, Two `68/68`, full projection `68/68`. These observed deltas were not used to select the limits.

## R2 authority and unchanged behavior

R2 authority hash: `a3e04e95965d6432d4d54aa2dfed7bf5b9d5995ef98c4bbb7e87208545160318`. It is the canonical hash of the R1 authority projection with only its ID changed to R2 and the exact `portability_comparison_policy` object persisted in the machine evidence added. R94 primary, fail-only trigger, original-seed dogbox fallback, 6/24 caps, R98, C_round, constitutive equations, property domain, fail-closed rules, baseline-valid bypass, and platform-native result identity are inherited unchanged.

Machine evidence canonical hash: `3ea204e2d1ae3a887fa8e001c3bb767d97b8b1632c9734df058783a90af0d6a9` (project RFC 8785 canonical JSON SHA256, excluding `canonical_hash`).

The prior review CI observation `36986332073` was functionally successful but reported a 592-second shard against the 540-second reference. That is not evidence of dogbox numerical/runtime failure. The R2 evidence HEAD must use the ordinary 540-second runtime reference; if exceeded, report the CI runtime gate separately without changing solver authority or timeout.

```ini
R94_CHANGED=false
R98_CHANGED=false
C_ROUND_CHANGED=false
CONSTITUTIVE_EQUATIONS_CHANGED=false
PROPERTY_DOMAIN_CHANGED=false
PORTABILITY_ENVELOPE_USED_AS_R98_ACCEPTANCE=false
PORTABILITY_ENVELOPE_USED_AS_SOLVER_STOPPING=false
PORTABILITY_ENVELOPE_USED_TO_ACCEPT_BLOCKED_RESULT=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
FIXTURES_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILE_CHANGED=false
WORKFLOWS_CHANGED=false
CORRECTION_IMPLEMENTED=false
PRODUCTION_MESH_REEXECUTED=false
REAL_CASE_MESH_ADMISSIBLE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
AUTHORITY_ACCEPTED=false
NEXT_GATE=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_R2_INDEPENDENT_REVIEW
NEXT_GATE_EXECUTED=false
STOP=true
```

The machine-readable record contains the seven full row comparisons, raw-file hashes, JUnit run/artifact provenance, corpus bound proof, authority delta/hash, and change/lifecycle boundaries.
