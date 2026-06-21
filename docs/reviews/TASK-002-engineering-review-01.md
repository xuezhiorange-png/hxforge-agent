# TASK-002 Engineering Review — Round 1

**PR:** #5  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed, including Ruff, mypy, pytest and pip-audit.

The typed quantity hierarchy and unit-registry design are directionally correct. The following issues must be resolved before TASK-002 can be approved because they affect the public engineering contract and physical validity.

## 1. Implement the approved `state_spec` public contract

`StreamSpec` still exposes only legacy `inlet_temperature` and `inlet_pressure` fields. The approved v0.1 I/O contract defines a versioned, mutually exclusive thermodynamic-state union:

- `TP`: absolute temperature + absolute pressure;
- `PH`: absolute pressure + specific enthalpy;
- `PQ`: absolute pressure + vapor quality.

Required revision:

- add typed `TPStateSpec`, `PHStateSpec` and `PQStateSpec` models;
- use a discriminated union on `type`;
- constrain PQ quality to `[0, 1]`;
- add `schema_version`;
- expose `state_spec` as the canonical public field;
- keep legacy inlet temperature/pressure handling only through an explicit compatibility adapter or validator with deprecation documentation;
- reject payloads that provide conflicting state specifications.

No property calculation is required in TASK-002; this is only the unit-safe input contract.

## 2. Implement structured fouling resistance

The approved contract requires:

```text
fouling_resistance.value
fouling_resistance.source
```

The current `StreamSpec` stores only a bare `FoulingResistance`, losing the required source and reference-verification metadata.

Required revision:

- add a structured `FoulingSource` model;
- include `source_type`, `reference_id`, `edition`, `table_or_clause`, `verification_status` and `note`;
- add a `FoulingResistanceSpec` containing `value` and `source`;
- require an explicit source even when the value is zero;
- preserve DEC-017 enum values and reject unknown values.

## 3. Enforce hard physical invariants

Finite-number validation alone permits physically impossible public quantities.

At minimum, reject:

- absolute temperature below `0 K`;
- absolute pressure below `0 Pa`;
- negative area;
- negative length;
- negative fouling resistance.

For stream fields, additionally require positive mass flow and positive design/operating absolute pressure unless a future solved-variable contract explicitly permits omission.

Do not apply universal non-negativity to signed quantities such as temperature difference, duty or solver residuals without an explicit sign convention.

Add structured error codes and boundary tests for each hard invariant.

## 4. Public input models must reject unknown fields

The quantity base model uses `extra="forbid"`, but surrounding public input models inherit Pydantic's default behavior and may silently ignore unknown fields.

Required revision:

- create a shared strict public-input base model using `ConfigDict(extra="forbid")`;
- apply it to `FluidSpec`, state specifications, `StreamSpec`, `DesignConstraints`, `DesignCase` and fouling-source models;
- add tests proving misspelled or unsupported fields are rejected rather than ignored.

This is required for reliable engineering validation and deterministic hashing.

## 5. Expose unit constraints in generated schemas

Runtime allowlists are implemented, but generated Pydantic/OpenAPI schemas still present `unit` as an unrestricted string. Non-technical API users cannot discover valid units from the schema.

Required revision:

- expose quantity-kind and allowed-unit information in generated JSON Schema/OpenAPI metadata;
- include the canonical SI unit and representative examples;
- add schema tests for at least absolute temperature, temperature difference, absolute pressure and mass flow.

Do not duplicate an independently maintained unit list; generate schema metadata from `UNIT_RULES`.

## 6. Add integration and compatibility regression tests

Unit-level tests are strong, but the PR does not prove that current repository entry points remain usable.

Required revision:

- validate `examples/water_water_double_pipe.json` against `DesignCase`;
- update the example to use explicit absolute-pressure notation such as `bar(a)` for clarity;
- test JSON serialization and revalidation of a complete design case;
- add one FastAPI/Pydantic error-response test showing a structured unit error reaches the API boundary;
- add a regression test that a legacy TP payload is either explicitly adapted or rejected with a documented migration error.

## 7. Clarify task completion and compatibility claims

The task card currently marks most acceptance items complete before engineering review. Keep TASK-002 `IN_PROGRESS` until these contract issues are resolved.

Update the PR description after revision to state clearly:

- which public schemas changed;
- whether the change is backward compatible;
- how legacy TP fields are handled;
- which physical bounds are enforced in quantity types versus workflow models.

## Approval gate

After revisions:

1. rerun Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12;
2. report the final public quantity and state-spec schemas;
3. report hard physical bounds and error codes;
4. confirm the example and API-boundary regression tests pass;
5. keep PR #5 as Draft until engineering approval is explicitly recorded.

No fluid-property calls, heat-balance equations, exchanger correlations, costing or mechanical calculations should be added in this PR.
