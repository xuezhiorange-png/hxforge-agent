# TASK-006 Engineering Review — Round 2

**PR:** #14  
**Head reviewed:** `1919098f159567d0c6d9d70ec51a64548d9e76b2`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27936066617` / run #119 passed.

Round 1 materially improved structured results, flow-arrangement semantics, phase-family checks, deterministic hashing and provenance, but eight blocking contracts remain.

## 1. Solver failures still escape the public result contract

The module states that `solve_heat_balance()` always returns `HeatBalanceResult` and represents root-solver failure as `HeatBalanceStatus.FAILED`. However, all calls to `_solve_outlet_temperature()` are still unguarded. `_BracketExhausted` and `_SolverNotConverged` therefore escape to callers.

The current tests explicitly expect these private exceptions to be raised, contradicting the public contract.

Required:

- add one solver boundary that catches `_BracketExhausted`, `_SolverNotConverged`, and iterative property failures;
- return a `FAILED` result carrying `RunFailure`, stable error code, bracket history, last valid state, bracket evaluations and Brent diagnostics;
- do not expose private solver exceptions through the public API;
- update tests to require `HeatBalanceStatus.FAILED`, not `pytest.raises`.

## 2. Invalid states inside Brent are still converted into synthetic residuals

`_safe_eval_tp()` catches `PropertyServiceError` and returns `None` without recording the failed call. During Brent evaluation, invalid or phase-incompatible states are converted to arbitrary `+/-1e6` residual values. This can manufacture a numerical sign and obscure a discontinuous or invalid thermodynamic interval.

`_is_valid_bracket_state()` also checks phase-family equality but does not require `_is_single_phase_strict()`, so saturated boundary states can be accepted as bracket states.

Required:

- never substitute artificial thermodynamic residuals for invalid states;
- record every failed iterative property call with error code/message and bracket location;
- require strict single-phase states throughout bracket construction and final inversion;
- prefer `state_ph()` for constant-pressure enthalpy inversion where supported, or fail deterministically when a continuous valid TP interval cannot be proven;
- add tests for invalid interior points, saturated bracket points, provider failure during Brent, and discontinuous phase intervals.

## 3. Near-zero energy acceptance is dimensionally inconsistent

For duties below `_ABSOLUTE_DUTY_THRESHOLD`, `relative_imbalance` is assigned `abs(residual_w)` in watts and then compared with `energy_tolerance`, which is dimensionless. The result field therefore changes physical meaning depending on duty magnitude.

Required:

- keep `relative_imbalance` dimensionless or optional;
- add an explicit validated `absolute_energy_tolerance_w` for zero/near-zero duty;
- expose which acceptance basis was used;
- include the absolute threshold/tolerance and basis in canonical hashing and provenance;
- test below, exactly at, and above both relative and absolute thresholds.

## 4. Provenance still invents case-revision lineage

When no real `case_revision_id` is supplied, `_build_provenance()` creates a deterministic `synthetic_case_revision` node. `run_heat_balance()` never supplies an actual revision or calculation-run identity, so the production path always emits invented lineage.

The calculation-run node identity is based mainly on mode and solver counts, not the complete request/result identity, so unrelated runs can receive the same node identity.

Required:

- accept an explicit calculation context carrying actual `DesignCaseRevision` and `CalculationRun` identities;
- never label a synthetic request identity as `CASE_REVISION`;
- when no revision exists, use an explicitly typed request/input root or require context at the domain-service boundary;
- derive deterministic node IDs from complete domain-separated node payloads, including request/result identity;
- update provenance tests to reject invented case revisions.

## 5. Result hash still omits structured identity fields

The result hash now includes most thermal inputs and property calls, but message hashing omits `schema_version`, `affected_paths`, `context`, and `allows_continuation`. The hash also omits final result `status`, `failure`, final `duty_w`, provider git revision/configuration identity, and the near-zero acceptance basis.

Required:

- canonicalize complete `EngineeringMessage` and `RunFailure` models;
- include final status, failure, final duty, acceptance basis and all solver thresholds;
- include provider git revision/configuration fingerprint where exposed by the provider contract;
- add collision tests for message context/path, failure context, provider revision, status and acceptance-basis changes.

## 6. Blocked results fabricate physical states

Early blocked results use `_placeholder_state_model()` with zero temperature, pressure and transport properties plus empty provider provenance. These values are not measured or calculated states and may be mistaken for real thermodynamic results.

Required:

- make unavailable inlet/outlet states optional in blocked/failed results, or use a dedicated unavailable-state type;
- never represent unavailable physical states as `0 K`, `0 Pa`, or zero properties;
- preserve only states that were actually evaluated;
- add partial-result JSON and hash tests for failures before the first property call and after only one inlet is evaluated.

## 7. Zero-duty trace and status consistency remain incorrect

For supplied zero-duty outlets equal to their inlets, the code appends additional `PropertyCallRecord` entries without actually calling the provider. This fabricates property calls. When a supplied outlet conflicts with zero duty, the result becomes `BLOCKED` but still sets `energy_balance_accepted=True` and `solver_converged=True`.

Required:

- record only actual provider invocations as property calls;
- represent state reuse separately or omit duplicate calls;
- set acceptance/convergence flags consistently with blockers and final status;
- strengthen `HeatBalanceResult` validation so:
  - `SUCCEEDED` requires accepted energy balance, solver convergence, no blockers and no failure;
  - `BLOCKED` cannot claim accepted calculation;
  - `FAILED` requires failure and cannot claim solver convergence;
- add zero-duty matching/mismatching outlet and status-consistency tests.

## 8. Flow arrangement is still a hidden production default

`run_heat_balance()` defaults to counterflow when `DesignCase` has no flow-arrangement field and emits no warning. This violates the requirement that arrangement be explicit and prevents callers from knowing whether counterflow was specified or assumed.

Required:

- add flow arrangement to the domain input contract, or require it as an explicit service argument until the design-case model supports it;
- do not silently default in the production domain service;
- if a temporary policy default is unavoidable, encode the policy/version in warnings, hashing and provenance;
- add service-level tests for missing arrangement and explicit counterflow.

## 9. Tests and records

Update tests that currently require private solver exceptions or synthetic `CASE_REVISION` nodes. Update PR body and task card only after the corrected final head is green.

## Approval gate

Before Round 3:

1. both Python 3.11 and 3.12 CI jobs remain green;
2. no private solver exception escapes the public service;
3. no synthetic residual masks an invalid thermodynamic state;
4. absolute and relative energy acceptance are dimensionally explicit;
5. provenance contains no invented case-revision identity;
6. result hashes cover complete structured inputs, status, failures and messages;
7. blocked/failed results contain no fabricated physical state or property call;
8. flow arrangement is explicit at the domain-service boundary;
9. no LMTD, epsilon-NTU, coefficients, pressure drop, sizing, rating, optimization, API, database, report or TASK-007 scope is added.
