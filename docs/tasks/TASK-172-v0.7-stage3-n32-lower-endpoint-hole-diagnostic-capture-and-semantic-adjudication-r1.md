# TASK172 v0.7 Stage-3 n=32 Lower-Endpoint Hole Diagnostic and Semantic Adjudication R1

Result: `PASS` for the bounded diagnostic/adjudication scope. This is not a production correction or mesh admission.

## Frozen execution identity

- Authorized predecessor head: `c3eb36960461ccee031413d22903a0256bb8bb19`
- PR #283 remains Open/Draft.
- Frozen cell-root, endpoint-classification, zero-q, and reconstruction authority hashes were verified and are copied into the machine evidence.
- No runtime source, tests, workflow, dependency, lockfile, or mesh policy was changed.
- The historical authority registry was left byte-for-byte unchanged; this adjudication is recorded in its standalone evidence files to preserve legacy registry formatting and duplicate-key history.

## Reproduced n=32 blocker

The fresh n=32 outer-boundary replay reached iteration 23 at shooting enthalpy `107537.399699021494920675754547119140625 J/kg`. It returned `HARD_BLOCKER` with public blocker `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED`, `endpoint_side=LOWER_ENDPOINT`, 12 production recovery levels, 11 valid samples, no valid sign pair, and no eligible root.

The failed support is `[4.9875,5.0250] m`, subdivision index 5 of physical interval `[4.8,6.0] m`. Its physical lower q endpoint is exactly zero. The support, tube-cell, shell-cell, and wall-interface identities, upstream thermodynamic snapshots, capacity bounds, and full q=0 TASK172 request/blocked payload are preserved in the JSON evidence.

Capture-on and capture-off direct replays produced identical 14-point failed-cell q sequences, the same 4617-call production TASK172 sequence digest, the same q=0 request/result hashes, and the same blocker. Two independent capture-on runs were byte-identical. The additional levels 13–24 were run only after production failure and are segregated as diagnostic-only.

## q=0 and TASK172 result

The exact-zero state-identity branch triggered; both upstream thermodynamic states and their property snapshots were reused; no PH reconstruction occurred. Contextual face identities remain distinct for distinct face locations. Therefore the zero-q portability contract passes, while TASK172 still returns a replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE` result. These are separate outcomes.

The blocked result carries only a diagnostic last-iterate vector. It supplies no production residual, sign, or physical result. The vector indicates the inner-film residual exceeds its existing R98 bound, while wall and outer-film residuals satisfy their bounds. TASK172 acceptance and `C_round=1.0` remain unchanged.

## Valid-point trajectory and semantic conclusion

The 12 production levels contain 11 valid positive-q evaluations, all with positive `F(q)`, and one further residual-acceptance hole at `q=1834.90115580185 W`. The endpoint `q=0` is also a residual-acceptance hole. Thus the captured pattern is not proven to be an exact-zero-only hole, nor is a finite positive-q hole interval established: the interval `(0,1834.90115580185 W)` has no valid samples.

Diagnostic levels 13–24 approach the *second, interior* hole edge from its valid side. Their fitted one-sided limits are consistently finite and positive (about `1555.6336815 W` at that interior edge). They do not establish a q→0+ limit and are not used as production residuals or physical results. No valid sign change or root was observed; global mathematical root nonexistence is not proven.

The adjudicated class is `G_MULTIHOLE_WITH_UNSAMPLED_LOW_Q_GAP`. The existing R3 authority is explicitly upper-endpoint/shell-capacity scoped and does not apply to this lower endpoint; no symmetric low-side inference is authorized.

## Correction direction (not implemented)

Option 4 is recommended for a separate authority adjudication: consider improving TASK172 local solver numerical accuracy while preserving the existing residual acceptance bounds exactly. No epsilon, relaxed R98, C_round change, extrapolated sign, or blocked-iterate acceptance is proposed. The next gate is `STAGE3_TASK172_LOCAL_RESIDUAL_ACCEPTANCE_NUMERICAL_CORRECTION_AUTHORITY_ADJUDICATION_R1`.

## Counts and lifecycle

For this targeted outer trial only, 4617 production TASK172 evaluations split exhaustively into 4611 valid local results and 6 `BLOCKED_RESIDUAL_ACCEPTANCE` holes. The predecessor full-run subtraction `121654 - 159 = 121495` remains only a derived non-hole count; its exhaustive classification breakdown is unavailable, so it is not promoted to authoritative valid count.

No complete production mesh sequence was rerun, n=64 was not run, no TASK173 production result was created, mesh admission remains false, TASK175 remains unexecuted, and the PR remains Draft. Exact-head CI for the evidence commit will be recorded in PR metadata without a follow-up repository commit.

Machine evidence: `docs/tasks/evidence/TASK-172-stage3-n32-lower-endpoint-hole-diagnostic-capture-and-semantic-adjudication-r1.json`
Evidence canonical hash: `11dd5de167eb6c40a184bb945763fc3a11cbd60d0a6b4e2c99100406854fb624`
