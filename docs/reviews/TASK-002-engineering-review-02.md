# TASK-002 Engineering Review — Round 2

**PR:** #5  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed, including Ruff, mypy, pytest and pip-audit.

Round 1 addressed most quantity-model requirements. The remaining issues are contract and integration defects that must be resolved before TASK-002 approval.

## 1. Make structured fouling resistance the canonical `fouling_resistance` field

The approved public contract is:

```yaml
fouling_resistance:
  value: {value: 0.0002, unit: m^2*K/W}
  source: {...}
```

The current model instead adds `fouling_resistance_spec` while retaining a bare `fouling_resistance` quantity. This creates a second public field name and allows callers to bypass the mandatory DEC-017 source metadata.

Required revision:

- make `fouling_resistance: FoulingResistanceSpec` the canonical field;
- do not accept an unsourced bare fouling value in the canonical `StreamSpec`;
- if backward compatibility is required, implement it through an explicit legacy adapter that rejects migration unless a source object is also supplied;
- update examples, tests and documentation to use the approved field name;
- test that a bare fouling quantity cannot enter the canonical model without provenance.

## 2. Make canonical TP `state_spec` usable by the existing design endpoint

`DoublePipeService.size()` still reads only `stream.inlet_temperature` and ignores `TPStateSpec.temperature`. A valid canonical TP case therefore validates successfully but is blocked when passed to `/v1/design/double-pipe`.

Required revision:

- add a deterministic state-access helper or model properties that expose inlet temperature and pressure from either the canonical TP state or the documented legacy TP adapter;
- use that helper in `DoublePipeService`;
- for PH or PQ states, return the correct explicit unsupported result (`NOT_IMPLEMENTED`) before attempting the starter calculation;
- add an integration test posting a canonical TP payload to `/v1/design/double-pipe` and verify the endpoint does not fail merely because legacy inlet fields are absent;
- retain the current task boundary: do not add property calculations for PH/PQ.

## 3. Enforce the state-schema version

`schema_version` is currently an arbitrary string with a default value, so unsupported versions such as `"9.9"` are accepted.

Required revision:

- constrain each v0.1 state model to `schema_version: Literal["1.0"]`;
- decide whether the field is required or defaulted, and document that behavior consistently;
- add tests rejecting unsupported schema versions.

## 4. Remove the hidden property-backend default

The approved I/O dictionary marks `fluid.backend` as required, but `FluidSpec` still defaults it to `CoolProp`. This is a hidden public-input default and conflicts with the approved baseline.

Required revision:

- make `backend` required in the canonical `FluidSpec`;
- keep any convenience default outside the canonical public model, for example in a UI or explicit adapter;
- add a test proving a canonical payload without `fluid.backend` is rejected.

## 5. Complete schema, endpoint and migration regression tests

The review report claims JSON/OpenAPI metadata and endpoint compatibility are complete, but current tests do not verify the generated quantity schemas and only exercise `/v1/cases/validate` for the canonical example.

Required revision:

- add JSON Schema/OpenAPI assertions for `MassFlow`, `AbsoluteTemperature`, `TemperatureDifference` and `AbsolutePressure` covering `quantity_kind`, `si_unit`, `allowed_units` and examples;
- add the canonical TP design-endpoint test described above;
- add a canonical structured-fouling validation test and a bare-fouling rejection test;
- document and test the legacy TP migration path, including its deprecation behavior;
- use the actual structured error-code names in tests and documentation.

## 6. Update task and PR records to match the implementation

The PR body still reports 86 tests and does not describe the new state/fouling contracts or compatibility behavior. The task card still leaves CI unchecked, contains contradictory pip-audit statements and does not mark Round 1 as resolved.

Required revision:

- update the PR description with the final public schema changes, backward-compatibility policy, physical bounds and current test count;
- update `docs/tasks/TASK-002-units-and-quantities.md` so CI is checked and validation records are non-contradictory;
- after all code changes pass, mark Round 1 review resolved but keep TASK-002 `IN_PROGRESS` until final engineering approval.

## Approval gate

After these revisions:

1. rerun Ruff, mypy, pytest and pip-audit on Python 3.11 and 3.12;
2. demonstrate canonical TP validation and design-endpoint integration;
3. demonstrate that unsourced fouling cannot enter the canonical model;
4. demonstrate unsupported state-schema versions are rejected;
5. confirm public schema metadata through automated tests;
6. keep PR #5 as Draft until final approval is recorded.

No fluid-property implementation, heat balance, exchanger correlations, costing or mechanical calculations should be added in this PR.
