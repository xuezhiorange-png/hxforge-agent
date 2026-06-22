# TASK-006 Engineering Review — Round 5

**PR:** #14  
**Head reviewed:** `a389108c58ed41eebf3e9f51cb2236adb688b371`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27948438946` / run #128 passed.

Review-04 closes most prior physical, failure-result, hashing and provenance gaps. Six final contracts remain open.

## 1. Failed property calls are misclassified as phase rejection

`_all_wrong_phase()` returns `True` whenever no successful same-family state exists. If every solver call failed because the provider was unavailable or the state was out of range, the function still returns `True` and the public solver reports `BLOCKED / UNSUPPORTED_SERVICE` as though a phase transition were proven.

Required:

- distinguish successful wrong-phase observations from failed property evaluations;
- classify phase rejection only when at least one successful candidate proves an incompatible phase family and no valid continuous same-family bracket exists;
- classify all-failed bracket searches using the actual property error (`PROPERTY_UNAVAILABLE`, `PROPERTY_OUT_OF_RANGE`, etc.) or a numerical convergence failure as appropriate;
- add all-failed, mixed failed/wrong-phase, and genuine cross-phase tests.

## 2. Iterative property failures lose their root-cause identity

Inside Brent evaluation, a `PropertyServiceError` is recorded and converted to `None`; the caller then raises `_SolverNotConverged`, and `_make_failed_result()` always emits `RunFailure(code=CALCULATION_NOT_CONVERGED)`. The property-call trace contains the original error, but the result status/failure identity does not.

Required:

- carry the dominant/causal property error through the structured solver failure object;
- define precedence between provider failure, out-of-range state, phase rejection and pure numerical non-convergence;
- ensure final `RunFailure` and/or blocker uses the actual stable error code;
- test provider backend failure and state-out-of-range during bracket probing and Brent evaluation.

## 3. Failed-result call merging can delete actual provider invocations

`_make_failed_result()` merges `solver_calls` using equality-based deduplication (`if sc not in all_calls`). Two actual identical calls can therefore collapse into one record. This is especially possible when the same fluid and state appear on both streams or when the solver retries the same state.

`PropertyCallRecord` also lacks stream role and a global sequence identity, so otherwise identical hot- and cold-side calls are indistinguishable.

Required:

- preserve every actual provider invocation in exact execution order;
- never deduplicate calls by value equality;
- include `stream_role` and deterministic `sequence_index` (or equivalent event identity);
- ensure hash and provenance consume the exact ordered trace;
- add duplicate-call, retry and same-fluid-both-sides tests.

## 4. Property-call provenance nodes omit part of the returned state identity

`PropertyCallRecord` and the result hash now include density, heat capacity, viscosity, conductivity, entropy and quality. The provenance property-call node payload still includes only temperature, pressure, enthalpy and phase plus success/error fields.

Required:

- build provenance property-call payloads from the same canonical serializer used by result hashing;
- include complete returned state identity and provider/configuration identity;
- retain occurrence index separately from content identity;
- add tests proving a transport-property or quality change alters the property-call provenance payload hash/node identity.

## 5. Solver statistics remain internally inconsistent

The implementation creates both `brent_iterations` and `brent_evals`, but `brent_evals` is not used in the returned result. `brent_iterations` is incremented on residual evaluations, so it represents function evaluations rather than Brent algorithm iterations. Public fields still use `solver_iterations` and `bracket_evaluations`, while Review-04 reports `bracket_probes` and Brent iterations as separate counts.

Required:

- define and expose unambiguous counters: bracket probes, Brent function evaluations and, if needed, Brent algorithm iterations;
- use SciPy `full_output=True` for true iteration/convergence metadata, or rename counters to what they actually count;
- remove unused counters and duplicate residual functions;
- include all counters in failure diagnostics, result hash and provenance;
- add exact-count tests with a deterministic mock provider.

## 6. Public identity/records are not final

`HeatBalanceResult` validates only the format of `result_hash`; it does not detect a valid-looking but tampered hash during direct construction or JSON loading. Also, PR #14 and the task card still describe Review Round 2 as open and do not record head `a389108`, 798 tests or CI run `27948438946`. No authoritative Review-04 document is present in the PR.

Required:

- make heat-balance results factory/engine-created, or store enough canonical request/result identity to recompute and validate the result hash on load;
- add tampered-hash and JSON round-trip validation tests;
- update PR body and task card only after the corrected final head is green;
- record Review-04 and Review-05 closure, final head, test count and CI run.

## Final approval gate

Before approval:

1. both Python 3.11 and 3.12 CI remain green;
2. property failures, phase rejection and numerical failure have correct stable classifications;
3. every provider invocation appears once in exact ordered trace;
4. provenance uses the complete canonical property-call identity;
5. solver counters are unambiguous and truthful;
6. result identity detects tampering or is construction-bound by design;
7. PR/task/review records match the final remote head and CI run;
8. no LMTD, epsilon-NTU, coefficients, pressure drop, sizing, rating, optimization, API, database, report or TASK-007 scope is added.
