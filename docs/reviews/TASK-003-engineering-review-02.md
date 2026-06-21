# TASK-003 Engineering Review — Round 2

**PR:** #7  
**Head reviewed:** `4ba133d62bc690da92aaccdc398b9e017ea4a32f`  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

Round 1 added the requested fields and tests, but several engineering guarantees are still not implemented. The following items must be resolved before TASK-003 approval.

## 1. The CoolProp configuration fingerprint does not protect live calculations

The fingerprint is captured once in `CoolPropProvider.__init__()` and then reused forever in provenance and cache keys. The provider does not recompute or verify it before later queries. Therefore a process-wide CoolProp mutation after provider construction can still reuse stale cached values.

The fingerprint function also calls `get_global_param_string()` using names that are not demonstrated to represent the active reference-state/configuration values; exceptions are converted to the constant string `unset`. This does not prove that the reference state is still `DEF`.

Required revision:

- implement a real runtime guard before every query and cache access;
- either isolate calculations with provider-owned low-level state objects and a documented process lock, or detect any external mutation and fail closed;
- do not silently continue with a stale construction-time fingerprint;
- include a deterministic per-fluid reference-state signature, not only unsupported global-string probes;
- add a test that mutates CoolProp after provider creation and proves cached results are not reused;
- add a stable error code such as `property_configuration_changed` if the provider fails closed.

## 2. `BENCHMARK_VALIDATED` is still assigned without independent benchmark evidence or state-envelope matching

The validation matrix cites `CoolProp v7.6.1` as its source, so it is a same-backend regression fixture rather than independent validation evidence. The provider then places all four Tier-1 names in `_BENCHMARK_VALIDATED_FLUIDS` and returns `BENCHMARK_VALIDATED` for every state of those fluids.

Required revision:

- classify the current CoolProp-derived fixtures as backend regression data, not independent benchmarks;
- return `SUPPORTED_TIER_1` unless independent/reference evidence is provided;
- evaluate validation level against the actual query type, state point or approved envelope;
- do not mark arbitrary Water, Air, R134a or R717 states as benchmark validated solely by fluid name;
- add `validation_dataset_id`, `validation_dataset_revision` and `validation_basis` to provenance;
- add tests for one state inside and one state outside each approved validation envelope;
- preserve `BENCHMARK_VALIDATED` as a future level, but do not claim it prematurely.

## 3. PH reference-state semantics remain optional and are absent from the provider protocol

`state_ph()` defaults `reference_state=DEF`, so a caller can omit the reference-state identifier. The `PropertyProvider` protocol still declares `state_ph()` without the reference-state argument. The implementation only compares enum values and does not prove that the active CoolProp reference state is actually `DEF`.

Required revision:

- make the reference-state identifier mandatory for PH queries;
- add it to the `PropertyProvider` protocol;
- update the TASK-002 `PHStateSpec` contract or add a versioned adapter requiring the identifier;
- verify the active provider state before interpreting enthalpy;
- include reference state directly in the PH input identity, provenance and cache key;
- reject omitted, unknown and mismatched identifiers with distinct structured errors.

## 4. The `FluidSpec` adapter still confuses provider identity with EOS backend identity

`FluidIdentifier.from_fluid_spec()` accepts a string named `backend` and maps it directly to `equation_of_state_backend`. The approved public `FluidSpec.backend` currently represents the property provider (`CoolProp`), not the internal EOS backend (`HEOS`). Passing the canonical public value would therefore produce `CoolProp::Water`, not `HEOS::Water`.

Required revision:

- accept the actual `FluidSpec` object or a clearly typed adapter input;
- verify `provider_id == "CoolProp"` separately;
- resolve `equation_of_state_backend` explicitly, with `HEOS` as an approved visible policy rather than by reusing the provider field;
- document and validate composition basis as mole fraction;
- reject unsupported provider/EOS combinations;
- add an integration test using the real public `FluidSpec(backend="CoolProp", ...)` contract.

## 5. Result serialization is not yet strict or a true domain round trip

The serialization models use `dict[str, Any]` for provenance and plain strings for enums. They do not use `extra="forbid"`, and `result_schema_version` is a regex-constrained string rather than a literal version. `FluidState.from_json()` returns `FluidStateModel`, not a reconstructed `FluidState`, so the current test is a model parse, not a domain-object round trip.

Required revision:

- define strict nested Pydantic models for provenance and results;
- use enum fields and `Literal["1.0"]`;
- set `extra="forbid"`;
- include every provenance field, including result schema version and validation dataset fields;
- provide either a true `FluidState -> JSON -> FluidState` round trip or rename the API to make the model-envelope behavior explicit;
- add deterministic canonical JSON tests;
- add structured JSON serialization and round-trip tests for `PropertyServiceError`.

## 6. The mixture capability boundary contradicts the stated policy

The tests describe v0.1 mixture support as “representation only,” but then execute an actual TP mixture calculation when `allow_unvalidated_fluids=True`. The provider contains no explicit mixture capability gate, so PH and saturation queries may also proceed despite not being validated.

Required revision:

Choose one policy and enforce it:

- **preferred v0.1 policy:** mixture identifiers are representable, but all mixture calculations return a structured `NOT_IMPLEMENTED`/unsupported-query error; or
- fully define and test the allowed mixture query set, composition basis, phase-envelope behavior, bubble/dew semantics and validation limits.

Do not use the same `allow_unvalidated_fluids` switch to imply that an unvalidated pure fluid and an unimplemented mixture calculation are equivalent.

## 7. Error classification remains dependent on backend message text

`_raise_backend_error()` searches English message tokens and the out-of-range test accepts either `STATE_OUT_OF_RANGE` or `BACKEND_FAILURE`. This does not meet the requirement for stable public error codes independent of CoolProp wording.

Required revision:

- make the tested public classification deterministic for known boundary cases;
- the below-triple/out-of-range regression must assert exactly `property_state_out_of_range`;
- above-critical saturation must assert exactly `property_saturation_unavailable`;
- keep the raw CoolProp message only as context;
- add tests proving failed queries do not increment cache hits or create entries.

## 8. Documentation and task records are not yet synchronized

The pushed revision did not update `docs/PROPERTY_BACKENDS.md`, so the documented reference-state, validation and mixture policies remain stale. The task card still marks CI unchecked even though the latest run passed, and Round 1 is still recorded as resolved despite the remaining defects.

Required revision:

- update `docs/PROPERTY_BACKENDS.md` with the final enforceable policy, not only intended behavior;
- update the PR description with the actual validation level and mixture boundary;
- mark CI complete in the task card only after the final revision passes;
- keep TASK-003 `IN_PROGRESS` and PR #7 Draft until final engineering approval.

## Approval gate

After correction:

1. rerun Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12;
2. demonstrate runtime detection or isolation of CoolProp global-state mutations;
3. report validation evidence and state-envelope rules without self-certification;
4. demonstrate mandatory PH reference-state identity end to end;
5. demonstrate the real `FluidSpec -> FluidIdentifier` adapter;
6. demonstrate strict deterministic result/error serialization;
7. demonstrate an enforced mixture capability boundary;
8. demonstrate exact stable error classifications.

No heat-balance equations, exchanger correlations, geometry selection, costing, mechanical design or downstream two-phase solvers may be added in this PR.
