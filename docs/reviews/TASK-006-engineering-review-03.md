# TASK-006 Engineering Review — Round 3

**PR:** #14  
**Head reviewed:** `858acc3a7033fa859e0cbaa09d325b57b4fe7684`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27941889205` / run #125 passed.

Review-02 materially improved structured failure results, dimensional energy acceptance, provenance identity, immutable result states and flow-arrangement semantics. Seven blocking contracts remain.

## 1. Phase-safe bracketing is not actually enforced

`_solve_outlet_temperature()` receives `expected_phase_family`, but `_is_valid_bracket_state()` only checks finite enthalpy and `_is_single_phase_strict()`. It never checks that the candidate state remains in the inlet phase family.

This permits a liquid inlet to bracket against a gas candidate, or vice versa. Brent may then cross an unsupported phase interval and return `FAILED` rather than the required `UNSUPPORTED_SERVICE` / `BLOCKED` result.

Required:

- require candidate phase family to equal `expected_phase_family` during bracket construction, Brent evaluation and final-state validation;
- use equality, not object identity, for phase-family comparison;
- when a continuous same-family interval cannot be established, return a structured unsupported-phase blocker rather than a numerical convergence failure;
- add tests for liquid-to-gas, gas-to-liquid, saturated interior points and discontinuous phase intervals.

## 2. Successful iterative property calls are missing from trace and hashing

`_safe_eval_tp()` records failed provider calls but does not record successful bracket probes or successful Brent evaluations. Only the final solved state is appended later.

These unrecorded provider calls directly determine the bracket and root, so the reported `property_calls`, provenance graph and result hash do not describe the actual calculation execution.

Required:

- record every provider invocation, successful or failed, with an explicit stage/sequence identifier such as `inlet`, `bracket_probe`, `brent_evaluation`, `final_state`;
- ensure each actual call appears once in the call trace;
- include the complete ordered call trace in result hashing and provenance;
- test call counts, order, success/failure records and hash changes when an intermediate provider response changes.

## 3. Failed-result diagnostics are discarded

Solver calls catch private exceptions and return `FAILED`, but `_make_failed_result()` is normally called without `bracket_evaluations`, `solver_iterations`, bracket endpoints, last valid state or last attempted temperature. Its defaults therefore report zero diagnostics even after a substantial search.

The private exceptions themselves contain only a message and do not carry structured diagnostic data.

Required:

- introduce a structured internal solver-failure object carrying side, target enthalpy, bracket endpoints, last attempted temperature, last valid state, bracket evaluations and Brent iterations;
- propagate those values into `RunFailure`, result fields, hash and provenance;
- preserve any successfully evaluated outlet state when the second side fails;
- add tests proving non-zero diagnostics and partial-state preservation for hot-side and cold-side failures.

## 4. CalculationContext is lost on blocked, failed and zero-duty paths

`solve_heat_balance()` accepts `CalculationContext`, but `_make_blocked_result()`, `_make_failed_result()` and `_handle_zero_duty()` do not accept or pass it to `_build_provenance()`.

`run_heat_balance()` also exposes no context argument and always calls `solve_heat_balance()` without context. Consequently, production service calls cannot retain real design-case revision or calculation-run identity, and early exits discard supplied identity.

Required:

- thread `CalculationContext` through every result-building path;
- add an explicit context argument to `run_heat_balance()` or accept a `DesignCaseRevision` / `CalculationRun` identity contract;
- verify success, blocked, failed and zero-duty results preserve the same real revision/run IDs;
- add service-level and JSON round-trip tests.

## 5. Deterministic UUID5 nodes collide for repeated identical events

Property-call, warning and blocker node IDs are derived only from their content payload. Two identical calls or messages therefore receive the same node ID, while `ProvenanceGraph` requires all node IDs to be unique.

This can occur for repeated provider calls at the same state, identical hot/cold requests, retries, or duplicate warnings.

Required:

- include a deterministic occurrence index or stable execution sequence in each event-node identity payload;
- retain content hashes separately so identical payloads remain visibly identical while node instances remain unique;
- apply the same rule to property calls, warnings and blockers;
- add duplicate-call and duplicate-message graph-construction tests.

## 6. Result hash does not cover the complete public result identity

The canonical state payload omits public `FluidStateModel` fields including viscosity, conductivity, quality and substantial property provenance identity such as backend git revision, validation metadata, query inputs, cache-policy version and configuration fingerprint.

Provider configuration is also read through the private `_construction_fingerprint` attribute, which is not part of the `PropertyProvider` protocol. Providers implementing the protocol can therefore silently hash as an empty configuration.

Required:

- hash the complete canonical `FluidStateModel` payload or a documented complete heat-balance state identity;
- include full public property provenance that can affect interpretation or reproducibility;
- expose provider configuration fingerprint through the public provider protocol or derive it from returned property provenance;
- add collision tests for viscosity/conductivity/quality, backend revision, validation identity and configuration fingerprint.

## 7. Near-zero duty verification and diagnostic messages still mix tolerance bases

For known outlet plus supplied duty, consistency checking uses `energy_tolerance * max(abs(duty), 1.0)` even when the duty falls under the configured near-zero threshold. It ignores `absolute_energy_tolerance_w` and `near_zero_duty_threshold_w`.

When the final energy gate uses the absolute basis, the blocker message still says `relative_imbalance` exceeds the dimensionless `energy_tolerance`, which is not the actual acceptance rule.

Near-zero terminal-approach warnings also use `SolverParams().temperature_tolerance` rather than the caller-supplied tolerance.

Required:

- centralize duty consistency and final energy acceptance in one basis-aware helper;
- use absolute tolerance below the configured threshold and relative tolerance above it;
- render basis-specific structured messages with correct units;
- use the supplied temperature tolerance for near-zero approach warnings;
- add below/at/above-threshold tests with non-default solver parameters.

## Records

The PR body still describes Review Round 2 as open. Update PR metadata and task records only after the corrected final head is green.

## Approval gate

Before Round 4:

1. both Python 3.11 and 3.12 CI remain green;
2. bracket and Brent evaluations remain in the inlet phase family;
3. every actual provider call is represented in ordered trace, hashing and provenance;
4. failed results retain structured non-zero diagnostics and partial valid states;
5. CalculationContext survives all result paths and the domain service;
6. repeated identical events cannot collide in ProvenanceGraph node IDs;
7. result hashes cover complete public thermal/property identity;
8. all energy and temperature checks use the configured dimensional tolerance basis;
9. no LMTD, epsilon-NTU, coefficients, pressure drop, sizing, rating, optimization, API, database, report or TASK-007 scope is added.
