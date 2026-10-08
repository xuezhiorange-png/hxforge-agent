# TASK172 dogbox R3 exact-zero portability amendment

```ini
TASK_ID=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_R3_EXACT_ZERO_PORTABILITY_AMENDMENT
MODE=OWNER_DIRECTED_AUTHORITY_CANDIDATE_AMENDMENT_ONLY
RESULT=PASS_DOGBOX_FALLBACK_R3_CANDIDATE_WITH_EXACT_ZERO_PORTABILITY_SEMANTICS_PENDING_INDEPENDENT_REVIEW
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
PREDECESSOR_HEAD=6063149fc5fbecd448b7d6c04d5df02cde427a9c
```

## Decision

This evidence-only amendment closes the R2 review's sole finding, `EXACT_ZERO_Q_PORTABILITY_STATUS_UNSPECIFIED`. It freezes exact-zero status as a discrete comparison precondition. For each pair of already independently `VALIDATED` and original-R98-passing platform-native results, define `ZERO_A = (q_A == Decimal("0"))` and `ZERO_B = (q_B == Decimal("0"))`. If the statuses differ, q portability fails with `CROSS_PLATFORM_EXACT_ZERO_STATUS_MISMATCH` before applying the numeric q envelope. A zero/nonzero pair fails even when its difference is within the `1e-8 W` floor.

If both values are exact zero, q portability passes as exact physical-zero semantics. If both are nonzero, the existing q envelope remains `abs(q_A-q_B) <= max(1e-8 W, 1e-8 * max(abs(q_A), abs(q_B)))`. The existing `1e-8 K` absolute limits for each wall temperature remain independent. No epsilon, deadband, tolerance-based zero, rounding, or clipping is introduced.

The contract examples in the machine evidence are normative truth-table statements, not numerical fixtures or solver experiments. No numerical characterization was performed.

## Authority lineage

The new candidate is `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, lifecycle `PROPOSED_AUTHORITY_REVIEW_PENDING`, with canonical authority projection hash `9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b`. R2 remains immutable. R3 carries forward the R2 candidate semantics and adds only the exact-zero portability status rule to the portability policy.

The R2 lineage distinguishes the candidate from its review receipt: candidate-under-review HEAD `717c2d07e676231fbcd3b4ea474a9bd5475b4320` has authority hash `a3e04e95965d6432d4d54aa2dfed7bf5b9d5995ef98c4bbb7e87208545160318` and candidate evidence hash `3ea204e2d1ae3a887fa8e001c3bb767d97b8b1632c9734df058783a90af0d6a9`; the R2 review receipt is final HEAD `6063149fc5fbecd448b7d6c04d5df02cde427a9c`, result `FAIL_FAIL_ONLY_DOGBOX_FALLBACK_R2_AUTHORITY_INDEPENDENT_REVIEW`, finding `EXACT_ZERO_Q_PORTABILITY_STATUS_UNSPECIFIED`, and evidence canonical hash `8a2943ab1db04e2551fd766f916dc3fd09981f6e37894fa8b61d6d013184f5ff`. Historical R1 review evidence hash `1741d3883ed986bbc2a71e672118376395f68def1bc8e11c9997d162f821980e` remains identified only as R1 lineage.

This closeout includes a traceability-only correction: the earlier R3 evidence bound the R2 review receipt HEAD to the R2 candidate HEAD and labeled the historical R1 review hash as the R2 review hash. The R3 authority projection is unchanged; only the evidence canonical hash changes.

The reviewed `V07-T173-ZERO-Q-STATE-IDENTITY-PORTABILITY-R1` governs TASK173 state propagation, not this TASK172 cross-platform output comparison. Its exact-zero-only convention is consistent with this clarification, but its authority is not directly transferred.

The q/Twi/Two projection and numerical limits are unchanged. Existing persisted evidence shows all six n=32 targets are nonzero on both local and Linux sides and already pass the numerical/full projection envelope (6/6). The historical n=16 upper comparison is also nonzero on both sides and remains within the envelope with the same final low-side semantics. For the 68-row corpus, the persisted aggregate supports the numeric envelope proof; it does not retain rowwise q values sufficient to prove the exact-zero status count. That count is therefore explicitly unavailable and is not inferred. The new rule is prospective and fail-closed.

## Unchanged scope

R94, R98, `C_round=1.0`, constitutive equations, property domain, solver controls, dogbox trigger/seed/budget, TASK173 root behavior, and production mesh policy are unchanged. The portability comparison remains downstream of independent result validation and R98 acceptance; it is not solver stopping, R98 acceptance, or a way to accept a blocked result. No production correction, mesh execution, or TASK175 acceptance was performed.

```ini
EXACT_ZERO_Q_IS_DISCRETE_PORTABILITY_SEMANTIC=true
EXACT_ZERO_STATUS_MATCH_REQUIRED=true
ZERO_DEFINITION=EXACT_DECIMAL_ZERO_ONLY
ZERO_NONZERO_PAIR_WITHIN_NUMERIC_FLOOR_ALLOWED=false
Q_ABSOLUTE_FLOOR_W=1e-8
Q_RELATIVE_LIMIT=1e-8
TWI_ABSOLUTE_LIMIT_K=1e-8
TWO_ABSOLUTE_LIMIT_K=1e-8
TARGET_EXACT_ZERO_STATUS_MATCH_COUNT=6/6
TARGET_FULL_PROJECTION_PASS_COUNT=6/6
N16_EXACT_ZERO_STATUS_MATCH=true
N16_PORTABILITY_ENVELOPE_PASS=true
R94_CHANGED=false
R98_CHANGED=false
C_ROUND_CHANGED=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
NUMERICAL_EXPERIMENTS_PERFORMED=false
CORRECTION_IMPLEMENTED=false
AUTHORITY_ACCEPTED=false
NEXT_GATE=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_R3_INDEPENDENT_REVIEW
NEXT_GATE_EXECUTED=false
STOP=true
```

Machine evidence: `docs/tasks/evidence/TASK-172-stage3-task172-dogbox-r3-exact-zero-portability-amendment.json`.

```ini
R3_PROPOSED_AUTHORITY_CANONICAL_HASH=9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b
EVIDENCE_CANONICAL_HASH=e9677c64a5e7d0d32f3129228bcf4bf17098a73ea2339a442d030c9acd01ac5c
```
