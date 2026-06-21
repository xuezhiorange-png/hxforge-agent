# TASK-003 Engineering Review — Round 1

**PR:** #7  
**Head reviewed:** `17e372c1109b588d66e3d3679d0182f3eb73101b`  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

The provider architecture and query paths are sound, but the following engineering-contract issues remain.

## 1. Freeze CoolProp reference state and configuration

The provider uses global high-level CoolProp calls. Enthalpy and entropy reference states and CoolProp configuration can be changed process-wide, while the current cache key does not capture those changes.

Required:

- define an explicit v0.1 reference-state policy, initially `DEF` unless separately approved;
- isolate provider calculations from later global reference-state mutation;
- record reference-state policy and a CoolProp configuration fingerprint in provenance and cache keys;
- document process and thread-safety boundaries;
- add regression tests proving external reference/config changes cannot silently reuse stale cache entries.

## 2. Separate support from validation evidence

Water, Air, R134a and R717 are currently labelled `TIER_1_VALIDATED` from the name allowlist. Positivity tests and TP/PH consistency against the same backend show implementation consistency, not sufficient engineering validation.

Required:

- separate `SUPPORTED_TIER_1` from `BENCHMARK_VALIDATED`;
- create a fixed validation matrix with dataset ID, revision, state points, expected values, sources and property-specific tolerances;
- cover liquid and gas regions where applicable;
- include saturation checks for R134a and R717;
- only return a validated level inside an approved validation envelope;
- distinguish backend regression fixtures from independent/reference evidence.

## 3. Make PH reference-state semantics explicit

Specific enthalpy depends on its reference state, but `state_ph()` accepts only pressure and enthalpy.

Required:

- add a reference-state identifier to provider configuration and the PH query contract;
- reject unspecified or mismatched PH reference states;
- record the identifier in provenance and cache keys;
- document the impact on TASK-002 `PHStateSpec`;
- add matching and mismatch tests.

## 4. Separate provider and equation-of-state backend names

`FluidSpec.backend` means the property provider (`CoolProp`), while `FluidIdentifier.backend` means the internal CoolProp backend (`HEOS`).

Required:

- use unambiguous names such as `provider_id` and `equation_of_state_backend`;
- add one deterministic adapter from `FluidSpec` to `FluidIdentifier`;
- document composition basis;
- reject unsupported combinations;
- test Water, the R717/Ammonia alias and one unvalidated mixture mapping.

## 5. Add stable result serialization

`FluidState`, `SaturationState` and provenance are dataclasses without an explicit public serialization version.

Required:

- add strict versioned serialization or Pydantic result models;
- serialize enums, tuples and optional quality deterministically;
- add JSON round-trip tests for states and structured errors;
- define which cache fields are internal;
- record a result-schema version.

## 6. Make PH saturation tolerance reference-state invariant

The current tolerance uses `max(abs(h_f), abs(h_g), 1)`. Absolute enthalpy changes with the reference convention.

Required:

- scale boundary distance using `abs(h_g - h_f)` with an explicit minimum floor;
- document the equation and units;
- add an invariant regression test.

## 7. Clarify mixture capability

Mixture strings are represented, but actual mixture TP/PH/saturation capability has not been validated.

Required:

- distinguish mixture representation from calculation support;
- either return explicit unvalidated/not-implemented behavior for v0.1 mixtures, or add actual query tests and applicability limits;
- do not describe mixture bubble/dew results as a pure-fluid saturation point;
- document the final boundary.

## 8. Add error-boundary regressions

Add tests for:

- an out-of-range state returning `property_state_out_of_range`;
- saturation above critical returning `property_saturation_unavailable`;
- unsupported backend and malformed composition;
- failed-query cache behavior;
- stable public error codes independent of backend message wording.

## Approval gate

After revision:

1. rerun all CI gates on Python 3.11 and 3.12;
2. report reference-state/configuration policy;
3. report the Tier-1 validation matrix and tolerances;
4. demonstrate PH reference matching and invariant tolerance;
5. demonstrate deterministic JSON serialization;
6. report the final mixture capability boundary;
7. keep PR #7 Draft until approval.

Do not add heat balance, exchanger correlations, geometry selection, costing, mechanical design or downstream two-phase solvers in this PR.
