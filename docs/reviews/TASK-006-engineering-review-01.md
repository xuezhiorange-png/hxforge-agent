# TASK-006 Engineering Review — Round 1

**PR:** #14  
**Head reviewed:** `17b89324248ef2f1f8c4cb544aba965ba5a8061b`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27931880107` / run #111 passed.

The implementation establishes a broad heat-balance scaffold and passes CI, but the current code does not yet satisfy HXForge's physical-feasibility, structured-failure, deterministic-provenance, immutable-model, or complete-identity contracts.

## 1. Structured failure contract is not implemented

Under-/over-specification, property failures, phase rejection, invalid duty direction, and solver failure are raised as plain `ValueError`. In several paths an `EngineeringMessage` blocker is created and immediately discarded when the function raises. `RunFailure` is not integrated.

Required:

- define one stable execution contract: either return a blocked `HeatBalanceResult` with structured messages, or raise a dedicated domain exception carrying `RunFailure` and immutable `EngineeringMessage` objects;
- do not create blockers and then discard them;
- preserve stable error codes, source module, context, failed stage and provider error identity;
- under-/over-specification must use `INPUT_MISSING` / `INPUT_INCONSISTENT`, not message-text matching;
- property and solver failures must be available to callers without parsing exception strings;
- add JSON round-trip tests for every failure class.

## 2. Temperature feasibility is physically ambiguous and incorrectly non-blocking

The implementation assumes both:

- `hot_outlet >= cold_outlet`, which is a parallel-flow outlet condition and is not a universal counterflow requirement; and
- counterflow terminal approaches `hot_in - cold_out` and `hot_out - cold_in`.

This mixes two different flow arrangements. In a valid counterflow exchanger, cold outlet can exceed hot outlet while both terminal approaches remain positive.

Additionally, temperature cross and non-positive minimum approach are emitted as warnings, while the TASK-006 contract requires these conditions to be rejected. The solver then appends all feasibility messages to `warnings`, even messages whose severity is `BLOCKER`.

Required:

- add an explicit `FlowArrangement` contract, or limit v0.1 to one explicitly declared arrangement with no hidden default;
- compute terminal pairs according to that arrangement;
- remove the topology-invalid `hot_outlet < cold_outlet` rule for counterflow;
- non-positive terminal approach and true temperature cross must be blockers;
- near-zero positive approach may be a warning under an explicit tolerance policy;
- route messages by severity into warnings vs blockers;
- blocked feasibility results must not be returned as accepted calculations;
- add counterflow cases where `cold_outlet > hot_outlet` but both terminal approaches are positive.

## 3. Energy-balance acceptance is not enforced

`relative_imbalance >= energy_tolerance` only sets `solver_converged=False`; the result is still returned without a blocker. In `BOTH_OUTLETS_KNOWN`, duty is reported as `(Q_hot + Q_cold)/2`, which can mask an inconsistent pair of outlet specifications.

Required:

- retain `Q_hot` and `Q_cold` as explicit typed result fields;
- distinguish root-solver convergence from energy-balance acceptance;
- if relative imbalance is at or above tolerance, emit a blocker / failed verification result;
- do not average inconsistent hot- and cold-side duties into an apparently valid duty;
- for verification mode, report both duties and a clearly defined representative duty only when accepted;
- define zero/near-zero imbalance denominator behavior with a documented absolute-duty tolerance;
- add tests just below, exactly at, and just above the 0.1% threshold.

## 4. Phase-change safety is incomplete

The code checks inlet states and explicitly supplied outlet states, but solved outlet states from Brent's method are not phase-checked before use. Endpoint phase compatibility is also not checked, so liquid inlet → gas outlet can be accepted if both endpoints are individually single phase.

During root finding, `PropertyServiceError` is converted into ±1e12 residual sentinels. This masks invalid states and can manufacture a sign change across an invalid or two-phase interval. Failed provider calls are not represented in the property-call trace.

Required:

- phase-check every final solved outlet state;
- reject incompatible inlet/outlet phase-region transitions for v0.1;
- do not convert property failures into synthetic thermodynamic residuals;
- use `state_ph()` for constant-pressure enthalpy inversion where supported, or use a phase-safe bounded solver that never brackets through invalid states;
- record failed property evaluations as structured provenance/failure records;
- define compatibility rules for liquid, gas and supercritical phase families;
- add tests for solved saturated outlet, liquid-to-gas endpoint transition, invalid bracket region, and property failure during iteration.

## 5. Zero-duty handling silently overwrites inconsistent specifications

The zero-duty branch runs after specification classification and forces both outlets equal to their inlets. If a caller provides zero duty plus a non-equal outlet temperature, the supplied outlet is silently ignored instead of being rejected.

The zero-duty path also creates duplicate property-call records for outlet states without actually calling the provider again.

Required:

- if a zero-duty case supplies an outlet, require it to equal the corresponding inlet within temperature tolerance;
- reject inconsistent zero-duty outlet specifications with a structured blocker;
- do not fabricate provider calls for reused inlet states;
- distinguish evaluated property calls from state reuse in provenance;
- add zero-duty tests with matching and mismatching supplied outlets.

## 6. Result and input models are not deeply immutable or fully finite

`HeatBalanceResult` stores states, property calls, warnings and blockers as mutable `dict[str, Any]` objects inside a frozen Pydantic model. Nested dictionaries remain mutable. Only three top-level floats are checked for finiteness.

`SolverParams`, `StreamState`, `HeatBalanceInput`, and `PropertyCallRecord` are dataclasses without complete finite/range validation. NaN passes comparisons such as `value <= 0` and can enter the solver.

Required:

- replace untyped dictionaries with immutable typed domain models;
- reuse `FluidState`, `EngineeringMessage`, property provenance models and existing unit-safe types rather than serializing them into parallel dictionaries;
- reject NaN/Inf recursively in all inputs, solver controls, states, calls and results;
- validate solver tolerances and iteration limits as finite and positive;
- prove nested mutation is impossible;
- remove `Any` from public heat-balance contracts where practical.

## 7. Result identity is incomplete

The result hash includes solved states, duty, residual, imbalance and software version, but omits material inputs and execution identity, including:

- hot/cold fluid identifiers;
- mass flows;
- specification inputs and supplied duty;
- solver controls;
- provider name, version and reference-state policy;
- property-call outputs and failure records;
- warnings and blockers;
- flow arrangement;
- case revision / calculation-run identity policy.

Different inputs can therefore produce the same result hash if their solved thermodynamic states and final duty coincide.

Required:

- hash a canonical complete request identity and complete structured result identity;
- include fluid composition/backend identity, flows, pressures, supplied outlet/duty values, solver controls, provider identity/reference policy, flow arrangement, messages and property-call/result identities;
- define whether run UUIDs are intentionally excluded from content identity;
- add collision-oriented tests for mass flow, fluid ID, pressure, provider version, solver tolerance, warning/blocker and flow arrangement changes.

## 8. Provenance is nondeterministic and contains invented identities

`_build_provenance()` uses `uuid4()` for every node. The main solver also supplies a newly generated UUID as `case_revision_id`, rather than an actual case revision. Therefore the same calculation produces different provenance JSON and an invented case-revision lineage.

Property-call payload hashes omit backend version, reference-state policy, returned state and failure status. Warning/blocker payload hashes omit severity, source and structured context.

Required:

- accept an explicit calculation context containing actual `DesignCaseRevision` and `CalculationRun` identities, or omit those node types when no real identity is available;
- never invent case-revision or calculation-run identities;
- use injected IDs or namespaced deterministic UUID5 node IDs derived from canonical node payloads;
- include provider identity/version/reference policy and complete returned state in property-call node identity;
- include complete `EngineeringMessage` payload in message-node identity;
- add exact provenance JSON repeatability tests, not only DAG and round-trip tests.

## 9. Root-solver controls and error handling are not contractual

Bracket step (10 K), maximum span (300 K), and the `max_iterations * 3` function-evaluation guard are hardcoded and conflict with documentation that describes `max_iterations` as the maximum function evaluations. Property failures can be hidden by sentinels.

Required:

- expose validated bracket step and maximum search span in solver controls, or derive them from explicit fluid validity limits;
- define exactly what `max_iterations` counts;
- separate bracket evaluations from Brent iterations in convergence records;
- return structured convergence failure with bracket history and last valid states;
- test invalid solver controls, bracket exhaustion and iteration exhaustion.

## 10. Documentation and tests encode incorrect behavior

Current tests explicitly expect temperature cross and negative approach as warnings, and expect plain `ValueError` for cases described as structured blockers. Provenance tests only check DAG structure and JSON round trip, not deterministic identity. Result immutability tests only attempt assignment to a top-level scalar.

Required:

- update tests to enforce the corrected contracts above;
- ensure golden cases contain independently reviewable expected balances and tolerances, not only snapshots produced by the same implementation;
- update PR status/body and task card only after the corrected final head is green.

## Approval gate

Before Round 2:

1. both Python 3.11 and 3.12 CI jobs remain green;
2. all failures have stable structured contracts;
3. flow arrangement and terminal feasibility are physically coherent;
4. energy imbalance above tolerance cannot be accepted;
5. no endpoint or iterative phase transition escapes v0.1 rejection;
6. zero-duty specifications cannot be silently overwritten;
7. public models are deeply immutable and recursively finite;
8. result and provenance identities are complete and deterministic;
9. root-solver controls and convergence records are explicit;
10. no LMTD, epsilon-NTU, coefficients, pressure drop, sizing, rating, optimization, API, database, report or TASK-007 scope is added.
